import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

def scrape_all_company_names(driver):
    """
    Scrapes all company names from the main YC directory by infinitely scrolling
    and extracting the name from the company's URL slug.
    """
    url = "https://www.ycombinator.com/companies"
    print(f"Loading main directory at {url} to find all company names...")
    driver.get(url)
    
    names = set() # Use a set to automatically handle duplicates
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    print("Starting to scroll through the directory. This will take several minutes...")

    try:
        while True:
            # Scroll down to the bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            
            # Wait for new companies to load
            time.sleep(2) 
            
            # --- MODIFIED LOGIC ---
            # Instead of looking for a specific text element, find all company links
            # and parse the name from the URL itself.
            link_elements = driver.find_elements(By.CSS_SELECTOR, 'a[href^="/companies/"]')
            
            if not link_elements:
                 print("Warning: Could not find any company links with the current selector.")

            for el in link_elements:
                href = el.get_attribute('href')
                if href:
                    # The name is the last part of the URL path (the "slug")
                    # e.g., https://www.ycombinator.com/companies/brex -> "brex"
                    slug = href.strip('/').split('/')[-1]
                    
                    # Clean up the slug to be a proper name and avoid navigational links
                    if slug and slug not in ['companies', 'founders']:
                        # Replace hyphens with spaces and capitalize words
                        clean_name = slug.replace('-', ' ').title()
                        names.add(clean_name)

            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                print("Reached the bottom of the page.")
                break # Exit loop if scroll height doesn't change
            
            last_height = new_height
            print(f"Scrolled down, now have {len(names)} unique names...")

    except Exception as e:
        print(f"An error occurred during scrolling: {e}")
    
    print(f"\nFinished scrolling. Extracted a total of {len(names)} unique company names.")
    return list(names) # Convert set to list for saving


if __name__ == "__main__":
    # Setup Selenium WebDriver
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        print("Starting the YC startup name scraper...")
        
        # 1. Scrape all names
        all_names = scrape_all_company_names(driver)
                
        if not all_names:
            print("No company names were found. Exiting.")
        else:
            # 2. Save the names to a file
            output_filename = "../../Data/StartupNames/yc_startup_names.txt"
            print(f"Saving {len(all_names)} names to '{output_filename}'...")
            
            with open(output_filename, 'w', encoding='utf-8') as f:
                for name in sorted(all_names): # Sort alphabetically for clean output
                    f.write(f"{name}\n")
                    
            print(f"\n✅ Success! All names have been saved to '{output_filename}'")

    except Exception as e:
        print(f"\n❌ An unexpected and critical error occurred: {e}. The script will now exit.")

    finally:
        if driver:
            driver.quit()

