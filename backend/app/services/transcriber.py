import os
import logging
from typing import Dict, Optional
from pathlib import Path
import whisper
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")
MAX_AUDIO_SIZE_MB = int(os.getenv("MAX_AUDIO_SIZE_MB", "100"))

_model_cache: Optional[whisper.Whisper] = None


class TranscriptionError(Exception):
    pass


def get_model(model_name: str = WHISPER_MODEL) -> whisper.Whisper:
    global _model_cache
    
    if _model_cache is None:
        logger.info(f"Loading Whisper model: {model_name}")
        try:
            _model_cache = whisper.load_model(model_name)
            logger.info(f"Whisper model '{model_name}' loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise TranscriptionError(f"Model loading failed: {str(e)}")
    
    return _model_cache


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
    model_name: str = WHISPER_MODEL,
    language: Optional[str] = None,
    task: str = "transcribe"
) -> Dict[str, any]:
    try:
        audio_path = validate_audio_file(filepath)
        
        logger.info(f"Transcribing: {audio_path.name}")
        
        model = get_model(model_name)
        
        options = {
            'fp16': False,
            'task': task,
        }
        
        if language:
            options['language'] = language
        
        result = model.transcribe(str(audio_path), **options)
        
        output = {
            'text': result.get('text', '').strip(),
            'language': result.get('language', 'unknown'),
            'segments': result.get('segments', []),
            'duration': sum(seg.get('end', 0) for seg in result.get('segments', [])),
        }
        
        logger.info(
            f"Transcription complete: {len(output['text'])} chars, "
            f"{len(output['segments'])} segments, "
            f"language: {output['language']}"
        )
        
        return output
        
    except TranscriptionError:
        raise
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        raise TranscriptionError(f"Failed to transcribe audio: {str(e)}")


def get_transcript_text(filepath: str, **kwargs) -> str:
    result = transcribe_audio(filepath, **kwargs)
    return result['text']


def simple_transcribe(filepath: str) -> dict:
    logger.warning("Using legacy simple_transcribe function. Consider using transcribe_audio().")
    
    try:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File path doesn't exist: {filepath}")
        
        logger.info(f"Transcribing the video at {filepath}")
        model = get_model()
        result = model.transcribe(filepath, fp16=False)
        return result
        
    except Exception as e:
        logger.error(f"Legacy transcription failed: {e}")
        raise


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Testing audio transcriber...")
    print(f"Whisper model: {WHISPER_MODEL}\n")
    
    test_file = "downloads/test_audio.mp3"
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        print("Create a test audio file or update the path above.\n")
    else:
        print(f"Testing with: {test_file}\n")
        
        try:
            print("1. Full transcription...")
            result = transcribe_audio(test_file)
            print(f"✅ Language: {result['language']}")
            print(f"✅ Duration: {result['duration']:.1f}s")
            print(f"✅ Segments: {len(result['segments'])}")
            print(f"✅ Text preview: {result['text'][:100]}...\n")
            
            print("2. Simple text extraction...")
            text = get_transcript_text(test_file)
            print(f"✅ Text length: {len(text)} characters\n")
            
        except TranscriptionError as e:
            print(f"❌ Failed: {e}\n")
