import os
import requests
import json

from dotenv import load_dotenv 
load_dotenv() 

SERPER_API_KEY = os.getenv("SERPER_API_KEY")
print(f"SERPER_API_KEY: {SERPER_API_KEY}")

def search_serper(query):
    """
    Performs a search on Serper's Google Search API using the correct POST method.
    
    Args:
        query (str): The search query.
        
    Returns:
        list: A list of links.
    """
    if not SERPER_API_KEY:
        print("Error: SERPER_API_KEY environment variable is not set.")
        return []
    
    url = "https://google.serper.dev/search"
    
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    payload = json.dumps({"q": query})
    
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status() 
        json_results = response.json()
        links = [item['link'] for item in json_results.get('organic', []) if 'link' in item]

        return links
    
    except requests.exceptions.RequestException as e:
        print(f"An error occurred with the Serper API: {e}")
        return []

def save_links_to_file(links, filename="../Data/links.txt"):
    """
    Saves a list of links to a text file, with each link on a new line.

    Args:
        links (list): A list of links to save.
        filename (str): The name of the file to save the links to.
    """
    try:
        with open(filename, 'w') as file:
            for link in links:
                file.write(link + '\n')
        print(f"Successfully saved {len(links)} links to {filename}.")
    except IOError as e:
        print(f"An error occurred while writing to the file: {e}")

# Example usage
if __name__ == '__main__':
    topics = [
        "Famous startup success stories and lessons",
        "Startup failure case studies",
        "In-depth analysis of successful startups",
        "Failed business models explained",
        "Biographies of tech entrepreneurs"
    ]
    all_links = []
    for topic in topics:
        print(f"Searching for topic: {topic}")
        found_links = search_serper(topic)
        print(f"Found {len(found_links)} links.")
        all_links.extend(found_links)
    
    if all_links:
        save_links_to_file(all_links)
    else:
        print("No links were found to save.")