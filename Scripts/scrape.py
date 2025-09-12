import undetected_chromedriver as uc
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def scrape_dynamic_page(url: str) -> str:
    """
    Scrapes the full HTML content of a JavaScript-heavy website
    while attempting to bypass bot detection and handling infinite scroll.
    """
    driver = None  # Initialize driver to None
    try:
        print("🚀 Starting browser in headless mode...")
        options = uc.ChromeOptions()
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = uc.Chrome(options=options)

        print(f" navigating to: {url}")
        driver.get(url)

        print("⏳ Scrolling to load all content...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_pause_time = 2

        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        print("✅ Scrolling complete.")
        page_html = driver.page_source
        
        print(" Scraped successfully!")
        return page_html

    except Exception as e:
        print(f"An error occurred while scraping {url}: {e}")
        return f"Error: Could not scrape the page. {e}"
        
    finally:
        if driver:
            try:
                driver.quit()
            except OSError as e:
                if "The handle is invalid" in str(e):
                    pass 
                else:
                    raise

def extract_text_and_links(html_content: str, base_url: str):
    """
    Extracts readable text and hyperlinks from the main content area of an HTML document.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    # List of common CSS selectors for the main content area of a webpage
    main_content_selectors = ['main', 'article', '[role="main"]', '#content', '#main', '.content', '.main']
    search_area = None
    
    # Try each selector until we find the main content area
    for selector in main_content_selectors:
        search_area = soup.select_one(selector)
        if search_area:
            print(f"  -> Found main content using selector: '{selector}'")
            break
            
    # If no specific main content area is found, fall back to the whole page body
    if not search_area:
        print("  -> No specific main content tag found. Searching entire page for links.")
        search_area = soup.body

    # Extract text and links from the determined search area
    text = search_area.get_text(separator='\n', strip=True)
    links = set()
    for a_tag in search_area.find_all('a', href=True):
        href = a_tag['href']
        # Convert relative links (like "/about") to absolute URLs
        absolute_link = urljoin(base_url, href)
        links.add(absolute_link)
        
    return text, list(links)


# --- Main execution ---
if __name__ == "__main__":
    start_url = "https://www.ycombinator.com/library"
    urls_to_visit = [start_url]
    visited_urls = set()
    all_scraped_text = []
    
    # Get the domain to ensure we don't leave the target website
    domain = urlparse(start_url).netloc
    
    # Set a limit to prevent the crawler from running indefinitely
    max_pages_to_crawl = 10 
    pages_crawled = 0

    print(f"Starting crawl at: {start_url}")
    print(f"Will stay on domain: {domain}")
    print(f"Maximum pages to crawl: {max_pages_to_crawl}")

    while urls_to_visit and pages_crawled < max_pages_to_crawl:
        current_url = urls_to_visit.pop(0)
        
        # Clean the URL (remove fragments) and check if we should visit it
        cleaned_url = urljoin(current_url, urlparse(current_url).path)
        if cleaned_url in visited_urls or urlparse(cleaned_url).netloc != domain:
            continue

        print(f"\n--- Crawling page {pages_crawled + 1}/{max_pages_to_crawl} ---")
        print(f"URL: {cleaned_url}")

        scraped_html = scrape_dynamic_page(cleaned_url)
        visited_urls.add(cleaned_url)
        pages_crawled += 1

        if "Error:" not in scraped_html:
            clean_text, new_links = extract_text_and_links(scraped_html, cleaned_url)
            all_scraped_text.append(f"\n\n--- CONTENT FROM {cleaned_url} ---\n\n{clean_text}")
            
            # Add all new, unvisited links from the same domain to the queue
            for link in new_links:
                if link not in visited_urls:
                    urls_to_visit.append(link)
    
    print("\nCrawling finished. Combining text...")
    
    # Combine the text from all visited pages and save it to a file
    final_text = "\n".join(all_scraped_text)
    file_path = "scraped_text.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_text)
    
    print(f"\n✅ All text from {pages_crawled} pages has been saved to '{file_path}'")

