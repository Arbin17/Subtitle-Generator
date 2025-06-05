from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import yt_dlp
import whisper
import tempfile
import os
import srt
from datetime import timedelta
import subprocess

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

model = whisper.load_model("base")

def download_audio_from_youtube(youtube_url: str) -> str:
    temp_dir = tempfile.gettempdir()
    output_path = os.path.join(temp_dir, "yt_audio.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(youtube_url, download=True)
            downloaded_file = os.path.join(temp_dir, f"yt_audio.mp3")
            if not os.path.exists(downloaded_file):
                raise Exception("Download failed.")
            return downloaded_file
    except Exception as e:
        raise Exception(f"Download failed: {e}")

def save_upload_file_tmp(upload_file: UploadFile) -> str:
    suffix = os.path.splitext(upload_file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(upload_file.file.read())
        tmp_path = tmp.name
    return tmp_path

def convert_to_wav(input_path: str) -> str:
    output_path = input_path + ".wav"
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-vn",  # no video
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",  # mono
        output_path
    ]
    completed = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode != 0:
        raise Exception(f"ffmpeg conversion failed: {completed.stderr.decode()}")
    if not os.path.exists(output_path):
        raise Exception("ffmpeg output file not found.")
    return output_path

def generate_srt(audio_path: str) -> str:
    result = model.transcribe(audio_path)
    subtitles = []
    for i, seg in enumerate(result["segments"]):
        start = timedelta(seconds=seg["start"])
        end = timedelta(seconds=seg["end"])
        text = seg["text"].strip()
        subtitles.append(srt.Subtitle(index=i + 1, start=start, end=end, content=text))
    return srt.compose(subtitles)

@app.get("/", response_class=HTMLResponse)
def form_get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "srt_text": "", "download_url": None})

@app.post("/", response_class=HTMLResponse)
async def form_post(
    request: Request,
    youtube_url: str = Form(None),
    video_file: UploadFile = File(None)
):
    try:
        # Determine input source
        if youtube_url:
            # Download audio from YouTube
            audio_path = download_audio_from_youtube(youtube_url)
        elif video_file:
            # Save uploaded file temporarily
            audio_path = save_upload_file_tmp(video_file)
        else:
            return templates.TemplateResponse("index.html", {
                "request": request,
                "srt_text": "Error: Please provide a YouTube URL or upload a video file.",
                "download_url": None
            })

        # Convert to WAV for Whisper
        wav_path = convert_to_wav(audio_path)

        # Generate subtitles
        srt_content = generate_srt(wav_path)

        # Clean up temp files
        os.remove(audio_path)
        os.remove(wav_path)

        # Save srt file in temp dir for download
        temp_srt_path = os.path.join(tempfile.gettempdir(), "subtitles.srt")
        with open(temp_srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)

        return templates.TemplateResponse("index.html", {
            "request": request,
            "srt_text": srt_content,
            "download_url": "/download_srt"
        })

    except Exception as e:
        return templates.TemplateResponse("index.html", {
            "request": request,
            "srt_text": f"Error: {e}",
            "download_url": None
        })

@app.get("/download_srt")
def download_srt():
    path = os.path.join(tempfile.gettempdir(), "subtitles.srt")
    if os.path.exists(path):
        return FileResponse(path, media_type="text/plain", filename="subtitles.srt")
    else:
        return {"error": "Subtitle file not found."}
