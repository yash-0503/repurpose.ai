import os
import re
import time
import logging
import httpx
from typing import Dict, List, Optional
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

WEBSHARE_USERNAME = os.getenv("WEBSHARE_PROXY_USERNAME")
WEBSHARE_PASSWORD = os.getenv("WEBSHARE_PROXY_PASSWORD")
TRANSCRIPT_HTTP_PROXY = os.getenv("YOUTUBE_TRANSCRIPT_HTTP_PROXY")
TRANSCRIPT_HTTPS_PROXY = os.getenv("YOUTUBE_TRANSCRIPT_HTTPS_PROXY")

_FETCH_RETRIES = max(1, int(os.getenv("YOUTUBE_TRANSCRIPT_FETCH_RETRIES", "4")))
_FETCH_RETRY_BASE_SEC = float(os.getenv("YOUTUBE_TRANSCRIPT_RETRY_BASE_SEC", "4"))

WEBSHARE_DOC = (
    "https://github.com/jdepoix/youtube-transcript-api/blob/master/README.md#working-around-ip-bans"
)


class TranscriptFetchError(Exception):
    pass


def validate_url(url: str) -> None:
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")

    valid_domains = ["youtube.com", "youtu.be", "m.youtube.com"]
    if not any(domain in url.lower() for domain in valid_domains):
        raise ValueError("Invalid YouTube URL")


def extract_video_id(url: str) -> str:
    """Extract the video ID from various YouTube URL formats."""
    patterns = [
        r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:embed/)([a-zA-Z0-9_-]{11})",
        r"(?:shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise TranscriptFetchError(f"Could not extract video ID from URL: {url}")


def _fetch_title(url: str) -> str:
    """Fetch video title via YouTube oEmbed (no auth required)."""
    try:
        resp = httpx.get(
            "https://www.youtube.com/oembed",
            params={"url": url, "format": "json"},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("title", "Unknown")
    except Exception as e:
        logger.warning(f"Failed to fetch title via oEmbed: {e}")
    return "Unknown"


def _parse_webshare_locations() -> Optional[List[str]]:
    raw = os.getenv("WEBSHARE_PROXY_LOCATIONS", "").strip()
    if not raw:
        return None
    return [x.strip().lower() for x in raw.split(",") if x.strip()]


def _get_ytt_api() -> YouTubeTranscriptApi:
    """Build API client: generic proxy > Webshare > direct."""
    if TRANSCRIPT_HTTP_PROXY or TRANSCRIPT_HTTPS_PROXY:
        from youtube_transcript_api.proxies import GenericProxyConfig

        logger.info("Using YOUTUBE_TRANSCRIPT_* proxy for transcript fetch")
        return YouTubeTranscriptApi(
            proxy_config=GenericProxyConfig(
                http_url=TRANSCRIPT_HTTP_PROXY,
                https_url=TRANSCRIPT_HTTPS_PROXY,
            )
        )

    if WEBSHARE_USERNAME and WEBSHARE_PASSWORD:
        from youtube_transcript_api.proxies import WebshareProxyConfig

        locations = _parse_webshare_locations()
        retries = int(os.getenv("WEBSHARE_RETRIES_WHEN_BLOCKED", "25"))
        logger.info(
            "Using Webshare proxy for transcript fetch "
            f"(locations={locations or 'any'}, retries_when_blocked={retries})"
        )
        return YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=WEBSHARE_USERNAME,
                proxy_password=WEBSHARE_PASSWORD,
                filter_ip_locations=locations,
                retries_when_blocked=retries,
            )
        )

    return YouTubeTranscriptApi()


