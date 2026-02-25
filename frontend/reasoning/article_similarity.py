import numpy as np
from reasoning.article_corpus import ARTICLES
from reasoning.article_index import ARTICLE_EMBEDDINGS

def find_related_articles(reasoning_nodes, threshold=0.75):
    related = set()

    for node in reasoning_nodes:
        vec = model.encode(node.legal_meaning, normalize_embeddings=True)
        sims = np.dot(ARTICLE_EMBEDDINGS, vec)

        for idx, score in enumerate(sims):
            if score >= threshold:
                related.add(ARTICLES[idx]["article"])

    return related
