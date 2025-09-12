"""Clean website scraper with minimal dependencies."""

import time
from urllib.parse import urljoin, urlparse
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from config import config

class WebsiteScraper:
    def __init__(self):
        self.driver = None
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def cleanup(self):
        """Safely cleanup Chrome driver."""
        if self.driver:
            try:
                # Remove sleep call and properly close service
                self.driver.service.stop()
                self.driver.close()
                self.driver = None
            except:
                pass

    def setup_driver(self):
        """Initialize Chrome driver with stealth options."""
        try:
            options = uc.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            # Add more stability options
            options.page_load_strategy = 'eager'
            self.driver = uc.Chrome(options=options)
            self.driver.set_page_load_timeout(30)
            return True
        except Exception as e:
            print(f"Failed to setup driver: {e}")
            return False
    
    def scrape_page(self, url, max_retries=3):
        """Scrape a single page with retry mechanism."""
        for attempt in range(max_retries):
            try:
                if self.driver is None:
                    if not self.setup_driver():
                        return None
                
                self.driver.get(url)
                # Wait for page load
                time.sleep(5)
                
                # Handle infinite scroll
                last_height = self.driver.execute_script("return document.body.scrollHeight")
                for _ in range(3):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(3)  # Increased delay
                    new_height = self.driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height
                
                return self.driver.page_source
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed for {url}: {e}")
                # Cleanup and recreate driver on error
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                    self.driver = None
                time.sleep(2 ** attempt)  # Exponential backoff
                
        return None
    
    def extract_content(self, html, base_url):
        """Extract text and links from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find main content
        main_selectors = ['main', 'article', '[role="main"]', '#content', '.content']
        main_content = None
        
        for selector in main_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break
        
        if not main_content:
            main_content = soup.body
            
        # Extract text and links
        text = main_content.get_text(separator='\n', strip=True)
        links = [urljoin(base_url, a['href']) for a in main_content.find_all('a', href=True)]
        
        return text, links
    
    def crawl_website(self, start_url):
        """Scrape single target URL without following links."""
        try:
            if not self.setup_driver():
                raise Exception("Failed to initialize driver")
            
            print(f"Crawling: {start_url}")
            html = self.scrape_page(start_url)
            
            if html:
                text, _ = self.extract_content(html, start_url)
                content = f"\n--- CONTENT FROM {start_url} ---\n{text}"
                return content
            
            return ""
            
        except Exception as e:
            print(f"Crawling failed: {e}")
            return ""
            
        finally:
            self.cleanup()

def scrape_website(url):
    """Main function to scrape a website."""
    with WebsiteScraper() as scraper:
        content = scraper.crawl_website(url)
        
        # Save raw data
        with open(config.raw_data_file, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"Scraped content saved to {config.raw_data_file}")
        return content