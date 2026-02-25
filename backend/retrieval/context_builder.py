# retrieval/context_builder.py
import json

class ContextBuilder:
    def __init__(self, data_path: str):
        with open(data_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        
        # Pre-index articles for O(1) lookup
        self.article_map = {str(a['article_id']): a for a in self.data['articles']}

    def expand_article_by_id(self, article_id: str):
        article = self.article_map.get(str(article_id))
        if not article:
            return f"[Error: Article {article_id} not found in structured data]"
        
        clauses = sorted(article['clauses'], key=lambda x: x['clause_id'])
        full_text = [f"Article {article_id}: {article.get('title', '')}"]
        full_text.extend([f"[{c['clause_id']}] {c['text']}" for c in clauses])
        
        return "\n".join(full_text)