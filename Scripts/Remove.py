import os
import shutil

def remove_invalid_files(folder_path, min_size_bytes=2048, valid_extensions=['.txt']):
    """
    Deletes files from a folder that are too short, have an invalid extension, or contain
    common scraping error messages, including security prompts.

    Args:
        folder_path (str): The path to the folder to clean.
        min_size_bytes (int): The minimum file size in bytes. Files smaller than this are removed.
        valid_extensions (list): A list of valid file extensions (e.g., ['.txt']).
    """
    # Define common error messages and security prompts to look for
    error_keywords = [
        "403 ERROR",
        "Request blocked",
        "We can't connect to the server",
        "You've been blocked by network security",
        "File a ticket",
        "you have been blocked",
        "needs to review the security of your connection",
        "Enable JavaScript and cookies"
    ]
    if not os.path.isdir(folder_path):
        print(f"Error: The folder at '{folder_path}' doesn't exist.")
        return

    print(f"Starting to clean folder: {folder_path}\n")
    print(f"  - Removing files smaller than {min_size_bytes / 1024:.2f} KB")
    print(f"  - Removing files with invalid extensions or error content")
    print("-" * 50)

    removed_count = 0

    for root, dirs, files in os.walk(folder_path):
        for filename in files:
            file_path = os.path.join(root, filename)

            try:
                file_size = os.path.getsize(file_path)
            except OSError as e:
                print(f"🚫 Could not get size of {file_path}. Skipping. Error: {e}")
                continue

            file_extension = os.path.splitext(filename)[1].lower()

            is_invalid_extension = file_extension not in valid_extensions
            is_too_short = file_size < min_size_bytes

            is_error_content = False
            # Only check content if the file is a valid extension and is long enough
            if not is_invalid_extension and not is_too_short:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read(500)
                        content_lower = content.lower()
                        if any(keyword.lower() in content_lower for keyword in error_keywords):
                            is_error_content = True
                except Exception as e:
                    print(f"🚫 Could not read file {file_path}. Skipping. Error: {e}")
                    continue

            # Check if the file should be removed based on any of the criteria
            if is_invalid_extension or is_too_short or is_error_content:
                try:
                    os.remove(file_path)
                    if is_error_content:
                        print(f"🗑️ Removed (Error Content): {file_path}")
                    elif is_too_short:
                        print(f"🗑️ Removed (Too Short): {file_path} (Size: {file_size} bytes)")
                    else: # Invalid extension
                        print(f"🗑️ Removed (Invalid Extension): {file_path}")
                    removed_count += 1
                except OSError as e:
                    print(f"🚫 Failed to remove {file_path}. Reason: {e}")

    print("\n" + "-" * 50)
    print("--- Cleaning complete ---")
    print(f"Total files removed: {removed_count}")


folder_to_clean = '../Data/Scraped'  

# You can customize the minimum size and valid extensions
# This will remove any file that isn't a .txt, .csv or is less than 50 bytes.
remove_invalid_files(folder_to_clean, min_size_bytes=2048, valid_extensions=['.txt', '.csv'])