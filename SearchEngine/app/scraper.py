# app/scraper.py
from bs4 import BeautifulSoup
import requests

def scrape_website(query):
    url = "https://ohsl.us/projects/bcda"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Custom logic to extract data based on the query
    extracted_data = extract_data_from_soup(soup, query)
    return extracted_data

def extract_data_from_soup(soup, query):
    # Example: Extract paragraphs that mention the query
    paragraphs = soup.find_all('p')
    relevant_data = [p.get_text() for p in paragraphs if query.lower() in p.get_text().lower()]
    return ' '.join(relevant_data)
