import json
import argparse
import os
import sys
from pathlib import Path

# --- IMPORTANT: Add the project root to the Python path ---
project_root = Path(__file__).resolve().parent
sys.path.append(str(project_root))

# --- Use the exact functions and schema you specified ---
from Scripts.Database.supabase_client import bulk_insert_from_json
from Scripts.PostProcessing.validation import validate_startup_json, startup_schema

# --- Main Execution Block ---

if __name__ == "__main__":
    # 1. Setup command-line argument parser to get the input file
    parser = argparse.ArgumentParser(
        description="Validate a JSON file and upload its valid contents to a database."
    )
    parser.add_argument(
        "json_file",
        type=str,
        help="The path to the source JSON file to process."
    )
    args = parser.parse_args()
    source_file_path = Path(args.json_file)

    # 2. Check if the source file exists
    if not source_file_path.is_file():
        print(f"❌ Error: The file '{source_file_path}' was not found.")
        sys.exit(1)

    try:
        # 3. Load the data from the source JSON file
        print(f"📄 Loading data from '{source_file_path.name}'...")
        with open(source_file_path, 'r', encoding='utf-8') as f:
            all_records = json.load(f)

        if not isinstance(all_records, list):
            print("❌ Error: JSON file content must be a list of objects.")
            sys.exit(1)
        
        # --- Clean "N/A" values before validation ---
        print("🧹 Cleaning data: Converting 'N/A' strings to null...")
        for record in all_records:
            for key, value in record.items():
                if value == "N/A":
                    record[key] = None
        # ---------------------------------------------

        # 4. Validate and filter the records using your 'validate_startup_json' function
        print(f"\n🧐 Validating {len(all_records)} records using your schema...")
        valid_records = []
        for record in all_records:
            # --- FIX: Wrap the single 'record' in a list [] to match the schema's expectation ---
            if validate_startup_json([record], startup_schema):
                valid_records.append(record)
            else:
                # Use a more reliable key for error messages if available, like 'Link' or 'Domain'
                record_identifier = record.get('Link', record.get('Domain', 'N/A'))
                print(f"   ⚠️  Skipping invalid record: '{record_identifier}'")
        
        print(f"✅ Validation complete. Found {len(valid_records)} valid records.")

        # 5. Push the valid data to the database
        if not valid_records:
            print("\n🏁 No valid records found. Nothing to upload.")
        else:
            temp_file_path = source_file_path.parent / "temp_valid_data.json"
            print(f"\n💾 Saving valid records to temporary file: '{temp_file_path.name}'")
            with open(temp_file_path, 'w', encoding='utf-8') as f:
                json.dump(valid_records, f, indent=2)

            print(f"☁️  Uploading '{temp_file_path.name}' to the database...")
            success = bulk_insert_from_json(temp_file_path)

            if success:
                print("✅ Successfully uploaded data.")
            else:
                print("❌ Failed to upload data.")

            print(f"🗑️  Removing temporary file...")
            os.remove(temp_file_path)
            print("\n🏁 Process finished.")

    except json.JSONDecodeError:
        print(f"❌ Error: Could not decode JSON. Please check the format of '{source_file_path}'.")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")