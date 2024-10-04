from config import AZURE_BING_KEY, AZURE_BING_ENDPOINT, requests

def get_bing_search_results(query):
    headers = {'Ocp-Apim-Subscription-Key': AZURE_BING_KEY}
    params = {'q': query, 'mkt': 'en-US'}
    try:
        response = requests.get(f"{AZURE_BING_ENDPOINT}/v7.0/search", headers=headers, params=params)
        response.raise_for_status()
        search_results = response.json()
        return search_results
    except Exception as e:
        print(f"Error fetching search results: {e}")
        return None

def extract_snippets_from_results(search_results):
    snippets_with_urls = []
    
    if not search_results:
        return snippets_with_urls
    
    web_pages = search_results.get('webPages', {}).get('value', [])
    
    for page in web_pages:
        snippet = page.get('snippet', '')
        url = page.get('url', '')
        
        # Append both snippet and URL to the result list
        snippets_with_urls.append({
            'snippet': snippet,
            'url': url
        })
    
    return snippets_with_urls

