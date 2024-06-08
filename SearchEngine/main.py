import requests
from bs4 import BeautifulSoup

def scrape_page_content(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    content = soup.get_text()  # Get all the text from the page
    return content

def scrape_website(base_url):
    response = requests.get(base_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    data = []
    for link in soup.find_all('a', href=True):
        page_url = link['href']
        if not page_url.startswith('http'):
            page_url = base_url + page_url  # Construct full URL if relative
        page_title = link.get_text()
        page_content = scrape_page_content(page_url)
        data.append({'title': page_title, 'content': page_content, 'url': page_url})
    return data

# Example URL
website_url = 'http://example.com'
website_data = scrape_website(website_url)

# Check the data
for item in website_data:
    print(f"Title: {item['title']}\nURL: {item['url']}\nContent: {item['content'][:100]}...\n")
