import undetected_chromedriver as uc
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor

def scrape_dynamic_page(url: str) -> str:
    # (Your existing scrape_dynamic_page function goes here)
    # Make sure this function is self-contained and returns the HTML
    driver = None
    try:
        print(f"🚀 Scraping in new process: {url}")
        options = uc.ChromeOptions()
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36')
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        driver = uc.Chrome(options=options)
        driver.get(url)

        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_pause_time = 2

        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause_time)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        page_html = driver.page_source
        
        print(f"✅ Scraped successfully: {url}")
        return page_html

    except Exception as e:
        print(f"An error occurred while scraping {url}: {e}")
        return f"Error: Could not scrape the page. {e}"
        
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                # Silently ignore the invalid handle error
                if not ("The handle is invalid" in str(e)):
                    print(f"Warning: ChromeDriver cleanup error: {e}")

def extract_text_and_links(html_content: str, base_url: str):
    soup = BeautifulSoup(html_content, 'html.parser')
    main_content_selectors = ['main', 'article', '[role="main"]', '#content', '#main', '.content', '.main']
    search_area = None
    
    for selector in main_content_selectors:
        search_area = soup.select_one(selector)
        if search_area:
            break
            
    if not search_area:
        search_area = soup.body

    text = search_area.get_text(separator='\n', strip=True)
    links = set()
    for a_tag in search_area.find_all('a', href=True):
        href = a_tag['href']
        absolute_link = urljoin(base_url, href)
        links.add(absolute_link)
        
    return text, list(links)


def process_url(url):
    """A wrapper function to handle scraping and extraction for a single URL."""
    scraped_html = scrape_dynamic_page(url)
    if "Error:" in scraped_html:
        return None, []
    
    clean_text, new_links = extract_text_and_links(scraped_html, url)
    return clean_text, new_links


# --- Main execution ---
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    links_file = os.path.join(project_root, "Data", "links.txt")

    # Read URLs from links.txt
    with open(links_file, "r", encoding="utf-8") as f:
        start_urls = [line.strip() for line in f if line.strip()]

    print(f"Found {len(start_urls)} start URLs in links.txt")

    for start_url in start_urls:
        urls_to_visit = [start_url]
        visited_urls = set()
        all_scraped_text = []

        domain = urlparse(start_url).netloc
        max_pages_to_crawl = 1
        pages_crawled = 0
        url_queue = {start_url}

        print(f"\n🚀 Starting crawl at: {start_url}")
        print(f"Will stay on domain: {domain}")
        print(f"Maximum pages to crawl: {max_pages_to_crawl}")

        with ProcessPoolExecutor(max_workers=4) as executor:
            while len(url_queue) > 0 and pages_crawled < max_pages_to_crawl:
                batch_size = min(len(url_queue), max_pages_to_crawl - pages_crawled)
                urls_to_process = list(url_queue)[:batch_size]
                url_queue = url_queue - set(urls_to_process)

                future_to_url = {executor.submit(process_url, url): url for url in urls_to_process}

                for future in future_to_url:
                    url = future_to_url[future]
                    if pages_crawled >= max_pages_to_crawl:
                        break
                    try:
                        clean_text, new_links = future.result()
                        if clean_text:
                            all_scraped_text.append(f"\n\n--- CONTENT FROM {url} ---\n\n{clean_text}")
                            visited_urls.add(url)
                            pages_crawled += 1

                            for link in new_links:
                                cleaned_link = urljoin(link, urlparse(link).path)
                                if cleaned_link not in visited_urls and urlparse(cleaned_link).netloc == domain:
                                    url_queue.add(cleaned_link)
                    except Exception as e:
                        print(f"Error processing {url}: {e}")

        print("\nCrawling finished. Combining text...")

        final_text = "\n".join(all_scraped_text)

        scraped_dir = os.path.join(project_root, "Data", "Scraped")
        os.makedirs(scraped_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        safe_domain = domain.replace(".", "_").replace(":", "_")
        file_path = os.path.join(scraped_dir, f"{safe_domain}_scraped_text_{timestamp}.txt")

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Original Link: {start_url}\n\n")
            f.write(final_text)

        print(f"✅ All text from {pages_crawled} pages ({start_url}) saved to '{file_path}'")