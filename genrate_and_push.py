import pandas as pd
import os
import json
import time
import argparse
import re
import google.generativeai as genai
from datasets import Dataset, load_from_disk
from tqdm import tqdm
from supabase import create_client, Client
from huggingface_hub import login
from dotenv import load_dotenv

# --- SCRIPT SETUP ---
# Load environment variables from .env file
load_dotenv()

# --- DATA GENERATION FUNCTION ---

def generate_business_analysis_with_gemini(batch_df, model, max_retries=5):
    """
    Sends a batch of rows to Gemini to generate structured QA data.
    Includes a retry mechanism and a very strict prompt with a few-shot example for consistent JSON output.
    """
    batch_context_str = ""
    for _, row in batch_df.iterrows():
        # Proactively convert all fields to string to prevent potential errors
        record_context = f"""
<record>
  <id>{str(row.get('id', ''))}</id>
  <context>
    Business Idea: {str(row.get('idea', ''))}
    Description: {str(row.get('description', ''))}
    Outcome: {str(row.get('success_or_fail', ''))}
    Reason: {str(row.get('reason', ''))}
    Key Takeaway: {str(row.get('takeaway', ''))}
  </context>
</record>"""
        batch_context_str += record_context

    prompt = f"""
    You are a senior business analyst creating training data for an AI model.
    For EACH record provided below, perform two tasks and return the output in a single, valid JSON object.

    {batch_context_str}

    **CRITICAL OUTPUT FORMAT:**
    Your entire output MUST be a single, valid JSON object with a "results" key. Do not include any text, explanations, or markdown formatting like ```json before or after the main JSON object.
    Each item in the "results" list must follow the exact structure shown in the example below.

    **EXAMPLE of a single item in the "results" list:**
    {{
      "id": "1234",
      "generative_analysis": [
        {{ "question": "Evaluate this business idea, considering its strengths and weaknesses.", "answer": "The core strength is its \\"hands-off\\" automation, which saves time. A weakness is the high technical skill required for initial setup." }},
        {{ "question": "Based on the outcome, what business requirements might have been missed?", "answer": "A key missed requirement was a simplified onboarding process for non-technical users." }},
        {{ "question": "Suggest one concrete refinement or pivot for the original idea.", "answer": "Pivot to a version with a visual, drag-and-drop interface targeted at marketing teams." }}
      ],
      "extractive_qa": [
        {{ "question": "What is the primary benefit?", "answer": "automation" }},
        {{ "question": "Who is the target audience?", "answer": "marketing teams" }}
      ]
    }}

    IMPORTANT RULE: As shown in the example, if any generated "answer" string needs to contain double quotes, you MUST escape them with a backslash (e.g., "This is an \\"example\\".").
    """

    for attempt in range(max_retries):
        try:
            print(f"\n[Attempt {attempt + 1}/{max_retries}] Sending request to Gemini API...")
            response = model.generate_content(prompt)
            raw_text = response.text
            print(f"[Attempt {attempt + 1}/{max_retries}] Received response from Gemini API.")
            
            json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
            
            if not json_match:
                raise ValueError("No JSON object found in the model's response.")

            json_string = json_match.group(0)
            return json.loads(json_string).get("results", [])

        except Exception as e:
            print(f"\nAn error occurred on attempt {attempt + 1}/{max_retries}: {e}")
            if attempt + 1 < max_retries:
                wait_time = 2 ** attempt
                print(f"Waiting for {wait_time} seconds before retrying...")
                time.sleep(wait_time)
            else:
                print("Max retries reached. Skipping this batch after final failure.")
                if 'raw_text' in locals():
                    print("--- FINAL PROBLEMATIC TEXT RECEIVED ---")
                    print(raw_text)
                    print("--- END PROBLEMATIC TEXT ---")
                return []
            
    return []


