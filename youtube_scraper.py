"""YouTube video transcript and metadata scraper."""

import re
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import YouTubeTranscriptApi
import requests
from config import config

class YouTubeScraper:
    def __init__(self):
        self.video_data = []
    
    def extract_video_id(self, url):
        """Extract video ID from YouTube URL."""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_video_metadata(self, video_id):
        """Get video metadata using YouTube API or web scraping."""
        try:
            # Simple metadata extraction (title from page)
            response = requests.get(f"https://www.youtube.com/watch?v={video_id}")
            title_match = re.search(r'"title":"([^"]*)"', response.text)
            title = title_match.group(1) if title_match else f"Video {video_id}"
            return {"title": title, "video_id": video_id}
        except:
            return {"title": f"Video {video_id}", "video_id": video_id}
    
    def get_transcript(self, video_id):
        """Get video transcript."""
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = " ".join([item['text'] for item in transcript_list])
            return transcript_text
        except Exception as e:
            print(f"Could not retrieve transcript for {video_id}: {e}")
            return None
    
    def scrape_video(self, url):
        """Scrape a single YouTube video."""
        video_id = self.extract_video_id(url)
        if not video_id:
            print(f"Invalid YouTube URL: {url}")
            return None
            
        metadata = self.get_video_metadata(video_id)
        transcript = self.get_transcript(video_id)
        
        if transcript:
            content = f"""
--- CONTENT FROM {url} ---
Title: {metadata['title']}
Video ID: {video_id}
Transcript:
{transcript}
"""
            return content
        return None
    
    def scrape_playlist_or_channel(self, url):
        """Scrape multiple videos from playlist or channel (basic implementation)."""
        # This would require YouTube API or more complex scraping
        # For now, just handle single video
        return self.scrape_video(url)

def scrape_youtube_videos(urls):
    """Main function to scrape YouTube videos."""
    scraper = YouTubeScraper()
    all_content = []
    
    for url in urls:
        content = scraper.scrape_video(url)
        if content:
            all_content.append(content)
    
    final_content = "\n".join(all_content)
    
    # Save raw data
    with open(config.raw_data_file, "w", encoding="utf-8") as f:
        f.write(final_content)
    
    print(f"YouTube content saved to {config.raw_data_file}")
    return final_content