from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

def build_index(articles):
    embeddings = model.encode(
        [a["text"] for a in articles],
        normalize_embeddings=True
    )
    return embeddings

ARTICLE_EMBEDDINGS = build_index(ARTICLES)
