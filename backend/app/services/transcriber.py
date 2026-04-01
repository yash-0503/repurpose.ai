import os
import logging
from typing import Dict, Optional
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_WHISPER_MODEL","whisper-large-v3-turbo")
MAX_AUDIO_SIZE_MB = int(os.getenv("MAX_AUDIO_SIZE_MB", "100"))


class TranscriptionError(Exception):
    pass


def validate_audio_file(filepath: str) -> Path:
    if not filepath:
        raise TranscriptionError("File path cannot be empty")
    
    path = Path(filepath)
    
    if not path.exists():
        raise TranscriptionError(f"Audio file not found: {filepath}")
    
    if not path.is_file():
        raise TranscriptionError(f"Path is not a file: {filepath}")
    
    file_size_mb = path.stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_AUDIO_SIZE_MB:
        raise TranscriptionError(
            f"Audio file too large: {file_size_mb:.1f}MB (max: {MAX_AUDIO_SIZE_MB}MB)"
        )
    
    valid_extensions = {'.mp3', '.mp4', '.wav', '.m4a', '.webm', '.ogg'}
    if path.suffix.lower() not in valid_extensions:
        logger.warning(f"Unusual audio format: {path.suffix}")
    
    return path


def transcribe_audio(
    filepath: str,
    model_name: str = GROQ_MODEL,
    language: Optional[str] = None,
    task: str = "transcribe"
) -> Dict[str, any]:
    try:
        audio_path = validate_audio_file(filepath)
        
        logger.info(f"Transcribing: {audio_path.name}")

        if not GROQ_API_KEY:
            raise TranscriptionError("Groq Api Key not configured")
        
        client = Groq(api_key=GROQ_API_KEY)
        with open(audio_path, "rb") as audio_file:
             response = client.audio.transcriptions.create(
                file=audio_file,
                model=model_name,
                language=language or "",
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
        
        segments = getattr(response,"segments",[]) or []
        duration = segments[-1].get("end",0) if segments else 0.0
        
        output = {
            'text': response.text.strip(),
            'language': getattr(response,"language","unknown"),
            'segments': segments,
            'duration': duration,
        }
        
        logger.info(
            f"Transcription complete: {len(output['text'])} chars, "
            f"language: {output['language']}"
        )
        
        return output
        
    except TranscriptionError:
        raise
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise TranscriptionError(f"Failed to transcribe audio: {str(e)}")
