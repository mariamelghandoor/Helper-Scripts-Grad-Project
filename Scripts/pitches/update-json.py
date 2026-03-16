import os
import json
import time
import logging
import google.generativeai as genai
from dotenv import load_dotenv

# ==========================================
# 1. SETUP & CONFIG
# ==========================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()
# Make sure your GEMINI_API_KEY is in your .env file
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

DOWNLOAD_DIR = "downloads"

TAXONOMY = {
    "Deep Tech & AI": [
        "Artificial Intelligence", "Robotics", "Space Tech", 
        "Quantum Computing", "Advanced Materials", "Computer Vision"
    ],
    "Enterprise Software": [
        "SaaS", "B2B SaaS", "Cybersecurity", 
        "Supply Chain Tech", "Cloud Infrastructure", "Automation"
    ],
    "Healthcare & Life Sciences": [
        "Healthcare", "Biotech", "Digital Health", 
        "Mental Health Tech", "Genomics", "Medical Devices"
    ],
    "Financial Technology": [
        "Fintech", "Blockchain", "Crypto/DeFi", 
        "Insurtech", "Wealthtech", "Payments"
    ],
    "Sustainability & Energy": [
        "Clean Energy", "Climate Tech", "Circular Economy", 
        "Waste Management", "Smart Mobility"
    ],
    "Agriculture & Food": [
        "Agritech", "FoodTech", "Alternative Proteins", 
        "Precision Farming"
    ],
    "Consumer & Commerce": [
        "E-commerce", "Creator Economy", "Consumer Social", 
        "Wearables", "Marketplace"
    ],
    "Specialized Industry Tech": [
        "Edtech", "Proptech", "Legaltech", 
        "HR Tech", "Traveltech"
    ]
}
# ==========================================
# 2. AI GENERATION
# ==========================================
def generate_new_metadata(title: str, field: str, taxonomy_str: str) -> dict:
    prompt = f"""
    You are an expert venture capitalist analyst categorizing startup pitches. 
    I am giving you the title of a 1-minute startup pitch video.
    
    Video Title: "{title}"
    Industry/Field: {field}
    
    CRITICAL RULES FOR TAGGING:
    1. You MUST select 1 to 3 "tags" ONLY from the top-level keys in the ALLOWED TAXONOMY below.
    2. For each tag you select, you MUST select 1 to 2 "sub_tags" ONLY from the corresponding list in the ALLOWED TAXONOMY.
    3. DO NOT invent, guess, or create any new tags or sub-tags. You are strictly limited to the options provided.
    
    ALLOWED TAXONOMY:
    {taxonomy_str}
    
    Output ONLY a valid JSON object using this exact structure:
    {{
        "tags": ["SelectedTag1", "SelectedTag2"],
        "sub_tags": {{
            "SelectedTag1": ["SelectedSubTagA", "SelectedSubTagB"],
            "SelectedTag2": ["SelectedSubTagC"]
        }},
        "investor_type": "Name the specific type of investor who would fund this"
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.strip('` \n')
        if clean_text.lower().startswith('json'):
            clean_text = clean_text[4:]
        return json.loads(clean_text)
    except Exception as e:
        logging.error(f"AI Tagging failed for '{title}': {e}")
        return None

# ==========================================
# 3. DIRECTORY WALKER & UPDATER
# ==========================================
def update_legacy_jsons():
    if not os.path.exists(DOWNLOAD_DIR):
        logging.error(f"Directory '{DOWNLOAD_DIR}' not found.")
        return

    updated_count = 0
    
    logging.info("Scanning for JSON files with legacy mock data...")
    
    # Walk through all folders and subfolders
    for root, _, files in os.walk(DOWNLOAD_DIR):
        for file in files:
            if file.endswith(".json"):
                file_path = os.path.join(root, file)
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        logging.error(f"Could not read {file_path}. Skipping.")
                        continue

                # Check if this JSON still has the old mock investor type or tags
                if data.get("investor_type") == "Seed Stage Venture Capital" and "b2b" in data.get("tags", []):
                    title = data.get("title", "")
                    field = data.get("field", "")
                    
                    logging.info(f"Updating metadata for: {title}")
                    
                    new_metadata = generate_new_metadata(title, field, json.dumps(TAXONOMY))
                    
                    if new_metadata:
                        # Safely update the dictionary with the new AI data
                        data["tags"] = new_metadata.get("tags", data.get("tags"))
                        data["sub_tags"] = new_metadata.get("sub_tags", data.get("sub_tags"))
                        data["investor_type"] = new_metadata.get("investor_type", data.get("investor_type"))
                        
                        # Overwrite the file with the fresh data
                        with open(file_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=4, ensure_ascii=False)
                            
                        updated_count += 1
                        
                        # Crucial: Sleep for 2 seconds to avoid hitting API rate limits
                        time.sleep(2) 
                    else:
                        logging.warning(f"Failed to generate new metadata for {file}.")

    logging.info(f"Finished! Successfully updated {updated_count} JSON files.")

if __name__ == "__main__":
    update_legacy_jsons()