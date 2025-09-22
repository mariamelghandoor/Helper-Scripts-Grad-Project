import os
import sys
import argparse
import time
import json
from dotenv import load_dotenv
from urllib.parse import urlparse

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
from Scripts.Cleaning.remove import remove_invalid_files
from project_config import *
from Scripts.project_config import *
from Scripts.Database.supabase_client import bulk_insert_from_json

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

if __name__ == "__main__":
    # Create all required directories at startup
    for directory in [SCRAPED_DIR, CLEANED_DIR, SCHEMAS_DIR, LINKS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
    
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
            
            # Read URLs from the saved links file
            try:
                with open(SCRAPED_LINKS_FILE, "r", encoding="utf-8") as f:
                    urls = [line.strip() for line in f if line.strip()]
            except FileNotFoundError:
                print("❌ Links file not found. Exiting.")
                sys.exit()

            print(f"🚀 Found {len(urls)} links to scrape.")
            SCRAPED_DIR.mkdir(parents=True, exist_ok=True)
            
            scraped_files_to_process = []
            for url in urls:
                scraped_text, _ = process_url(url)
                
                if scraped_text:
                    safe_filename = urlparse(url).netloc.replace('.', '_') + "_" + str(time.time()).replace('.', '')
                    scraped_file_path = SCRAPED_DIR / f"{safe_filename}.txt"
                    
                    with open(scraped_file_path, "w", encoding="utf-8") as f:
                        f.write(scraped_text)
                    
                    scraped_files_to_process.append(scraped_file_path)
                    print(f"✅ Scraped data for {url} saved to {scraped_file_path}")
                else:
                    print(f"⚠️ Skipping URL due to scraping error: {url}")
            
            if scraped_files_to_process:
                # Step 2.5: Remove invalid files from the scraped directory
                print("\n🧹 Starting file validation and cleanup...")
                # SCRAPED_DIR is a pathlib.Path object, so convert it to a string for the function
                remove_invalid_files(str(SCRAPED_DIR))
                print("✅ File cleanup completed.")
                
                # Re-read the list of files to process after invalid ones are removed
                final_files_to_process = [
                    file_path for file_path in scraped_files_to_process 
                    if os.path.exists(file_path)
                ]
                
                if final_files_to_process:
                    # Run the cleaning and structuring pipeline for each file
                    for file_path in final_files_to_process:
                        file_name = file_path.stem 
                        print(f"\n--- Processing scraped file: {file_name} ---")
                        run_cleaning_and_structuring_pipeline(file_path, file_name)
                else:
                    print("❌ No valid files remaining after cleanup. Exiting pipeline.")
            else:
                print("❌ No content was successfully scraped. Exiting pipeline.")
    
    # After processing is complete, upload to Supabase
    print("\n Uploading analyzed data to Supabase...")
    schema_files = list(SCHEMAS_DIR.glob('*_structured.json'))
    
    for schema_file in schema_files:
        print(f"\nUploading {schema_file.name}...")
        if bulk_insert_from_json(schema_file):
            print(f"✅ Successfully uploaded {schema_file.name}")
        else:
            print(f"❌ Failed to upload {schema_file.name}")