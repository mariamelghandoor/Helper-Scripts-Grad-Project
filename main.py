"""Main pipeline orchestrator for data scraping and structuring."""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from config import config
from website_scraper import scrape_website
from youtube_scraper import scrape_youtube_videos
from data_cleaner import clean_data
from gemini_structurer import structure_with_gemini

def run_website_pipeline(url):
    """Run complete pipeline for website scraping."""
    print(f"Starting website pipeline for: {url}")
    
    # Step 1: Scrape website
    print("\n=== Step 1: Scraping Website ===")
    scrape_website(url)
    
    # Step 2: Clean data
    print("\n=== Step 2: Cleaning Data ===")
    chunks = clean_data()
    
    # Step 3: Structure with Gemini
    print("\n=== Step 3: Structuring with Gemini ===")
    structured_data = structure_with_gemini(chunks)
    
    print(f"\n✅ Pipeline completed! {len(structured_data)} insights extracted.")
    return structured_data

def main():
    """Main function with hardcoded URL."""
    try:
        # Replace this URL with your target website
        url = "https://www.ycombinator.com/companies/doordash"
        run_website_pipeline(url)
    except Exception as e:
        print(f"Pipeline failed: {e}")
        return 1
    return 0

if __name__ == "__main__":
    exit(main())