import os

class Config:
    """Configuration settings for the data cleaning script."""
    def __init__(self):
        # Define project root by navigating up from the current file's directory
        # This makes the script portable regardless of where it's run from.
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Define default chunk size for text processing
        self.chunk_size = 4000
        
        # Define default file paths, using the project root
        self.raw_data_file = os.path.join(self.project_root, "Data", "Scraped", "raw_data.txt")
        self.cleaned_data_file = os.path.join(self.project_root, "Data", "Cleaned", "cleaned_data.txt")

# Create a singleton instance of the config
config = Config()