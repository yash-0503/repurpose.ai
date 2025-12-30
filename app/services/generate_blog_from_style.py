import os
from dotenv import load_dotenv
from llama_index.core import Document, VectorStoreIndex, Settings
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding

load_dotenv()

Settings.llm= GoogleGenAI(
    model="gemini-flash-latest",
    api_key= os.getenv("GEMINI_API_KEY")
)

Settings.embed_model= GoogleGenAIEmbedding(
    model_name="models/text-embedding-004",
    api_key=os.getenv("GEMINI_API_KEY")
)

def generate_blog_from_transcript(transcription: str, style_guide: str):
    print("Generating the blog with style matching...")
    document = Document(text=transcription)
    index = VectorStoreIndex.from_documents([document])
    query_engine = index.as_query_engine()

    # We make the structure MANDATORY
    structure_instructions = (
        "TASK: You are an expert Blog Editor. Rewrite the following video transcript into a structured HTML/Markdown Blog Post.\n"
        "MANDATORY STRUCTURE:\n"
        "1. A Catchy Title (H1)\n"
        "2. A 'Key Takeaways' bulleted list at the top.\n"
        "3. Use H2 Headings for every major topic change.\n"
        "4. Conclusion.\n"
    )

    if style_guide:
        print(f"Applying Style Guide...")
        prompt = (
            f"{structure_instructions}\n"
            "--- VOICE & TONE INSTRUCTIONS ---\n"
            "While keeping the structure above, you must write in the specific voice described below:\n"
            f"{style_guide}\n"
            "IMPORTANT: Do not just copy the transcript. You must REWRITE it as a written article, "
            "but keep the author's conversational tone and jargon (like SSB, AFCAT).\n"
            "---------------------------------\n"
        )
    else:
        prompt = structure_instructions + "Tone: Professional but easy to read."
        
    response = query_engine.query(prompt)
    print("Gemini has finished writing.")
    return str(response)



if __name__ == "__main__":
    print("Reading the transcript Data...")
    with open("demo/surajmahto.txt",'r', encoding="utf-8") as f:
        transcript_data= f.read()
    print("Reading the style Data...")
    with open("demo/suraj_mahto_style.txt",'r', encoding="utf-8") as d:
        style_data= d.read()
    data = generate_blog_from_transcript(transcript_data,style_data)
    with open("demo/final_blog1.txt","w",encoding="utf-8") as s:
        s.write(data)

