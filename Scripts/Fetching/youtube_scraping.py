"""
Scrapes YouTube for videos, downloads audio, and transcribes
using the Whisper model.
"""

import os
import re
import time
import random
import subprocess
from pathlib import Path
import sys
from dotenv import load_dotenv

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Add the parent directory to the Python path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import all variables directly from the project's config file
from project_config import *

# Load environment variables
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# ----------------------------
# YouTube Search
# ----------------------------
def search_youtube_videos(query: str, max_results: int = 10):
    """
    Searches YouTube for videos and returns a list of dicts
    with video_id, title, and url.
    """
    api_key = os.environ.get("YOUTUBE_API_KEY")
    if not api_key:
        print("❌ Error: YOUTUBE_API_KEY environment variable not set.")
        return []

    try:
        youtube = build("youtube", "v3", developerKey=api_key)
        search_response = youtube.search().list(
            q=query,
            part="id,snippet",
            maxResults=max_results,
            type="video",
            videoDuration="short"
        ).execute()

        video_links = []
        for item in search_response.get("items", []):
            video_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            url = f"https://www.youtube.com/watch?v={video_id}"
            video_links.append({"video_id": video_id, "title": title, "url": url})
        return video_links

    except HttpError as e:
        print(f"❌ YouTube API error: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error during YouTube search: {e}")
        return []

# ----------------------------
# Helpers
# ----------------------------
def sanitize_filename(title: str) -> str:
    s = re.sub(r"[^\w\s-]", "", title)
    s = re.sub(r"\s+", "_", s).strip("_").lower()
    return s[:80]

def download_audio(video_id: str, title: str):
    """
    Downloads audio-only from a YouTube video using yt-dlp.
    Returns the path to the downloaded audio file, or None on failure.
    """
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    safe = sanitize_filename(title)
    url = f"https://www.youtube.com/watch?v={video_id}"

    out_tpl = str(AUDIO_DIR / f"{safe}.%(ext)s")

    cmd = [
        "yt-dlp", "-f", "bestaudio/best", "-o", out_tpl, "--no-playlist",
        "--extract-audio", "--audio-format", "m4a", "--audio-quality", "0",
        "--add-metadata", "--embed-metadata", url
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "yt-dlp failed")
        
        matches = list(AUDIO_DIR.glob(f"{safe}.*"))
        if matches:
            print(f"🎧 Downloaded audio → {matches[0]}")
            return str(matches[0])
        raise FileNotFoundError("Audio file not found after yt-dlp run")

    except Exception as e:
        print(f"❌ Audio download failed for '{title}': {e}")
        return None

# ----------------------------
# Whisper Transcription
# ----------------------------
def transcribe_with_whisper(audio_path: str, title: str, url: str, transcript_file_handle, failed_file_handle):
    """
    Transcribes the given audio file with OpenAI Whisper (local).
    """
    try:
        import whisper
        import torch
    except ImportError:
        print("❌ Missing dependency: please `pip install openai-whisper torch`")
        failed_file_handle.write(f"{title} - {audio_path} | Error: whisper not installed\n")
        return

    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisper.load_model("base", device=device)
        print(f"🗣️ Transcribing '{audio_path}' with Whisper on {device}...")
        result = model.transcribe(audio_path, language=None, verbose=False)

        text = result.get("text", "").strip()
        if not text:
            raise RuntimeError("Whisper returned empty transcript")
        transcript_file_handle.write(f"--- CONTENT FROM {url} ---\n\n")
        transcript_file_handle.write(f"--- Title: {title} ---\n\n")
        transcript_file_handle.write(text + "\n\n")
        print(f"✅ Appended transcript to '{YOUTUBE_TRANSCRIPT_FILE}'")

    except Exception as e:
        print(f"❌ Whisper transcription failed for '{title}': {e}")
        failed_file_handle.write(f"{title} - {audio_path} | Error: {e}\n")

# ----------------------------
# Main Orchestration
# ----------------------------
def scrape_youtube_videos(query: str):
    """Main function to orchestrate the YouTube scraping pipeline."""
    print(f"🔍 Searching for videos about: '{query}' (Duration > 20 mins)\n")
    videos = search_youtube_videos(query, max_results=MAX_YOUTUBE_RESULTS)

    if not videos:
        print("❌ No videos found. Check API key or query.")
        return

    print(f"Found {len(videos)} videos.\n")

    LINKS_DIR.mkdir(parents=True, exist_ok=True)
    with open(SCRAPED_LINKS_FILE, "w", encoding="utf-8") as f:
        for video in videos:
            f.write(f"{video['url']}\n")
    print(f"✅ Saved video links to {SCRAPED_LINKS_FILE}\n")

    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(YOUTUBE_TRANSCRIPT_FILE, "w", encoding="utf-8") as transcript_file, \
            open(YOUTUBE_FAILED_LINKS_FILE, "w", encoding="utf-8") as failed_file:
        for i, v in enumerate(videos, start=1):
            title = v["title"]
            url = v["url"]
            print(f"\n[{i}/{len(videos)}] 🎬 {title}\n→ {url}")

            audio_path = download_audio(v["video_id"], title)
            if not audio_path:
                failed_file.write(f"{title} - {url} | Error: audio download failed\n")
                continue

            time.sleep(random.randint(2, 6))
            transcribe_with_whisper(audio_path, title, url, transcript_file, failed_file)
            time.sleep(random.randint(2, 5))
    
    print(f"\n📄 Failed items (if any) saved to: {YOUTUBE_FAILED_LINKS_FILE}")
    print(f"📜 All transcripts saved to: {YOUTUBE_TRANSCRIPT_FILE}")