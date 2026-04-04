import os
import re
import logging
import httpx
from typing import Dict
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


class TranscriptFetchError(Exception):
    pass


def validate_url(url: str) -> None:
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")

    valid_domains = ['youtube.com', 'youtu.be', 'm.youtube.com']
    if not any(domain in url.lower() for domain in valid_domains):
        raise ValueError("Invalid YouTube URL")


def extract_video_id(url: str) -> str:
    """Extract the video ID from various YouTube URL formats."""
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'(?:embed/)([a-zA-Z0-9_-]{11})',
        r'(?:shorts/)([a-zA-Z0-9_-]{11})',
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


def _get_ytt_api() -> YouTubeTranscriptApi:
    """Create a YouTubeTranscriptApi instance, with Webshare proxy if configured."""
    if WEBSHARE_USERNAME and WEBSHARE_PASSWORD:
        from youtube_transcript_api.proxies import WebshareProxyConfig
        logger.info("Using Webshare proxy for transcript fetch")
        return YouTubeTranscriptApi(
            proxy_config=WebshareProxyConfig(
                proxy_username=WEBSHARE_USERNAME,
                proxy_password=WEBSHARE_PASSWORD,
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
                logger.info(f"Selected {group_label} English transcript ({t.language_code})")
                return t.fetch()

    for group_label, group in [("manual", manual), ("auto-generated", generated)]:
        if group:
            t = group[0]
            logger.info(f"Selected {group_label} transcript: {t.language} ({t.language_code})")
            return t.fetch()

    raise NoTranscriptFound(video_id, [], [])


def fetch_transcript(url: str) -> Dict[str, str]:
    """Fetch transcript for a YouTube video using captions/subtitles.

    Returns dict with keys: text, title, language
    """
    try:
        validate_url(url)
        video_id = extract_video_id(url)

        logger.info(f"Fetching transcript for video: {video_id}")

        transcript = _fetch_best_transcript(video_id)

        text = " ".join(snippet.text for snippet in transcript)

        if not text or len(text.strip()) < 10:
            raise TranscriptFetchError("Transcript is empty or too short")

        title = _fetch_title(url)
        language = transcript.language_code if hasattr(transcript, 'language_code') else "auto"

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
        raise TranscriptFetchError(f"Failed to fetch transcript: {str(e)}")
