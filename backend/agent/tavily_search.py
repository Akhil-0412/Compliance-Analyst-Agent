import os
from tavily import TavilyClient
from dotenv import load_dotenv, find_dotenv

# Force updated env
load_dotenv(find_dotenv(), override=True)

class LawsuitSearcher:
    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")
        print(f"🔧 LawsuitSearcher Init. API Key Present: {bool(api_key)}")
        
        if not api_key:
            print("⚠️ Warning: TAVILY_API_KEY not found. Search will fail.")
            self.client = None
        else:
            self.client = TavilyClient(api_key=api_key)

    def search_lawsuits(self, query: str, max_results=5) -> str:
        """
        Searches for lawsuits and legal precedents using Tavily.
        """
        if not self.client:
            return "❌ Error: Tavily API Key missing. Cannot perform external search."

        print(f"🔎 Tavily Searching: {query}")
        try:
            # Optimized search for legal context
            response = self.client.search(
                query=f"legal lawsuit court case {query}",
                search_depth="advanced",
                max_results=max_results,
                include_answer=True
            )
            
            context = []
            if response.get('answer'):
                context.append(f"**AI Overview:** {response['answer']}")
            
            for res in response.get('results', []):
                context.append(f"- **{res['title']}**: {res['content'][:300]}... [Source]({res['url']})")
                
            return "\n\n".join(context)
            
        except Exception as e:
            return f"⚠️ Search Error: {str(e)}"
