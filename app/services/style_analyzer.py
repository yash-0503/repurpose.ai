import os
from dotenv import load_dotenv
from llama_index.core import Settings

# Load environment variables
load_dotenv()

# Lazy initialization flag
_initialized = False

def _ensure_initialized():
    """Lazy initialization of LLM - only when first needed."""
    global _initialized
    if _initialized:
        return
    
    from llama_index.llms.google_genai import GoogleGenAI
    from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set in environment")
    
    # Use gemini-2.5-flash (Jan 2025 - replaced 1.5-flash)
    Settings.llm = GoogleGenAI(
        model="gemini-2.5-flash",
        api_key=api_key
    )
    
    Settings.embed_model = GoogleGenAIEmbedding(
        model_name="text-embedding-004",
        api_key=api_key
    )
    
    _initialized = True
    print("✅ Style analyzer LLM initialized")


def analyze_style(reference_text: str):
    """Analyze writing style from reference text and return a style guide."""
    _ensure_initialized()
    
    print("📝 Analyzing writing style...")
    
    style_prompt = (
        "You are an expert literary analyst. "
        "Read the following text samples written by an author. "
        "Analyze their writing style deeply. Focus on:\n"
        "1. Tone (Casual, Academic, Humorous?)\n"
        "2. Sentence Structure (Short & punchy? Long & complex?)\n"
        "3. Vocabulary (Simple words? Jargon?)\n"
        "4. Formatting quirks (Uses emojis? Bullet points?)\n\n"
        "Output a concise 'Style Guide' paragraph that describes exactly how to write like this author."
        f"\n\n--- TEXT SAMPLES ---\n{reference_text[:10000]}"
    )

    response = Settings.llm.complete(style_prompt)
    print("✅ Style analysis complete")
    return str(response)


if __name__ == "__main__":
    # Read the file content, not just the path
    with open("demo/surajmahto.txt", 'r', encoding='utf-8') as f:
        test_data = f.read()
    
    data = analyze_style(test_data)
    print("Writing the style guide")
    
    with open("downloads/suraj_mahto_style.txt", 'w', encoding="utf-8") as f:
        f.write(data)
