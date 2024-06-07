import requests
from bs4 import BeautifulSoup

def scrape_website(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Extract relevant data (title, content, etc.)
    data = []
    for page in soup.find_all('a', href=True):  # Example: finding all links
        page_url = page['href']
        page_title = page.get_text()
        page_content = scrape_page_content(page_url)  # Implement this function to scrape content
        data.append({'title': page_title, 'content': page_content, 'url': page_url})
    return data

def scrape_page_content(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    # Extract the main content of the page
    content = soup.get_text()
    return content

# Example URL
website_data = scrape_website('https://ohsl.us/')
