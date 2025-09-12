"""Configuration management for the data scraping pipeline."""

import os
from dotenv import load_dotenv
from pathlib import Path

class Config:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Project paths
        self.project_root = Path(__file__).parent
        self.data_dir = self.project_root / "data"
        self.scripts_dir = self.project_root / "scripts"
        
        # Create directories if they don't exist
        self.data_dir.mkdir(exist_ok=True)
        
        # API Configuration
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.youtube_api_key = os.getenv("YOUTUBE_API_KEY")  # If needed later
        
        # File paths
        self.raw_data_file = self.data_dir / "raw_data.txt"
        self.cleaned_data_file = self.data_dir / "cleaned_data.txt"
        self.structured_data_file = self.data_dir / "structured_data.json"
        
        # Scraping settings
        self.max_pages = 10
        self.chunk_size = 4000
        self.request_timeout = 60
        self.retry_attempts = 3
        
    def validate_config(self):
        """Validate required configuration."""
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        return True

# Global config instance
config = Config()