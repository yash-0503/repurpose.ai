import os
import logging
from typing import Optional
from dotenv import load_dotenv
from llama_index.core import Settings

load_dotenv()

logger = logging.getLogger(__name__)

MIN_REFERENCE_LENGTH = int(os.getenv("MIN_STYLE_TEXT_LENGTH", "100"))
MAX_REFERENCE_LENGTH = int(os.getenv("MAX_STYLE_TEXT_LENGTH", "10000"))

_llm_initialized = False


class StyleAnalysisError(Exception):
    pass


def ensure_llm_initialized() -> None:
    global _llm_initialized
    
    if _llm_initialized:
        return
    
    try:
        from llama_index.llms.google_genai import GoogleGenAI
        from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise StyleAnalysisError(
                "GEMINI_API_KEY not found in environment variables. "
                "Add it to your .env file."
            )
        
        Settings.llm = GoogleGenAI(model="gemini-2.5-flash", api_key=api_key)
        Settings.embed_model = GoogleGenAIEmbedding(
            model_name="text-embedding-004",
            api_key=api_key
        )
        
        _llm_initialized = True
        logger.info("Gemini LLM initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        raise StyleAnalysisError(f"LLM initialization failed: {str(e)}")


def validate_reference_text(text: str) -> str:
    if not text or not isinstance(text, str):
        raise StyleAnalysisError("Reference text must be a non-empty string")
    
    cleaned = text.strip()
    
    if len(cleaned) < MIN_REFERENCE_LENGTH:
        raise StyleAnalysisError(
            f"Reference text too short. Minimum {MIN_REFERENCE_LENGTH} characters required, "
            f"got {len(cleaned)}. Please provide more sample text for accurate style analysis."
        )
    
    if len(cleaned) > MAX_REFERENCE_LENGTH:
        logger.warning(f"Reference text truncated from {len(cleaned)} to {MAX_REFERENCE_LENGTH} characters")
        cleaned = cleaned[:MAX_REFERENCE_LENGTH]
    
    return cleaned


def create_style_prompt(reference_text: str) -> str:
    return f"""You are an expert literary analyst specializing in writing style identification.

Analyze the following text and create a comprehensive style guide that captures the author's unique voice.

Focus on:
1. **Tone**: Is it casual, academic, humorous, professional, conversational, or formal?
2. **Sentence Structure**: Do they prefer short, punchy sentences or longer, complex ones?
3. **Vocabulary**: Simple everyday words, technical jargon, or sophisticated language?
4. **Paragraph Length**: Brief or detailed paragraphs?
5. **Formatting Patterns**: Do they use bullet points, numbered lists, emojis, or special formatting?
6. **Personality Traits**: Enthusiastic, analytical, storytelling, direct, empathetic?
7. **Unique Expressions**: Any recurring phrases, idioms, or stylistic quirks?

Provide a concise style guide (2-3 paragraphs) that describes EXACTLY how to write like this author.
Be specific and actionable - someone should be able to mimic this style based on your description.

--- TEXT SAMPLE TO ANALYZE ---
{reference_text}
--- END OF SAMPLE ---

STYLE GUIDE:"""


def analyze_style(reference_text: str) -> str:
    try:
        ensure_llm_initialized()
        
        cleaned_text = validate_reference_text(reference_text)
        
        logger.info(f"Analyzing style for {len(cleaned_text)} characters of text")
        
        prompt = create_style_prompt(cleaned_text)
        
        response = Settings.llm.complete(prompt)
        style_guide = str(response).strip()
        
        if not style_guide or len(style_guide) < 50:
            raise StyleAnalysisError("Generated style guide is too short or empty")
        
        logger.info(f"Style analysis complete: {len(style_guide)} characters")
        return style_guide
        
    except StyleAnalysisError:
        raise
    except Exception as e:
        logger.error(f"Style analysis failed: {e}")
        raise StyleAnalysisError(f"Failed to analyze writing style: {str(e)}")


def quick_style_check(reference_text: str) -> dict:
    try:
        cleaned = validate_reference_text(reference_text)
        
        words = cleaned.split()
        sentences = cleaned.count('.') + cleaned.count('!') + cleaned.count('?')
        paragraphs = len([p for p in cleaned.split('\n\n') if p.strip()])
        
        metrics = {
            'word_count': len(words),
            'sentence_count': max(sentences, 1),
            'paragraph_count': max(paragraphs, 1),
            'avg_words_per_sentence': len(words) / max(sentences, 1),
            'avg_word_length': sum(len(w) for w in words) / max(len(words), 1),
        }
        
        style_guide = analyze_style(reference_text)
        
        return {
            'style_guide': style_guide,
            'metrics': metrics
        }
        
    except Exception as e:
        logger.error(f"Quick style check failed: {e}")
        raise StyleAnalysisError(f"Style check failed: {str(e)}")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Testing style analyzer...")
    print(f"Min text length: {MIN_REFERENCE_LENGTH} chars")
    print(f"Max text length: {MAX_REFERENCE_LENGTH} chars\n")
    
    sample_text = """
    Hey there! Welcome to my blog where I share cool coding tips and tricks.
    I like to keep things simple and fun. No boring technical jargon here!
    
    Today, we're diving into Python. It's awesome! 🐍
    
    Here's what you'll learn:
    • How to write clean code
    • Why readability matters
    • Some neat shortcuts
    
    Let's get started! Ready? Let's go!
    """
    
    print("Sample text:")
    print(sample_text)
    print("\n" + "="*50 + "\n")
    
    try:
        print("Analyzing style...\n")
        style_guide = analyze_style(sample_text)
        print("STYLE GUIDE:")
        print(style_guide)
        print("\n" + "="*50 + "\n")
        
        print("Quick style check...\n")
        result = quick_style_check(sample_text)
        print("METRICS:")
        for key, value in result['metrics'].items():
            print(f"  {key}: {value:.2f}")
        
    except StyleAnalysisError as e:
        print(f"❌ Failed: {e}")
