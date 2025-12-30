import yt_dlp
import os

def simple_download(url, output_dir='downloads'):
    os.makedirs(output_dir, exist_ok= True)
    ydl_opts = {
        'format':'bestaudio/best',
        'postprocessors': [{
            'key':'FFmpegExtractAudio',
            'preferredquality':'128',
            'preferredcodec':'mp3',
        }],
        'outtmpl': os.path.join(output_dir,'%(title)s.%(ext)s'),
        'quiet':False
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        root, ext = os.path.splitext(filename)
    return root + ".mp3"

if __name__ == "__main__":
    test_url = "https://www.youtube.com/watch?v=UJCVh8px1fg"
    print(f"Downloading {test_url}")
    file_path = simple_download(test_url,'downloads')
    print(f"Downloads are saved in {file_path}")