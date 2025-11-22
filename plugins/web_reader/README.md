# Web Reader Plugin

## Description
This plugin detects general web URLs (excluding YouTube), fetches the page content, extracts the visible text, and asks the LLM to provide a comprehensive summary.

## How it Works
1.  **Detection:** The plugin scans for `http` or `https` URLs. It explicitly ignores YouTube links (handled by another plugin).
2.  **Scraping:** It uses `requests` and `BeautifulSoup` to fetch the HTML and extract text, removing scripts and styles.
3.  **Prompt Generation:** It replaces the URL with a prompt containing the page text and a request for summary.
4.  **Processing:** The LLM summarizes the content.

## Requirements
- `requests`
- `beautifulsoup4`

## Compatibility
- Works with all text-based LLM providers.
