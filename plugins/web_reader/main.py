import requests
from bs4 import BeautifulSoup
import re

def extract_text_from_url(url):
    """
    Fetches the content of a URL and extracts the visible text.
    """
    try:
        # Set a user agent to avoid being blocked by some sites
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
            
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading/trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Limit text length to avoid context window issues (e.g., 10000 chars)
        return text[:10000]
        
    except Exception as e:
        print(f"Error fetching URL {url}: {e}")
        return None

def get_summarization_prompt(text):
    """
    Returns the prompt for summarizing the web page content.
    """
    return f"""Please provide a brief and comprehensive summary of the following web page content.
Focus on the main points and key information.

CONTENT:
{text}"""

def is_plugin_applicable(messages, provider):
    """
    Returns True if the last message contains a URL but is NOT a YouTube link.
    """
    if not messages:
        return False
    
    last_message = messages[-1]
    if last_message.get("role") != "user":
        return False
    
    content = last_message.get("content", "")
    
    url = None
    if isinstance(content, str):
        # Simple regex for URL
        url_match = re.search(r'https?://\S+', content)
        if url_match:
            url = url_match.group(0)
    elif isinstance(content, list):
        for part in content:
            if part.get("type") == "text":
                text = part.get("text", "")
                url_match = re.search(r'https?://\S+', text)
                if url_match:
                    url = url_match.group(0)
                    break
    
    if url:
        # Exclude YouTube links as they are handled by another plugin
        if "youtube.com" in url or "youtu.be" in url:
            return False
        return True
            
    return False

def process_messages(messages, provider):
    """
    Modifies the messages by replacing the URL with the web page content and summarization prompt.
    """
    if not messages:
        return messages

    last_message = messages[-1]
    content = last_message.get("content", "")
    
    url = None
    if isinstance(content, str):
        url_match = re.search(r'https?://\S+', content)
        if url_match:
            url = url_match.group(0)
    elif isinstance(content, list):
        for part in content:
            if part.get("type") == "text":
                text = part.get("text", "")
                url_match = re.search(r'https?://\S+', text)
                if url_match:
                    url = url_match.group(0)
                    break
    
    if url:
        print(f"Plugin web_reader processing URL: {url}")
        text = extract_text_from_url(url)
        if text:
            prompt = get_summarization_prompt(text)
            messages[-1]["content"] = prompt
            print("Plugin web_reader: Content attached to messages.")
        else:
            print("Plugin web_reader: Failed to fetch content.")
            
    return messages
