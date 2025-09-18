import json
import os
import requests
import time
from datetime import datetime
from dotenv import load_dotenv

def chunk_text(text: str, max_chunk_size: int = 4000) -> list[str]:
    """
    Splits the scraped text into smaller, more manageable chunks.
    The max_chunk_size has been further reduced to prevent timeouts.
    """
    print("Splitting text into smaller chunks for analysis...")
    articles = text.split('\n\n--- CONTENT FROM ')
    chunks = []
    current_chunk = ""

    if not articles[0].strip().startswith("--- CONTENT FROM"):
        if articles[0].strip():
             current_chunk = f"--- CONTENT FROM [assumed start]\n\n{articles.pop(0)}"
    
    for article in articles:
        # Re-add the separator that was removed by split()
        full_article_text = f"--- CONTENT FROM {article}"
        if len(current_chunk) + len(full_article_text) > max_chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = ""
        
        # If the chunk is empty, it means the article itself is larger than the max size.
        # We start the chunk with this large article. It might still fail, but this is a graceful way to handle it.
        if not current_chunk:
            current_chunk = full_article_text
        else:
            current_chunk += "\n\n" + full_article_text

    if current_chunk:
        chunks.append(current_chunk)
    
    print(f"Split text into {len(chunks)} chunk(s).")
    return chunks

def analyze_text_with_gemini(text_chunk: str) -> list:
    """
    Analyzes a single chunk of text using the Gemini 2.5 Flash model,
    with a faster retry mechanism to handle timeouts.
    """
    # Read the API key from the environment variable
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY not found.")
        print("Please ensure it is set in your .env file and you have run 'pip install python-dotenv'.")
        return None

    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={api_key}"
    json_schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "Link": {"type": "STRING"}, "Domain": {"type": "STRING"}, "Sub_domain": {"type": "STRING"},
                "Idea": {"type": "STRING"}, "Description": {"type": "STRING"},
                "success_or_fail": {"type": "STRING"}, "Reason": {"type": "STRING"},
                "Takeaway": {"type": "STRING"}, "Region": {"type": "STRING"},
                "Tags": {"type": "ARRAY", "items": {"type": "STRING"}}
            },
            "required": ["Link", "Idea", "Description", "Takeaway", "Domain"]
        }
    }
    prompt = (
    "Act as a meticulous business analyst and venture capital expert. Your task is to identify and extract **only** information related to specific business or startup ideas, case studies of businesses (either successful or failed), or analyses of a company's performance. "
    "Ignore generic articles, 'how-to' guides, or lists that do not describe a specific company, business model, or a success/failure case. "
    "For each distinct startup idea or case study found in the text, extract the information and structure it as a JSON object according to the provided schema. "
    "Each full article is preceded by '--- CONTENT FROM' and its URL. Use the URL for the 'Link', 'Domain', and 'Sub_domain' fields. "
    "If an entry is just a title with metadata, use the title for both the 'Idea' and 'Description' fields. For these short entries, fields like 'Reason' and 'Takeaway' will be null. "
    "If no relevant startup idea or case study can be found in a chunk of text, you MUST return an empty JSON array `[]`."
    "If a specific piece of information for any field cannot be found in the text, you MUST use `null` as its value. Here is the text:\n\n"
    f"{text_chunk}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": json_schema},
    }

    # --- Retry logic with exponential backoff ---
    max_retries = 3
    base_delay = 2  # Reduced delay
    for attempt in range(max_retries):
        try:
            response = requests.post(
                api_url, headers={"Content-Type": "application/json"}, json=payload, timeout=60 # Reduced timeout
            )
            response.raise_for_status()
            result = response.json()
            candidate = result.get("candidates", [])[0]
            json_text = candidate.get("content", {}).get("parts", [])[0].get("text", "[]")
            return json.loads(json_text)
        except requests.exceptions.Timeout:
            print(f"  -> ⏳ Request timed out. Retrying in {base_delay}s... (Attempt {attempt + 1}/{max_retries})")
            time.sleep(base_delay)
            base_delay *= 2  # Increase delay for next retry
        except requests.exceptions.RequestException as e:
            print(f"  -> ❌ API request error: {e}")
            return None # Don't retry on other HTTP errors
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            print(f"  -> ❌ Could not parse API response: {e}")
            return None
    
    print("  -> ❌ API request failed after multiple retries.")
    return None

# --- Main execution ---
if __name__ == "__main__":
    # --- Robust Path Handling ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    dotenv_path = os.path.join(project_root, '.env')
    
    print(f"Attempting to load .env file from: {dotenv_path}")
    load_dotenv(dotenv_path=dotenv_path)

    scraped_dir = os.path.join(project_root, "Data", "Cleaned")
    schemas_dir = os.path.join(project_root, "Data", "Schemas")

    os.makedirs(scraped_dir, exist_ok=True)
    os.makedirs(schemas_dir, exist_ok=True)

    # Find all scraped text files
    scraped_files = [f for f in os.listdir(scraped_dir) if f.endswith(".txt")]

    if not scraped_files:
        print("❌ No scraped text files found in the Scraped directory. Run the scraper first.")
    else:
        print(f"📂 Found {len(scraped_files)} scraped file(s) to analyze.")

        for scraped_file in scraped_files:
            input_path = os.path.join(scraped_dir, scraped_file)
            base_name = os.path.splitext(scraped_file)[0]
            output_file = os.path.join(schemas_dir, f"{base_name}_analysis.json")

            print(f"\n📖 Reading content from '{input_path}'...")
            with open(input_path, "r", encoding="utf-8") as f:
                scraped_text = f.read()

            if not scraped_text.strip():
                print(f"⚠️ Skipping '{scraped_file}' (empty file).")
                continue

            text_chunks = chunk_text(scraped_text)
            all_results = []

            for i, chunk in enumerate(text_chunks):
                print(f"\n🧠 Sending chunk {i + 1}/{len(text_chunks)} from '{scraped_file}' to Gemini...")
                analysis_data = analyze_text_with_gemini(chunk)

                if analysis_data:
                    all_results.extend(analysis_data)
                    print(f"✅ Received {len(analysis_data)} insights from chunk {i + 1}.")
                else:
                    print(f"⚠️ Failed to process chunk {i + 1} of '{scraped_file}'. Skipping.")
                
                if i < len(text_chunks) - 1:
                    time.sleep(2)

            if all_results:
                print(f"\n💾 Saving {len(all_results)} insights to '{output_file}'...")
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(all_results, f, indent=2)
                print(f"✅ Analysis for '{scraped_file}' complete.")
            else:
                print(f"❌ No insights extracted from '{scraped_file}'.")