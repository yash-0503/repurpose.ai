import os
import re
import time
import logging
import httpx
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_TRANSCRIPT_API_URL = "https://www.youtube-transcript.io/api/transcripts"
_API_TOKEN = os.getenv("YOUTUBE_TRANSCRIPT_IO_API_TOKEN")
_FETCH_RETRIES = max(1, int(os.getenv("YOUTUBE_TRANSCRIPT_FETCH_RETRIES", "4")))
_FETCH_RETRY_BASE_SEC = float(os.getenv("YOUTUBE_TRANSCRIPT_RETRY_BASE_SEC", "4"))


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


def _parse_transcript_io_response(data: Any, video_id: str) -> Dict[str, str]:
    """Parse youtube-transcript.io response into text, title, language."""
    if not isinstance(data, list) or not data:
        raise TranscriptFetchError("No transcript returned for this video.")

    entry = next((item for item in data if item.get("id") == video_id), data[0])
    if not isinstance(entry, dict):
        raise TranscriptFetchError("Unexpected transcript API response format.")

    text = (entry.get("text") or "").strip()
    if not text or len(text) < 10:
        raise TranscriptFetchError("Transcript is empty or too short")

    title = entry.get("title") or "Unknown"
    language = entry.get("language") or entry.get("lang") or "auto"

    return {"text": text, "title": title, "language": language}


def _fetch_via_transcript_io(video_id: str) -> Dict[str, str]:
    if not _API_TOKEN:
        raise TranscriptFetchError(
            "YouTube transcript API not configured. Set YOUTUBE_TRANSCRIPT_IO_API_TOKEN in .env"
        )

    last_error: Optional[Exception] = None
    for attempt in range(1, _FETCH_RETRIES + 1):
        try:
            response = httpx.post(
                _TRANSCRIPT_API_URL,
                headers={
                    "Authorization": f"Basic {_API_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={"ids": [video_id]},
                timeout=30,
            )

            if response.status_code == 429:
                retry_after = float(
                    response.headers.get("Retry-After", _FETCH_RETRY_BASE_SEC)
                )
                if attempt < _FETCH_RETRIES:
                    logger.warning(
                        "Transcript API rate limited. Retrying in %.1fs (attempt %s/%s).",
                        retry_after,
                        attempt,
                        _FETCH_RETRIES,
                    )
                    time.sleep(retry_after)
                    continue
                raise TranscriptFetchError(
                    "Transcript API rate limit exceeded. Please try again shortly."
                )

            if response.status_code == 401:
                raise TranscriptFetchError(
                    "Invalid YouTube transcript API token. Check YOUTUBE_TRANSCRIPT_IO_API_TOKEN."
                )

            if response.status_code != 200:
                detail = response.text[:200] if response.text else "Unknown error"
                raise TranscriptFetchError(
                    f"Transcript API error ({response.status_code}): {detail}"
                )

            return _parse_transcript_io_response(response.json(), video_id)

        except TranscriptFetchError:
            raise
        except Exception as exc:
            last_error = exc
            if attempt < _FETCH_RETRIES:
                wait = _FETCH_RETRY_BASE_SEC * (2 ** (attempt - 1))
                logger.warning(
                    "Transcript attempt %s/%s failed: %s. Sleeping %.1fs.",
                    attempt,
                    _FETCH_RETRIES,
                    exc,
                    wait,
                )
                time.sleep(wait)

    raise TranscriptFetchError(
        f"Failed to fetch transcript: {last_error or 'unknown error'}"
    )


def fetch_transcript(url: str) -> Dict[str, str]:
    """Fetch transcript for a YouTube video via youtube-transcript.io.

    Returns dict with keys: text, title, language
    """
    validate_url(url)
    video_id = extract_video_id(url)

    logger.info(f"Fetching transcript for video: {video_id}")
    result = _fetch_via_transcript_io(video_id)

    logger.info(
        f"Transcript fetched: {len(result['text'])} chars, "
        f"language={result['language']}, title={result['title']}"
    )
    return result
