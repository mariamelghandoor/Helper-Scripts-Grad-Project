# project_config.py
from pathlib import Path

# Get the absolute path to the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent

# --- Directories ---
DATA_DIR = PROJECT_ROOT / "Data"
SCRIPTS_DIR = PROJECT_ROOT / "Scripts"
CLEANED_DIR = DATA_DIR / "cleaned"
TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
SCRAPED_DIR = DATA_DIR / "scraped"
SCHEMAS_DIR = DATA_DIR / "schemas"
AUDIO_DIR = DATA_DIR / "audio"
LINKS_DIR = DATA_DIR / "links"

# --- File Paths ---
YOUTUBE_TRANSCRIPT_FILE = TRANSCRIPTS_DIR / "youtube_transcript.txt"
YOUTUBE_FAILED_LINKS_FILE = TRANSCRIPTS_DIR / "youtube_failed_links.txt"
SCRAPED_LINKS_FILE = LINKS_DIR / "links.txt"

# --- Pipeline Settings ---
CHUNK_SIZE_FOR_ANALYSIS = 4000
MAX_YOUTUBE_RESULTS = 1