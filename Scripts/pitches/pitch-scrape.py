import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()
import os
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import yt_dlp

# ==========================================
# 1. INIT & CONFIG
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
# Using flash for fast, cheap, and highly accurate JSON generation
model = genai.GenerativeModel('gemini-2.5-flash')
FIELDS = ["supply chain tech"
]
TARGET_VIDEOS_PER_FIELD = 10
DOWNLOAD_DIR = "downloads"
HISTORY_FILE = os.path.join(DOWNLOAD_DIR, "history.txt")
MAX_WORKERS = 3 

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ==========================================
# 2. HISTORY TRACKING LOGIC
# ==========================================
def load_history() -> set:
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, 'r') as f:
        return set(line.strip() for line in f)

def mark_as_seen(video_id: str):
    with open(HISTORY_FILE, 'a') as f:
        f.write(f"{video_id}\n")

seen_videos = load_history()

# ==========================================
# 3. METADATA PIPELINE (Mocked)
# ==========================================
def extract_transcript(audio_path: str) -> str:
    return "Simulated transcript of the founder explaining their startup..."

def agentic_evaluation_pipeline(title: str, field: str) -> dict:
    """Uses an LLM to dynamically generate tags based on the video title and field."""
    
    prompt = f"""
    You are an expert venture capitalist analyst. I am giving you the title of a 1-minute startup pitch video.
    
    Video Title: "{title}"
    Industry/Field: {field}
    
    Analyze this title and generate a JSON object with the following structure:
    {{
        "tags": ["list 2 to 3 relevant, highly specific tags"],
        "sub_tags": {{
            "tag1": ["list 2 sub-tags related to tag1"],
            "tag2": ["list 2 sub-tags related to tag2"]
        }},
        "investor_type": "Name the specific type of investor who would fund this (e.g., Deep Tech VC, Angel Investor, Seed Fund, Corporate VC)"
    }}
    
    Return ONLY valid JSON. Do not include markdown formatting or extra text.
    """
    
    try:
        response = model.generate_content(prompt)
        
        # Clean up the response in case the LLM adds markdown formatting like ```json
        clean_text = response.text.strip('` \n')
        if clean_text.startswith('json'):
            clean_text = clean_text[4:]
            
        metadata = json.loads(clean_text)
        return metadata
        
    except Exception as e:
        logging.error(f"AI Tagging failed for '{title}': {e}")
        # Return a fallback if the AI fails or hits a rate limit
        return {
            "tags": [field, "startup"],
            "sub_tags": {field: ["general pitch"]},
            "investor_type": "General Investor"
        }

# ==========================================
# 4. OFFLINE STORAGE LOGIC
# ==========================================
def count_valid_videos(field_dir: str) -> int:
    if not os.path.exists(field_dir):
        return 0
    return len([f for f in os.listdir(field_dir) if f.endswith('.mp4')])

def save_metadata_offline(video_id: str, title: str, field: str, field_dir: str, metadata: dict):
    json_path = os.path.join(field_dir, f"{video_id}.json")
    record = {
        "video_id": video_id,
        "title": title,
        "field": field,
        "tags": metadata['tags'],
        "sub_tags": metadata['sub_tags'],
        "investor_type": metadata['investor_type']
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(record, f, indent=4, ensure_ascii=False)

# ==========================================
# 5. CORE PROCESSING WORKER
# ==========================================
def process_field(field: str):
    field_dir = os.path.join(DOWNLOAD_DIR, field)
    os.makedirs(field_dir, exist_ok=True)
    
    existing_count = count_valid_videos(field_dir)
    videos_needed = TARGET_VIDEOS_PER_FIELD - existing_count
    
    if videos_needed <= 0:
        logging.info(f"[{field.upper()}] Already has {existing_count} videos. Skipping.")
        return

    logging.info(f"[{field.upper()}] Needs {videos_needed} more videos. Searching...")

    ydl_opts = {
        'format': 'best',
        'outtmpl': f'{field_dir}/%(id)s.%(ext)s',
        'match_filter': yt_dlp.utils.match_filter_func("duration > 30 & duration <= 60"),
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True, # Keep this to ignore dead videos!
    }

    # NEW: A list of diverse search prompts to cast a wider net
    search_templates = [
        "'{field} startup pitch'",
        "'{field} elevator pitch'",
        "'{field} demo day pitch'",
        "'1 minute {field} pitch'",
        "'{field} pitch competition'"
    ]

    downloaded_this_session = 0

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # Loop through our different search prompts
        for template in search_templates:
            if downloaded_this_session >= videos_needed:
                break # Stop searching if we hit the target
                
            query_str = template.format(field=field)
            search_query = f"ytsearch{TARGET_VIDEOS_PER_FIELD * 5}:{query_str}"
            
            logging.info(f"[{field.upper()}] Trying search query: {query_str}")
            
            try:
                info = ydl.extract_info(search_query, download=False)
                if not info or 'entries' not in info:
                    continue # Try the next prompt

                for entry in info['entries']:
                    if downloaded_this_session >= videos_needed:
                        break
                    
                    if not entry:
                        continue

                    duration = entry.get('duration', 0)
                    if duration <= 30 or duration > 60:
                        continue

                    video_id = entry.get('id')
                    title = entry.get('title')

                    if video_id in seen_videos:
                        continue

                    try:
                        logging.info(f"[{field.upper()}] Downloading new pitch ({duration}s): {title}")
                        ydl.download([entry.get('webpage_url')])
                        file_path = os.path.join(field_dir, f"{video_id}.mp4")

                        seen_videos.add(video_id)
                        mark_as_seen(video_id)

                        if os.path.exists(file_path):
                            transcript = extract_transcript(file_path)
                            metadata = agentic_evaluation_pipeline(title, field)
                            
                            if metadata:
                                save_metadata_offline(video_id, title, field, field_dir, metadata)
                                downloaded_this_session += 1
                            else:
                                logging.info(f"[{field.upper()}] Video {video_id} failed AI validation. Trashing.")
                                os.remove(file_path)
                                
                    except Exception as e:
                        logging.warning(f"[{field.upper()}] Failed to process video {video_id}. Error: {e}")
                        continue

            except Exception as e:
                logging.error(f"Error executing search '{search_query}': {e}")
                continue # Move to the next prompt in the list
# ==========================================
# 6. EXECUTION ENTRY POINT
# ==========================================
def main():
    logging.info("Starting Resilient Startup Pitch Pipeline (30s-60s)...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_field, field): field for field in FIELDS}
        for future in as_completed(futures):
            future.result()

if __name__ == "__main__":
    main()