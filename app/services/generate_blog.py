import os
from dotenv import load_dotenv
from llama_index.core import Document, VectorStoreIndex, Settings
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
import shutil

load_dotenv()

Settings.llm= GoogleGenAI(
    model="gemini-flash-latest",
    api_key= os.getenv("GEMINI_API_KEY")
)

Settings.embed_model= GoogleGenAIEmbedding(
    model_name="models/text-embedding-004",
    api_key=os.getenv("GEMINI_API_KEY")
)

def generate_blog_from_transcript(transcription: str):
    print("Generating the blog....")
    document = Document(text=transcription)
    index = VectorStoreIndex.from_documents([document])
    query_engine = index.as_query_engine()
    prompt = (
        "You are an expert technical writer. "
        "Take the following video transcript and convert it into a well-structured blog post "
        "in Markdown format. "
        "Include a 'Key Takeaways' section. "
        "Tone: Professional but easy to read."
    )
    response = query_engine.query(prompt)
    print("Asking Gemini Flash to write the blog...")
    return str(response)

with open("downloads/transcription1.txt",'r', encoding="utf-8") as f:
    file_data = f.read()

if __name__ == "__main__":
   try:
        with open("downloads/transcription1.txt", 'r', encoding="utf-8") as f:
            file_data = f.read()
        
        final_output = generate_blog_from_transcript(file_data)
        print(final_output)
        with open("downloads/generated_blog.txt",'w',encoding="utf-8") as d:
            d.write(final_output)
            shutil.copyfile("generated_blog.txt","generated_blog.md")
   except FileNotFoundError:
        print("Error: 'downloads/transcription1.txt' not found. Did you run the transcriber first?")
