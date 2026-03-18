import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv

# ==========================================
# 1. SETUP & CONFIG
# ==========================================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") 

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase URL or Service Role Key in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

DOWNLOAD_DIR = "downloads"
BUCKET_NAME = "pitch-videos" # Updated to match your screenshot
MAX_FILE_SIZE_MB = 150
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# ==========================================
# 2. MASTER USER CREATION
# ==========================================
def get_or_create_master_user() -> str:
    master_email = "dataset_owner@spark2scale.com"
    master_password = "SecureData123!"
    
    print("Checking for Master Scraper User...")
    res = supabase.table("users").select("uid").eq("email", master_email).execute()
    if res.data:
        return res.data[0]['uid']
        
    print("Creating new Master Scraper User...")
    auth_response = supabase.auth.sign_up({"email": master_email, "password": master_password})
    auth_id = auth_response.user.id
    
    supabase.table("users").upsert({
        "uid": auth_id, "fname": "Dataset", "lname": "Owner", 
        "email": master_email, "user_type": "founder"
    }).execute()
    
    supabase.table("founders").insert({"user_id": auth_id}).execute()
    return auth_id

# ==========================================
# 3. NEW DATA PROCESSING & UPLOAD PIPELINE
# ==========================================
def process_pitch(json_path: str, mp4_path: str, founder_id: str):
    # STEP 1: Strict 150MB File Size Validation
    file_size_bytes = os.path.getsize(mp4_path)
    if file_size_bytes > MAX_FILE_SIZE_BYTES:
        file_size_mb = file_size_bytes / (1024 * 1024)
        print(f"\n[SKIPPED] {mp4_path} is {file_size_mb:.2f}MB (Exceeds 150MB limit)")
        return

    # Load metadata
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    video_id = data.get("video_id")
    title = data.get("title", "Untitled Pitch")
    field = data.get("field", "General")
    tags = data.get("tags", [])
    
    analysis_data = {
        "sub_tags": data.get("sub_tags", {}),
        "ideal_investor": data.get("investor_type", ""),
        "source": "YouTube Scrape"
    }

    print(f"\nProcessing: {title} ({field})")

    try:
        # STEP 2: Create Startup FIRST to generate the UUID
        startup_res = supabase.table("startups").insert({
            "startupname": title,
            "founder_id": founder_id,
            "field": field,
            "idea_description": f"A {field} startup analyzed by Spark2Scale.",
            "startup_stage": "Pre-Seed"
        }).execute()
        
        # Extract the generated UUID
        startup_id = startup_res.data[0]['sid']
        print(f"  -> Startup created. UUID: {startup_id}")

        # STEP 3: Upload Video to {startup_id} Folder
        storage_path = f"{startup_id}/{video_id}.mp4"
        
        with open(mp4_path, 'rb') as f:
            supabase.storage.from_(BUCKET_NAME).upload(
                file=f, path=storage_path, file_options={"content-type": "video/mp4", "upsert": "true"}
            )
            
        video_url = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)
        print(f"  -> Video uploaded to bucket: {storage_path}")

        # STEP 4: Unlock Workflow & Insert Pitch Deck
        supabase.table("startup_workflow").insert({
            "startup_id": startup_id,
            "idea_check": True, "market_research": True, "evaluation": True,
            "recommendation": True, "documents": True, "pitch_deck": True
        }).execute()

        supabase.table("pitchdecks").insert({
            "startup_id": startup_id,
            "pitchname": title,
            "video_url": video_url,
            "tags": tags,
            "analysis": analysis_data,
            "is_current": True,
            "canaccess": True
        }).execute()
        
        print("  -> Pitch deck record fully linked!")

    except Exception as e:
        print(f"  -> ERROR processing {video_id}: {e}")

# ==========================================
# 4. DIRECTORY WALKER
# ==========================================
def main():
    if not os.path.exists(DOWNLOAD_DIR):
        print(f"Error: Could not find '{DOWNLOAD_DIR}' directory.")
        return

    founder_id = get_or_create_master_user()
    print("\nStarting bulk upload to 'pitch-videos'...")
    
    for root, _, files in os.walk(DOWNLOAD_DIR):
        for file in files:
            if file.endswith(".json"):
                json_path = os.path.join(root, file)
                mp4_path = json_path.replace(".json", ".mp4")
                
                if os.path.exists(mp4_path):
                    process_pitch(json_path, mp4_path, founder_id)

    print("\n🎉 All valid scraped data has been successfully uploaded!")

if __name__ == "__main__":
    main()