def create_t5_qa_dataset(table_name: str, batch_size: int, gemini_model, supabase_client):
    """Fetches data, uses Gemini to generate a QA dataset, and saves it locally."""
    print("--- Starting Data Generation ---")
    
    print(f"Step 1: Fetching all rows from '{table_name}'...")
    response = supabase_client.table(table_name).select("*").execute()
    if not response.data:
        print(f"❌ No data found in table '{table_name}'. Halting script.")
        return None
    df = pd.DataFrame(response.data).fillna('')
    print(f"Loaded {len(df)} rows.")

    print(f"\nStep 2: Generating QA data in batches of {batch_size}...")
    qa_examples = []
    
    for i in tqdm(range(0, len(df), batch_size), desc="Processing batches"):
        batch_df = df.iloc[i:i + batch_size]
        context_map = {str(row['id']): f"Description: {row.get('description', '')}. Outcome: {row.get('success_or_fail', '')}. Reason: {row.get('reason', '')}. Takeaway: {row.get('takeaway', '')}." for _, row in batch_df.iterrows()}
        
        batch_results = generate_business_analysis_with_gemini(batch_df, gemini_model)
        if not batch_results:
            continue

        for result in batch_results:
            original_id = result.get('id')
            context = context_map.get(str(original_id))
            if not context: continue

            for section in ["generative_analysis", "extractive_qa"]:
                qa_pairs = result.get(section, [])
                for pair in qa_pairs:
                    if isinstance(pair, dict) and 'question' in pair and 'answer' in pair:
                        qa_examples.append({
                            'question': pair['question'],
                            'context': context,
                            'answer': pair['answer']
                        })
        time.sleep(1.5)

    print(f"\nGenerated a total of {len(qa_examples)} QA examples.")
    if not qa_examples:
        print("\n❌ No data was generated. Halting script.")
        return None

    print("\nStep 3: Creating and saving the Hugging Face Dataset locally...")
    output_dir = "business_qa_t5_format"
    if os.path.exists(output_dir):
        import shutil
        shutil.rmtree(output_dir)
        
    Dataset.from_list(qa_examples).train_test_split(test_size=0.1, seed=42).save_to_disk(output_dir)
    print(f"✅ Success! Dataset saved locally to '{output_dir}'.")
    return output_dir

def upload_dataset_to_hub(local_path, hub_name, hf_username):
    """Loads a dataset from a local path and pushes it to the Hub."""
    print(f"\n--- Starting Upload to Hugging Face Hub ---")
    print(f"Loading dataset from '{local_path}'...")
    repo_id = f"{hf_username}/{hub_name}"
    load_from_disk(local_path).push_to_hub(repo_id=repo_id, private=True)
    print(f"\n✅ Success! Your dataset is available at: [https://huggingface.co/datasets/](https://huggingface.co/datasets/){repo_id}")

# --- MAIN EXECUTION BLOCK ---

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Full pipeline to generate and upload QA data.")
    parser.add_argument("--table_name", type=str, default="startups", help="Name of the table in Supabase.")
    parser.add_argument("--gemini_batch_size", type=int, default=5, help="Batch size for Gemini API calls.")
    args = parser.parse_args()

    try:
        print("--- STEP 1: CONFIGURING SERVICES from .env file ---")
        
        # --- Load API keys and check them ---
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        hf_token = "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"

        if not all([gemini_api_key, supabase_url, supabase_key, hf_token]):
            raise ValueError("One or more API keys are missing. Please check your .env file.")

        # --- Configure clients with timeout ---
        genai.configure(api_key=gemini_api_key, client_options={'api_endpoint': 'generativelanguage.googleapis.com'})
        gemini_model = genai.GenerativeModel(os.getenv("DEFAULT_MODEL"))
        print("✅ Gemini configured.")

        supabase_client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client configured.")
        
        login(token=hf_token)
        print("✅ Logged into Hugging Face Hub.")

        # --- Run pipeline ---
        print("\n--- STEP 2: GENERATING AND SAVING DATASET LOCALLY ---")
        local_dataset_path = create_t5_qa_dataset(
            table_name=args.table_name,
            batch_size=args.gemini_batch_size,
            gemini_model=gemini_model,
            supabase_client=supabase_client
        )

        if local_dataset_path:
            print("\n--- STEP 3: UPLOADING DATASET TO HUGGING FACE HUB ---")
            upload_dataset_to_hub(
                local_path=local_dataset_path,
                hub_name="business-qa-analysis",
                hf_username="Dohahemdann"
            )
        else:
            print("\nPipeline halted because data generation failed.")
            
    except Exception as e:
        print(f"\n❌ A critical error occurred during the pipeline execution: {e}")

