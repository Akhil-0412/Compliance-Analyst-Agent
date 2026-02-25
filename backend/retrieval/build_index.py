import json
from indexer import ClauseIndexer

# Load the structured GDPR data you saved in Step 1.3
with open("data/processed/gdpr_structured.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Inside build_index.py
texts_to_embed = []
metadatas = []

indexer = ClauseIndexer()

for article in data["articles"]:
    article_title = article.get("title", "GDPR")
    for clause in article["clauses"]:
        # Title Injection for Article 25 hits
        enriched_text = f"Article {article['article_id']} - {article_title}: {clause['text']}"
        texts_to_embed.append(enriched_text)
        
        # KEY: This dictionary MUST contain 'article_id'
        metadatas.append({
            "article_id": str(article["article_id"]),
            "clause_id": clause["clause_id"],
            "clause_type": clause.get("clause_type", "other"),
            "text": clause["text"]
        })

indexer.build(texts_to_embed, metadatas)



# Test the Hybrid Precision
# 1. Search for the specific concept
results = indexer.hybrid_search("What are the rules for data protection by design?", k=1)
top_hit = results[0]

# 2. Expand context to Article 25
full_context = indexer.get_full_article(top_hit['article_id'])

print(f"--- ANALYST INPUT (ARTICLE {top_hit['article_id']}) ---")
print(full_context)