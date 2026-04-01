import yt_dlp
import os
import logging
import tempfile
import base64
from typing import Tuple, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_AUDIO_SIZE_MB", "100"))

_cookies_file: Optional[str] = None


class AudioDownloadError(Exception):
    pass


def _get_cookies_path() -> Optional[str]:
    """Decode YOUTUBE_COOKIES_B64 env var to a temp file (once) and return the path."""
    global _cookies_file
    if _cookies_file and Path(_cookies_file).exists():
        return _cookies_file

    cookies_b64 = os.getenv("YOUTUBE_COOKIES_B64")
    if not cookies_b64:
        return None

    try:
        content = base64.b64decode(cookies_b64).decode("utf-8")
        path = Path(tempfile.gettempdir()) / "yt_cookies.txt"
        path.write_text(content)
        _cookies_file = str(path)
        logger.info("YouTube cookies file written")
        return _cookies_file
    except Exception as e:
        logger.warning(f"Failed to decode YOUTUBE_COOKIES_B64: {e}")
        return None


def get_ydl_opts(output_template: str) -> dict:
    opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'extractor_retries': 3,
        'fragment_retries': 10,
        'retry_sleep_functions': {'http': lambda n: min(3 * n, 30)},
        'socket_timeout': 30,
    }

    cookies_path = _get_cookies_path()
    if cookies_path:
        opts['cookiefile'] = cookies_path

    return opts


def validate_url(url: str) -> None:
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")
    
    valid_domains = ['youtube.com', 'youtu.be', 'm.youtube.com']
    if not any(domain in url.lower() for domain in valid_domains):
        raise ValueError("Invalid YouTube URL")


def download_audio(url: str, use_temp: bool = True) -> Tuple[str, str]:
    try:
        validate_url(url)
        
        if use_temp:
            output_dir = Path(tempfile.mkdtemp(prefix="repurpose_audio_"))
        else:
            output_dir = DOWNLOAD_DIR
            output_dir.mkdir(parents=True, exist_ok=True)
        
        output_template = str(output_dir / "%(title)s.%(ext)s")
        ydl_opts = get_ydl_opts(output_template)
        
        logger.info(f"Downloading audio from: {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if info.get('filesize', 0) > MAX_FILE_SIZE_MB * 1024 * 1024:
                logger.warning(f"File size ({info.get('filesize')} bytes) exceeds limit")
            
            title = info.get('title', 'Unknown')
            filename = ydl.prepare_filename(info)
            audio_path = Path(filename)
            
            if not audio_path.exists():
                 for f in audio_path.parent.iterdir():
                    if f.stem == audio_path.stem:
                        audio_path = f
                        break
            
            logger.info(f"Successfully downloaded: {title}")
            return str(audio_path), title
            
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp download error: {e}")
        raise AudioDownloadError(f"Failed to download video: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error during download: {e}")
        raise AudioDownloadError(f"Download failed: {str(e)}")


def cleanup_audio_file(file_path: str) -> None:
    try:
        path = Path(file_path)
        if path.exists():
            path.unlink()
            logger.debug(f"Deleted audio file: {file_path}")
            
            if 'repurpose_audio_' in str(path.parent):
                if path.parent.exists() and not list(path.parent.iterdir()):
                    path.parent.rmdir()
                    logger.debug(f"Deleted temp directory: {path.parent}")
    except Exception as e:
        logger.warning(f"Failed to cleanup audio file {file_path}: {e}")
