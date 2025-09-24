import os
import json
from groq import Groq
import jsonschema
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()
# 1. Groq API client setup
api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key)

# 2. Define the JSON schema for validation
startup_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "Link": {"type": "string", "format": "uri"},
            "Idea": {"type": "string"},
            "Description": {"type": "string"},
            "Takeaway": {"type": "string"},
            "Domain": {"type": ["string", "null"]},
            "Reason": {"type": "string"},
            "Region": {"type": ["string", "null"]},
            "Sub_domain": {"type": ["string", "null"]},
            "Tags": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 1
            },
            "success_or_fail": {"type": "string", "enum": ["success", "fail","Success","Fail","SUCCESS","FAIL","failure","Failure","FAILURE"]}
        },
        "required": ["Link", "Idea", "Description", "Takeaway", "Domain", "Reason", "Region", "Sub_domain", "Tags", "success_or_fail"]
    }
}

# 3. Validation function
def validate_startup_json(json_data, schema):
    """
    Validates a JSON object against a given JSON schema.
    Returns True if validation is successful, False otherwise.
    """
    try:
        jsonschema.validate(instance=json_data, schema=schema)
        return True
    except jsonschema.exceptions.ValidationError as err:
        print(f"❌ Validation Error: {err.message}")
        return False

# 4. Main function to process the folder
def process_folder(folder_path, output_folder):
    """
    Loops through all files in a folder, processes each with Groq API,
    validates the output, and saves valid/invalid schemas to separate files.
    """
    if not os.path.isdir(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist.")
        return

    # Create the output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        
        # Skip non-files and hidden files like .gitkeep
        if not os.path.isfile(file_path) or filename.startswith('.'):
            continue

        print(f"--- Processing file: {filename} ---")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text_chunk = f.read()

            # Construct the prompt with the file content
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

            # Call Groq API
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="llama-3.1-8b-instant",
                response_format={"type": "json_object"},
            )

            # Parse the JSON response
            json_output = chat_completion.choices[0].message.content
            parsed_data = json.loads(json_output)
            
            # Check for nested array and extract it
            if isinstance(parsed_data, dict) and len(parsed_data) == 1 and isinstance(list(parsed_data.values())[0], list):
                startup_data = list(parsed_data.values())[0]
                print(f"⚠️ Model returned a JSON object, extracting array from key: '{list(parsed_data.keys())[0]}'")
            else:
                startup_data = parsed_data
            
            # Lists to hold valid and invalid schemas
            valid_schemas = []
            invalid_schemas = []
            
            # Validate each item within the array
            for item in startup_data:
                # Clean the item by removing extra fields not in the schema
                cleaned_item = {key: item[key] for key in item if key in startup_schema['items']['properties']}
                
                # Check for "Region" as it seems to be an issue in some cases.
                if 'Region' in cleaned_item and cleaned_item['Region'] is None:
                    cleaned_item['Region'] = "null"

                if validate_startup_json(cleaned_item, startup_schema['items']):
                    valid_schemas.append(item)
                else:
                    invalid_schemas.append(item)
            
            # Save the validated schemas to new files
            if valid_schemas:
                valid_output_path = os.path.join(output_folder, f"valid_{filename}")
                with open(valid_output_path, 'w', encoding='utf-8') as f:
                    json.dump(valid_schemas, f, indent=4)
                print(f"✅ Saved {len(valid_schemas)} valid schemas to '{valid_output_path}'.")
            
            if invalid_schemas:
                invalid_output_path = os.path.join(output_folder, f"invalid_{filename}")
                with open(invalid_output_path, 'w', encoding='utf-8') as f:
                    json.dump(invalid_schemas, f, indent=4)
                print(f"❌ Saved {len(invalid_schemas)} invalid schemas to '{invalid_output_path}'.")
            
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found.")
        except json.JSONDecodeError as e:
            print(f"❌ Failed to decode JSON from Groq API response for '{filename}': {e}")
        except Exception as e:
            print(f"❌ An error occurred while processing '{filename}': {e}")
        
        print("-" * 30)

# 5. Run the processing on the folder
if __name__ == "__main__":
    source_folder = "../../Data/Schemas"
    output_folder = "../../Data/Validated_Schemas"
    process_folder(source_folder, output_folder)
