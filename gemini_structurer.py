"""Gemini API integration for structuring data."""

import json
import time
import requests
from config import config

class GeminiStructurer:
    def __init__(self):
        config.validate_config()
        self.api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={config.gemini_api_key}"
        self.schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "Link": {"type": "STRING"},
                    "Domain": {"type": "STRING"},
                    "Sub_domain": {"type": "STRING"},
                    "Idea": {"type": "STRING"},
                    "Description": {"type": "STRING"},
                    "success_or_fail": {"type": "STRING"},
                    "Reason": {"type": "STRING"},
                    "Takeaway": {"type": "STRING"},
                    "Region": {"type": "STRING"},
                    "Tags": {"type": "ARRAY", "items": {"type": "STRING"}}
                },
                "required": ["Link", "Idea", "Description", "Takeaway", "Domain"]
            }
        }
    
    def create_prompt(self, text_chunk):
        """Create analysis prompt for Gemini."""
        return f"""
Act as a business analyst. Analyze the following content and extract structured business insights.

For each business idea, case study, or content piece, create a JSON object with:
- Link: Source URL
- Domain: Main domain from URL
- Sub_domain: Subdomain if any
- Idea: Main business idea or concept
- Description: Detailed description
- success_or_fail: Success status if mentioned
- Reason: Reason for success/failure
- Takeaway: Key learning or insight
- Region: Geographic region if mentioned
- Tags: Relevant category tags

Use null for missing information. Here's the content:

{text_chunk}
"""
    
    def analyze_chunk(self, text_chunk):
        """Send chunk to Gemini for analysis."""
        payload = {
            "contents": [{"parts": [{"text": self.create_prompt(text_chunk)}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": self.schema
            }
        }
        
        # Retry logic
        for attempt in range(config.retry_attempts):
            try:
                response = requests.post(
                    self.api_url,
                    headers={"Content-Type": "application/json"},
                    json=payload,
                    timeout=config.request_timeout
                )
                response.raise_for_status()
                
                result = response.json()
                json_text = result["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(json_text)
                
            except requests.exceptions.Timeout:
                print(f"Timeout on attempt {attempt + 1}. Retrying...")
                time.sleep(2 ** attempt)
            except Exception as e:
                print(f"Error analyzing chunk: {e}")
                return None
        
        print("Failed after all retry attempts.")
        return None
    
    def structure_data(self, chunks):
        """Structure all data chunks."""
        all_results = []
        
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i + 1}/{len(chunks)}...")
            
            result = self.analyze_chunk(chunk)
            if result:
                all_results.extend(result)
                print(f"Extracted {len(result)} insights from chunk {i + 1}")
            
            # Rate limiting
            if i < len(chunks) - 1:
                time.sleep(1)
        
        return all_results

def structure_with_gemini(chunks=None):
    """Main function to structure data using Gemini."""
    if chunks is None:
        # Load cleaned data and create chunks
        from data_cleaner import clean_data
        chunks = clean_data()
    
    structurer = GeminiStructurer()
    structured_data = structurer.structure_data(chunks)
    
    # Save structured data
    with open(config.structured_data_file, "w", encoding="utf-8") as f:
        json.dump(structured_data, f, indent=2)
    
    print(f"Structured data saved to {config.structured_data_file}")
    print(f"Total insights extracted: {len(structured_data)}")
    
    return structured_data