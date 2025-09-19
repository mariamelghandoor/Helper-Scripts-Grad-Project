import os
import sys
import argparse
import time
import json
from dotenv import load_dotenv

# Add the parent directory to the Python path
# This allows imports from the project root and other scripts
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(current_dir, '..')
sys.path.append(project_root)

# Import all necessary modules and the project config
from Scripts.Fetching.youtube_scraping import scrape_youtube_videos
from Scripts.Fetching.fetch_links import search_serper, save_links_to_file
from Scripts.Fetching.scrape import process_url
from Scripts.Cleaning.data_cleaner import DataCleaner
from Scripts.Schema.schema import chunk_text, analyze_text_with_gemini
from project_config import *

# Load environment variables
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

# --- Helper Functions ---
def run_cleaning_and_structuring_pipeline(input_path: str, output_name: str):
    """
    Runs the data cleaning and Gemini analysis on a given input file.
    """
    try:
        # Step 1: Read raw data
        with open(input_path, "r", encoding="utf-8") as f:
            raw_text = f.read()
        
        # Step 2: Clean the data
        cleaner = DataCleaner()
        cleaned_text = cleaner.clean_text(raw_text)
        
        # Save cleaned data to a file
        CLEANED_DIR.mkdir(parents=True, exist_ok=True)
        cleaned_file_path = CLEANED_DIR / f"{output_name}_cleaned.txt"
        with open(cleaned_file_path, "w", encoding="utf-8") as f:
            f.write(cleaned_text)
        print(f"✅ Cleaned data saved to {cleaned_file_path}")

        # Step 3: Chunk and analyze with Gemini
        text_chunks = chunk_text(cleaned_text)
        all_results = []
        for i, chunk in enumerate(text_chunks):
            print(f"\n🧠 Sending chunk {i + 1}/{len(text_chunks)} to Gemini...")
            analysis_data = analyze_text_with_gemini(chunk)
            if analysis_data:
                all_results.extend(analysis_data)
                print(f"✅ Received {len(analysis_data)} insights from chunk {i + 1}.")
            else:
                print(f"⚠️ Failed to process chunk {i + 1}. Skipping.")
            if i < len(text_chunks) - 1:
                time.sleep(2)
        
        # Step 4: Save final structured data
        SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
        output_file_path = SCHEMAS_DIR / f"{output_name}_structured.json"
        with open(output_file_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2)
        print(f"✅ Final structured data saved to {output_file_path}")

    except FileNotFoundError:
        print(f"❌ Error: The input file {input_path} was not found.")
    except Exception as e:
        print(f"❌ An error occurred during the pipeline: {e}")


# --- Main Execution Logic ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the data pipeline.")
    parser.add_argument("pipeline", choices=["youtube", "website"], help="Specify which pipeline to run (youtube or website).")
    parser.add_argument("--query", required=True, help="The search query for the pipeline.")
    
    args = parser.parse_args()

    # --- Run YouTube Pipeline ---
    if args.pipeline == "youtube":
        print("--- Starting the YouTube Pipeline ---")
        scrape_youtube_videos(args.query)
        run_cleaning_and_structuring_pipeline(YOUTUBE_TRANSCRIPT_FILE, "youtube_videos")

    # --- Run Website Pipeline ---
    elif args.pipeline == "website":
        print("--- Starting the Website Pipeline ---")
        # Step 1: Fetch links from Serper
        print(f"🔍 Searching for web links about: '{args.query}'")
        links = search_serper(args.query)
        if not links:
            print("❌ No links found. Exiting.")
        else:
            save_links_to_file(links, SCRAPED_LINKS_FILE)
            
            # Step 2: Scrape content from the fetched links
            all_scraped_text = process_url(SCRAPED_LINKS_FILE)
            
            # Save scraped data
            scraped_file_path = SCRAPED_DIR / "web_scraped_text.txt"
            SCRAPED_DIR.mkdir(parents=True, exist_ok=True)
            with open(scraped_file_path, "w", encoding="utf-8") as f:
                f.write(all_scraped_text)
            
            # Step 3: Run the cleaning and structuring pipeline
            run_cleaning_and_structuring_pipeline(scraped_file_path, "web_content")