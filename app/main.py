import os
from pydantic import BaseModel
from fastapi import FastAPI,HTTPException

from app.services.audio_downloader import simple_download
from app.services.transcriber import simple_transcribe

class VideoRequest(BaseModel):
    url : str

app = FastAPI()

@app.post("/generate-blog")
async def generate_blog(request: VideoRequest):
    try:
        print(f"Recieved request for {request.url}")
        audio_path = simple_download(request.url, output_dir='downloads')
        transcribe_path = simple_transcribe(audio_path)
        
        return {
            "status":"success",
            "audio_language": transcribe_path.get('language','unknown'),
            "video_url": request.url,
            "transcribe_text": transcribe_path['text']
        }

    except Exception as e:
        raise HTTPException(status_code=500,detail=str(e))