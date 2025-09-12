import undetected_chromedriver as uc
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os

def scrape_dynamic_page(url: str) -> str:
    """
    Scrapes the full HTML content of a JavaScript-heavy website
    while attempting to bypass bot detection and handling infinite scroll.
    """
    driver = None
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
        # Check if the driver object was successfully created
        if driver:
            try:
                # Use a small delay before quitting to avoid race conditions
                time.sleep(1)
                driver.quit()
            except Exception as e:
                # Catch any errors during the quit process itself, like the OSError
                print(f"Error during driver quit: {e}")

def extract_text_and_links(html_content: str, base_url: str):
    # ... (rest of the function is the same)
    soup = BeautifulSoup(html_content, 'html.parser')
    main_content_selectors = ['main', 'article', '[role="main"]', '#content', '#main', '.content', '.main']
    search_area = None
    
    for selector in main_content_selectors:
        search_area = soup.select_one(selector)
        if search_area:
            print(f"  -> Found main content using selector: '{selector}'")
            break
            
    if not search_area:
        print("  -> No specific main content tag found. Searching entire page for links.")
        search_area = soup.body

    text = search_area.get_text(separator='\n', strip=True)
    links = set()
    for a_tag in search_area.find_all('a', href=True):
        href = a_tag['href']
        absolute_link = urljoin(base_url, href)
        links.add(absolute_link)
        
    return text, list(links)

def read_links_from_file(filename="links.txt"):
    # ... (rest of the function is the same)
    links = []
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            links = [line.strip() for line in f if line.strip()]
        print(f"Loaded {len(links)} initial links from {filename}.")
    else:
        print(f"Warning: The file '{filename}' was not found. Starting with an empty list.")
    return links

# --- Main execution ---
# --- Main execution ---
if __name__ == "__main__":
    urls_to_visit = read_links_from_file()
    visited_urls = set()
    all_scraped_text = []

    if not urls_to_visit:
        print("No URLs to crawl. Exiting.")
        exit()

    start_url = urls_to_visit[0]
    domain = urlparse(start_url).netloc
    
    # We will use a set to avoid duplicates and a list for the crawl queue
    urls_to_visit_queue = urls_to_visit.copy()
    
    max_pages_to_crawl = 20
    pages_crawled = 0

    print(f"Starting crawl with {len(urls_to_visit_queue)} initial links.")
    print(f"Will stay on domain: {domain}")
    print(f"Maximum pages to crawl: {max_pages_to_crawl}")

    while urls_to_visit_queue and pages_crawled < max_pages_to_crawl:
        current_url = urls_to_visit_queue.pop(0)
        
        cleaned_url = urljoin(current_url, urlparse(current_url).path)
        
        # Check if URL is in the visited set
        if cleaned_url in visited_urls:
            print(f"Skipping already visited URL: {cleaned_url}")
            continue

        # Check if the URL is on the target domain
        if urlparse(cleaned_url).netloc != domain:
            print(f"Skipping out-of-domain URL: {cleaned_url}")
            continue

        print(f"\n--- Crawling page {pages_crawled + 1}/{max_pages_to_crawl} ---")
        print(f"URL: {cleaned_url}")
        
        scraped_html = scrape_dynamic_page(cleaned_url)
        visited_urls.add(cleaned_url)
        pages_crawled += 1

        if "Error:" not in scraped_html:
            clean_text, new_links = extract_text_and_links(scraped_html, cleaned_url)
            all_scraped_text.append(f"\n\n--- CONTENT FROM {cleaned_url} ---\n\n{clean_text}")
            
            for link in new_links:
                # Add new, unvisited links from the same domain to the queue
                if urlparse(link).netloc == domain:
                    # Only add if not already in the queue or visited
                    if link not in visited_urls and link not in urls_to_visit_queue:
                        urls_to_visit_queue.append(link)
    
    print("\nCrawling finished. Combining text...")
    
    final_text = "\n".join(all_scraped_text)
    file_path = "scraped_text.txt"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(final_text)
    
    print(f"\n✅ All text from {pages_crawled} pages has been saved to '{file_path}'")