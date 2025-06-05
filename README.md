# 🎬 YouTube Subtitle Generator

Generate `.srt` subtitles from **YouTube videos** or **uploaded video/audio files** using OpenAI Whisper + FastAPI.

---

## 📌 Features

- ✅ Paste a YouTube link and auto-generate subtitles
- ✅ Upload your own video/audio file
- ✅ Outputs clean `.srt` subtitle files
- ✅ Browser-based UI with live preview
- ✅ Downloadable subtitles file

---

## ⚙️ Installation

### 🔧 Prerequisites

- Python 3.8+
- `ffmpeg` (must be installed and added to your system PATH)
- `git` (to clone this repo)

### 🧱 Setup

```bash
git clone https://github.com/Arbin17/Subtitle-Generator
cd youtube-subtitle-generator
python -m venv venv
source venv/bin/activate    # On Windows use: venv\Scripts\activate
pip install -r requirements.txt
