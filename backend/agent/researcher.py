import os
from tavily import TavilyClient
import trafilatura
from typing import Optional, Dict

class LegalResearcher:
    """
    Finds and downloads legal texts from the web.
    """
    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY not found in environment.")
        self.client = TavilyClient(api_key=self.api_key)

    def find_regulation_text(self, law_name: str, region: str) -> Dict[str, str]:
        """
        Searches for the full text of a law.
        Returns: {'url': str, 'content': str, 'title': str}
        """
        query = f"official full text of {law_name} {region} regulation law filetype:html OR filetype:pdf"
        print(f"🔎 Researching: {query}")
        
        # 1. Search with Tavily (advanced search)
        results = self.client.search(
            query=query, 
            search_depth="advanced", 
            max_results=5,
            include_raw_content=False
        )
        
        best_url = None
        # Simple heuristic: Look for .gov or .org or "legislation" in URL
        for r in results.get('results', []):
            url = r['url']
            if any(x in url for x in ['.gov', 'legislation', 'parliament', 'europa.eu', 'law.cornell']):
                best_url = url
                break
        
        if not best_url and results['results']:
            best_url = results['results'][0]['url']
            
        if not best_url:
            raise RuntimeError("No suitable source found for this regulation.")

        print(f"📥 Downloading from: {best_url}")
        
        # 2. Scrape Content
        downloaded = trafilatura.fetch_url(best_url)
        text_content = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
        
        if not text_content or len(text_content) < 500:
             # Fallback: Use Tavily's raw content window if scrape fails?
             # For now, just raise or return partial
             if results['results'][0].get('content'):
                 return {
                     "url": best_url,
                     "content": results['results'][0]['content'],  # Tavily snippet (not ideal for full RAG)
                     "title": results['results'][0]['title']
                 }
             raise RuntimeError(f"Failed to extract content from {best_url}")

        return {
            "url": best_url,
            "content": text_content, # Clean raw text
            "title": results['results'][0]['title']
        }
