import os
from dotenv import load_dotenv
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.core import Document, VectorStoreIndex, Settings
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

# Load environment variables FIRST
load_dotenv()

Settings.llm = GoogleGenAI(
    model="gemini-flash-latest",
    api_key=os.getenv("GEMINI_API_KEY")
)

Settings.embed_model = GoogleGenAIEmbedding(
    model_name="models/text-embedding-004",
    api_key=os.getenv("GEMINI_API_KEY")
)

def analyze_style(reference_text: str):
    print("Starting the analyzing part")
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
    return str(response)

if __name__ == "__main__":
    # Read the file content, not just the path
    with open("demo/surajmahto.txt", 'r', encoding='utf-8') as f:
        test_data = f.read()
    
    data = analyze_style(test_data)
    print("Writing the style guide")
    
    with open("downloads/suraj_mahto_style.txt", 'w', encoding="utf-8") as f:
        f.write(data)