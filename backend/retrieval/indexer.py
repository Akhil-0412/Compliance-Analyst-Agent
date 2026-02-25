import faiss
import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi

class ClauseIndexer:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🚀 Embedding Device: {self.device}")
        
        try:
            self.model = SentenceTransformer(model_name, device=self.device)
        except Exception as e:
            print(f"⚠️ Failed to load embedding model ({model_name}): {e}")
            self.model = None

        self.index = None
        self.metadata = []
        self.bm25 = None # Sparse index

    def build(self, texts: list[str], metadata: list[dict]):
        self.metadata = metadata
        
        # 1. Dense (Semantic) Indexing on GPU
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(embeddings.astype(np.float32))

        # 2. Sparse (Keyword) Indexing on CPU
        # We tokenize by splitting on whitespace and removing casing
        tokenized_corpus = [t.lower().split() for t in texts]
        self.bm25 = BM25Okapi(tokenized_corpus)

    def hybrid_search(self, query: str, k=5):
        # 1. Dense Search (GPU-powered meaning search)
        if self.index is None:
            raise RuntimeError("Index not built. Call build() first with texts and metadata.")
        
        q_emb = self.model.encode([query], convert_to_numpy=True)
        distances, dense_ids = self.index.search(np.array([q_emb[0]]).astype(np.float32), k)
        # Ensure we have a flat list of Python integers
        dense_hits = [int(i) for i in dense_ids[0]] 

        # 2. Sparse Search (Keyword overlap search)
        tokenized_query = query.lower().split()
        sparse_scores = self.bm25.get_scores(tokenized_query) if self.bm25 else np.zeros(len(self.metadata))
        # Get indices of top k results
        sparse_hits = np.argsort(sparse_scores)[-k:].tolist()

        # 3. Merge Indices (Deduplicated)
        # Combine both lists and remove duplicates while keeping order
        combined_indices = list(dict.fromkeys(dense_hits + sparse_hits))
        
        # 4. Critical Metadata Recovery
        results = []
        for idx in combined_indices:
            # SAFETY: Ensure the index is within range and is a dictionary
            if idx < len(self.metadata):
                item = self.metadata[idx]
                if isinstance(item, dict) and 'article_id' in item:
                    results.append(item)
                else:
                    # If this triggers, your metadata was built as strings, not dicts
                    print(f"⚠️ Warning: Metadata at index {idx} is invalid type: {type(item)}")
            
        return results[:k]

    def get_full_article(self, article_id: str):
        # Filter all metadata for the same article_id
        full_text = []
        # Sort them by clause_id to ensure logical reading order
        article_clauses = [m for m in self.metadata if m['article_id'] == article_id]
        article_clauses.sort(key=lambda x: x['clause_id'])
        
        for c in article_clauses:
            full_text.append(f"[{c['clause_id']}] {c['text']}")
        
        return "\n".join(full_text)