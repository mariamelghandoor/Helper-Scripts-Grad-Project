import os
import json
import time
from urllib.parse import urlparse
from dotenv import load_dotenv
import google.generativeai as genai
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- Configuration ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("❌ Error: GEMINI_API_KEY not found in .env file.")
    exit()
genai.configure(api_key=GEMINI_API_KEY)

# --- Robust Path Configuration ---
# Get the absolute path of the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Navigate up two directories to get to the project root (e.g., 'SCRAPER')
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../../"))

# Build absolute paths to the data files from the project root
INPUT_FILENAME = os.path.join(PROJECT_ROOT, "Data", "StartupNames", "yc_startup_names.txt")
OUTPUT_FILENAME = os.path.join(PROJECT_ROOT, "Data", "Schemas", "yc_enriched_data.json")
# Checkpoint file will be created in the same directory as the script
CHECKPOINT_FILENAME = os.path.join(SCRIPT_DIR, "checkpoint.json")


def get_domain_info(url):
    """Parses a URL to extract domain and subdomain."""
    if not url or not url.startswith(('http://', 'https://')):
        return "N/A", "N/A"
    try:
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname
        if not hostname:
            return "N/A", "N/A"
            
        parts = hostname.split('.')
        # Handle common TLDs like .co.uk
        if len(parts) > 2 and parts[-2] in ('co', 'com', 'org', 'net'):
             domain = '.'.join(parts[-3:])
             subdomain = '.'.join(parts[:-3]) if len(parts) > 3 else "N/A"
        elif len(parts) > 2 and parts[0] != 'www':
            subdomain = parts[0]
            domain = '.'.join(parts[1:])
        else:
            domain = '.'.join(parts[-2:]) if len(parts) > 1 else hostname
            subdomain = "N/A"
        
        if subdomain == 'www':
            subdomain = 'N/A'

        return domain, subdomain
    except Exception as e:
        print(f"Could not parse URL {url}: {e}")
        return "N/A", "N/A"

def analyze_and_structure_data(company_name, scraped_text):
    """
    Uses the Gemini API to research the company on the web and structure the findings.
    """
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    
    prompt = f"""
    You are a world-class startup analyst. Your primary task is to conduct web research on the Y Combinator startup named '{company_name}' and populate a JSON object with your findings.

    Use information from news articles, press releases, company websites, social media, and any available public post-mortems to find the most accurate and detailed information.

    The text scraped from the company's YC profile page is provided below for initial context. You should verify and supplement this with your external research, especially for fields like "Reason" and "Takeaway". Do not rely solely on the provided text.

    Scraped Context:
    ---
    {scraped_text if scraped_text else 'No text was scraped from the YC page.'}
    ---

    Now, based on your comprehensive web research, populate the following JSON schema. Be thorough and accurate.

    - For 'success_or_fail', determine if the company is currently operational ('Success'), has been acquired ('Success'), or has shut down ('Fail').
    - For 'Reason' and 'Takeaway', provide a concise summary of why the company succeeded or failed based on public information.
    - If you cannot find specific information for a field after searching, use the value "N/A". Do not leave required fields empty.

    Return ONLY the completed, valid JSON object, with no other text, explanations, or markdown formatting.

    JSON Schema to populate:
    {{
        "Link": "STRING",
        "Domain": "STRING",
        "Sub_domain": "STRING",
        "Idea": "STRING",
        "Description": "STRING",
        "success_or_fail": "STRING (Success or Fail)",
        "Reason": "STRING",
        "Takeaway": "STRING",
        "Region": "STRING",
        "Tags": ["ARRAY", "OF", "STRINGS"]
    }}
    """

    try:
        response = model.generate_content(prompt)
        # Clean the response to ensure it's valid JSON
        json_text = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(json_text)
        
        # Post-process domain and subdomain from the link the AI found
        link = data.get("Link", "N/A")
        domain, sub_domain = get_domain_info(link)
        data["Domain"] = domain
        data["Sub_domain"] = sub_domain

        return data
    except Exception as e:
        print(f"An error occurred during Gemini API call for {company_name}: {e}")
        print(f"Raw response was: {response.text if 'response' in locals() else 'No response'}")
        return None

def scrape_company_page_text(driver, company_name):
    """
    Scrapes all visible text from a single YC company page to use as context.
    """
    slug = company_name.lower().replace(' ', '-')
    url = f"https://www.ycombinator.com/companies/{slug}"
    print(f"Scraping page for context: {url}")
    
    try:
        driver.get(url)
        # Wait for the main content to be loaded, identifiable by the h1 tag for the company name
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        # Extract all text from the body
        body_text = driver.find_element(By.TAG_NAME, 'body').text
        return body_text
    except Exception as e:
        print(f"Could not scrape YC page for '{company_name}'. It might be delisted. Continuing with web research only. Error: {e}")
        return None

def load_checkpoint():
    """Loads the last processed company index and results from a checkpoint file."""
    if os.path.exists(CHECKPOINT_FILENAME):
        with open(CHECKPOINT_FILENAME, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"last_index": -1, "results": []}

def save_checkpoint(last_index, results):
    """Saves the current progress to a checkpoint file."""
    with open(CHECKPOINT_FILENAME, 'w', encoding='utf-8') as f:
        json.dump({"last_index": last_index, "results": results}, f, indent=4)

if __name__ == "__main__":
    if not os.path.exists(INPUT_FILENAME):
        print(f"❌ Error: Input file '{INPUT_FILENAME}' not found. Please run the name scraper first.")
        exit()

    with open(INPUT_FILENAME, 'r', encoding='utf-8') as f:
        company_names = [line.strip() for line in f if line.strip()]

    # Load progress
    checkpoint = load_checkpoint()
    last_processed_index = checkpoint['last_index']
    all_results = checkpoint['results']
    
    start_index = last_processed_index + 1
    
    if start_index >= len(company_names):
        print("✅ All companies have already been processed.")
    else:
        print(f"Resuming from company {start_index + 1} of {len(company_names)}...")

    # Setup Selenium WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        for i in range(start_index, len(company_names)):
            company = company_names[i]
            print(f"\n--- Processing {i+1}/{len(company_names)}: {company} ---")
            
            # Scrape the YC page for initial context, but don't fail if it's not found
            scraped_data = scrape_company_page_text(driver, company)
            
            # The analysis function will now perform the main web research
            structured_data = analyze_and_structure_data(company, scraped_data)
            
            if structured_data:
                all_results.append(structured_data)
                print(f"✅ Successfully researched and structured data for {company}.")
            
            # Save checkpoint after each company
            save_checkpoint(i, all_results)
            time.sleep(1) # Be respectful to the server and API rate limits

        # Final save to the main output file
        # Ensure the output directory exists before saving
        output_dir = os.path.dirname(OUTPUT_FILENAME)
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"\nEnrichment complete. Saving all {len(all_results)} results to '{OUTPUT_FILENAME}'...")
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=4)
        
        print(f"\n✅ Success! All data saved to '{OUTPUT_FILENAME}'")
        # Clean up checkpoint file on successful completion
        if os.path.exists(CHECKPOINT_FILENAME):
            os.remove(CHECKPOINT_FILENAME)

    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}. Progress has been saved.")
    finally:
        if driver:
            driver.quit()

