import whisper
import os
model_type="base"
model = whisper.load_model(model_type)

def simple_transcribe(filepath: str) -> dict:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File Path didnt exist {filepath}")
    print(f"Transcribing the video at {filepath}")
    result = model.transcribe(filepath, fp16=False)
    return result

if __name__ == "__main__":
    test_file = "downloads/Indian Air Force Selection Journey ✈️ ｜ SSB, AFCAT, Govt Exam Reality & Roadmap ｜ ft.Krunal Badgujar.mp3"
    data = simple_transcribe(test_file)
    with open('downloads/surajmahto.txt','w',encoding="utf-8") as f:
        f.write(data["text"])