def _fetch_best_transcript(video_id: str):
    """List all available transcripts and pick the best one.

    Priority: manual English > auto English > manual any > auto any.
    """
    ytt_api = _get_ytt_api()
    transcript_list = ytt_api.list(video_id)

    manual = []
    generated = []
    for t in transcript_list:
        (manual if not t.is_generated else generated).append(t)

    for group_label, group in [("manual", manual), ("auto-generated", generated)]:
        for t in group:
            if t.language_code.startswith("en"):
                logger.info(
                    f"Selected {group_label} English transcript ({t.language_code})"
                )
                return t.fetch()

    for group_label, group in [("manual", manual), ("auto-generated", generated)]:
        if group:
            t = group[0]
            logger.info(
                f"Selected {group_label} transcript: {t.language} ({t.language_code})"
            )
            return t.fetch()

    raise NoTranscriptFound(video_id, [], [])


def _map_transient_error(exc: Exception) -> Optional[TranscriptFetchError]:
    """Turn Google CAPTCHA / rate-limit into a clear, actionable error."""
    msg = str(exc)
    low = msg.lower()
    if (
        "sorry/index" in low
        or "www.google.com" in low
        or "429" in low
        or "too many" in low and "retry" in low
        or "responseerror" in low
    ):
        return TranscriptFetchError(
            "YouTube blocked this server (Google CAPTCHA or rate limit). "
            "Datacenter / free Webshare 'Proxy Server' IPs usually fail. "
            "Fix: use Webshare **Residential** rotating proxies (not Static Residential), "
            "or set YOUTUBE_TRANSCRIPT_HTTP_PROXY to a trusted residential proxy URL. "
            f"Docs: {WEBSHARE_DOC}"
        )
    return None


def _fetch_best_transcript_with_retries(video_id: str):
    last_exc: Optional[Exception] = None
    for attempt in range(1, _FETCH_RETRIES + 1):
        try:
            return _fetch_best_transcript(video_id)
        except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
            raise
        except Exception as e:
            last_exc = e
            mapped = _map_transient_error(e)
            if mapped and attempt == _FETCH_RETRIES:
                raise mapped
            if attempt < _FETCH_RETRIES:
                wait = _FETCH_RETRY_BASE_SEC * (2 ** (attempt - 1))
                logger.warning(
                    "Transcript attempt %s/%s failed: %s. Sleeping %.1fs before retry.",
                    attempt,
                    _FETCH_RETRIES,
                    e,
                    wait,
                )
                time.sleep(wait)
    if last_exc is not None:
        mapped = _map_transient_error(last_exc)
        if mapped:
            raise mapped
        raise TranscriptFetchError(f"Failed to fetch transcript: {last_exc}")
    raise TranscriptFetchError("Transcript fetch failed with no exception")


def fetch_transcript(url: str) -> Dict[str, str]:
    """Fetch transcript for a YouTube video using captions/subtitles.

    Returns dict with keys: text, title, language
    """
    try:
        validate_url(url)
        video_id = extract_video_id(url)

        logger.info(f"Fetching transcript for video: {video_id}")

        transcript = _fetch_best_transcript_with_retries(video_id)

        text = " ".join(snippet.text for snippet in transcript)

        if not text or len(text.strip()) < 10:
            raise TranscriptFetchError("Transcript is empty or too short")

        title = _fetch_title(url)
        language = (
            transcript.language_code
            if hasattr(transcript, "language_code")
            else "auto"
        )

        logger.info(
            f"Transcript fetched: {len(text)} chars, "
            f"language={language}, title={title}"
        )

        return {"text": text, "title": title, "language": language}

    except TranscriptsDisabled:
        raise TranscriptFetchError(
            "Transcripts are disabled for this video. Try a different video."
        )
    except NoTranscriptFound:
        raise TranscriptFetchError(
            "No captions found for this video. Try a video with subtitles enabled."
        )
    except VideoUnavailable:
        raise TranscriptFetchError(
            "This video is unavailable or private."
        )
    except TranscriptFetchError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error fetching transcript: {e}")
        mapped = _map_transient_error(e)
        if mapped:
            raise mapped
        raise TranscriptFetchError(f"Failed to fetch transcript: {str(e)}")
