"""Data cleaning pipeline for scraped content."""

import re
from config import config

class DataCleaner:
    def __init__(self):
        self.stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should'}
    
    def remove_html_artifacts(self, text):
        """Remove HTML tags and artifacts."""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Remove HTML entities
        text = re.sub(r'&[a-zA-Z0-9#]+;', '', text)
        return text
    
    def normalize_whitespace(self, text):
        """Normalize whitespace and line breaks."""
        # Replace multiple whitespaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Fix line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()
    
    def remove_navigation_elements(self, text):
        """Remove common navigation and UI elements."""
        nav_patterns = [
            r'(?i)(home|about|contact|privacy|terms|login|register|sign up|menu|search|newsletter)',
            r'(?i)(cookie|gdpr|accept|decline|subscribe|follow us)',
            r'(?i)(share|tweet|facebook|twitter|linkedin|instagram)',
        ]
        
        for pattern in nav_patterns:
            text = re.sub(pattern, '', text)
        
        return text
    
    def extract_meaningful_content(self, text):
        """Extract meaningful content from text blocks."""
        lines = text.split('\n')
        meaningful_lines = []
        
        for line in lines:
            line = line.strip()
            # Skip very short lines (likely navigation/UI)
            if len(line) < 10:
                continue
            # Skip lines with too many special characters
            if len(re.sub(r'[a-zA-Z0-9\s]', '', line)) / len(line) > 0.5:
                continue
            meaningful_lines.append(line)
        
        return '\n'.join(meaningful_lines)
    
    def chunk_content(self, text, chunk_size=None):
        """Split content into manageable chunks."""
        if chunk_size is None:
            chunk_size = config.chunk_size
            
        # Split by content sections first
        sections = text.split('\n--- CONTENT FROM ')
        chunks = []
        current_chunk = ""
        
        for section in sections:
            if not section.strip():
                continue
                
            section_text = f"--- CONTENT FROM {section}" if not section.startswith('--- CONTENT FROM') else section
            
            if len(current_chunk) + len(section_text) > chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = section_text
            else:
                current_chunk = current_chunk + '\n\n' + section_text if current_chunk else section_text
        
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks
    
    def clean_text(self, raw_text):
        """Main cleaning pipeline."""
        print("Starting data cleaning pipeline...")
        
        # Step 1: Remove HTML artifacts
        text = self.remove_html_artifacts(raw_text)
        
        # Step 2: Normalize whitespace
        text = self.normalize_whitespace(text)
        
        # Step 3: Remove navigation elements
        text = self.remove_navigation_elements(text)
        
        # Step 4: Extract meaningful content
        text = self.extract_meaningful_content(text)
        
        print("Data cleaning completed.")
        return text

def clean_data(input_file=None, output_file=None):
    """Main function to clean scraped data."""
    if input_file is None:
        input_file = config.raw_data_file
    if output_file is None:
        output_file = config.cleaned_data_file
    
    # Read raw data
    with open(input_file, "r", encoding="utf-8") as f:
        raw_text = f.read()
    
    # Clean data
    cleaner = DataCleaner()
    cleaned_text = cleaner.clean_text(raw_text)
    
    # Save cleaned data
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(cleaned_text)
    
    print(f"Cleaned data saved to {output_file}")
    
    # Return chunks for further processing
    chunks = cleaner.chunk_content(cleaned_text)
    return chunks