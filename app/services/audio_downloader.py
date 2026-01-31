import yt_dlp
import os
import logging
import tempfile
from typing import Tuple, Optional
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = Path(os.getenv("DOWNLOAD_DIR", "downloads"))
MAX_FILE_SIZE_MB = int(os.getenv("MAX_AUDIO_SIZE_MB", "100"))
AUDIO_QUALITY = os.getenv("AUDIO_QUALITY", "128")


class AudioDownloadError(Exception):
    pass


def get_ydl_opts(output_template: str, extract_audio: bool = True) -> dict:
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
    
    if extract_audio:
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredquality': AUDIO_QUALITY,
            'preferredcodec': 'mp3',
        }]
    
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
        ydl_opts = get_ydl_opts(output_template, extract_audio=True)
        
        logger.info(f"Downloading audio from: {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            if info.get('filesize', 0) > MAX_FILE_SIZE_MB * 1024 * 1024:
                logger.warning(f"File size ({info.get('filesize')} bytes) exceeds limit")
            
            title = info.get('title', 'Unknown')
            filename = ydl.prepare_filename(info)
            audio_path = Path(filename).with_suffix('.mp3')
            
            if not audio_path.exists():
                raise AudioDownloadError(f"Downloaded file not found: {audio_path}")
            
            logger.info(f"Successfully downloaded: {title}")
            return str(audio_path), title
            
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp download error: {e}")
        raise AudioDownloadError(f"Failed to download video: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error during download: {e}")
        raise AudioDownloadError(f"Download failed: {str(e)}")


def extract_audio_url(url: str) -> Tuple[str, str, int]:
    try:
        validate_url(url)
        
        ydl_opts = get_ydl_opts("", extract_audio=False)
        ydl_opts['extract_flat'] = False
        
        logger.info(f"Extracting audio URL from: {url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            audio_url = info.get('url')
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            
            if not audio_url:
                raise AudioDownloadError("Could not extract audio URL")
            
            logger.info(f"Extracted audio URL for: {title}")
            return audio_url, title, duration
            
    except Exception as e:
        logger.error(f"Failed to extract audio URL: {e}")
        raise AudioDownloadError(f"URL extraction failed: {str(e)}")


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


def simple_download(url: str, output_dir: Optional[str] = None) -> str:
    logger.warning("Using legacy simple_download function. Consider using download_audio().")
    
    if output_dir:
        global DOWNLOAD_DIR
        original_dir = DOWNLOAD_DIR
        DOWNLOAD_DIR = Path(output_dir)
    
    try:
        audio_path, _ = download_audio(url, use_temp=False)
        return audio_path
    finally:
        if output_dir:
            DOWNLOAD_DIR = original_dir


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    print("Testing audio downloader...")
    print(f"Test URL: {test_url}\n")
    
    print("1. Extracting audio URL (no download)...")
    try:
        audio_url, title, duration = extract_audio_url(test_url)
        print(f"✅ Title: {title}")
        print(f"✅ Duration: {duration}s")
        print(f"✅ URL: {audio_url[:80]}...\n")
    except AudioDownloadError as e:
        print(f"❌ Failed: {e}\n")
    
    print("2. Downloading to temp directory...")
    try:
        temp_path, title = download_audio(test_url, use_temp=True)
        print(f"✅ Downloaded: {title}")
        print(f"✅ Path: {temp_path}")
        
        cleanup_audio_file(temp_path)
        print("✅ Cleaned up\n")
    except AudioDownloadError as e:
        print(f"❌ Failed: {e}\n")
