import json
import os
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi


class SimpleRAG:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize RAG system."""
        print(f"Loading model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.chunks = []
        self.metadata = []
        self.faiss_index = None
        self.bm25 = None
        
    def load_documents(self, json_dir: str):
        """Load all JSON files from directory."""
        json_dir = Path(json_dir)
        json_files = list(json_dir.glob("*.json"))
        
        print(f"Found {len(json_files)} JSON files")
        
        for json_file in json_files:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                file_path = data.get('file_path', str(json_file))
                chunks = data.get('chunks', [])
                
                for i, chunk in enumerate(chunks):
                    self.chunks.append(chunk)
                    self.metadata.append({
                        'source': file_path,
                        'chunk_id': i,
                        'json_file': str(json_file.name)
                    })
        
        print(f"Loaded {len(self.chunks)} chunks from {len(json_files)} files")
        return self
    
    def build_index(self):
        """Build FAISS and BM25 indices."""
        if not self.chunks:
            raise ValueError("No documents loaded. Call load_documents() first.")
        
        print("Building indices...")
        
        # Build dense index
        embeddings = self.model.encode(self.chunks, show_progress_bar=True, batch_size=32)
        faiss.normalize_L2(embeddings)
        
        self.faiss_index = faiss.IndexFlatIP(embeddings.shape[1])
        self.faiss_index.add(embeddings)
        
        # Build sparse index
        tokenized = [chunk.lower().split() for chunk in self.chunks]
        self.bm25 = BM25Okapi(tokenized)
        
        print("Index built successfully!")
        return self
    
    def search(self, query: str, top_k: int = 5, alpha: float = 0.5) -> List[Dict]:
        """
        Hybrid search with RRF fusion.
        
        Args:
            query: Search query
            top_k: Number of results
            alpha: Weight for dense (not used in RRF, kept for compatibility)
            
        Returns:
            List of dicts with 'text', 'score', and 'metadata'
        """
        # Dense search
        query_emb = self.model.encode([query])
        faiss.normalize_L2(query_emb)
        dense_scores, dense_indices = self.faiss_index.search(query_emb, top_k * 2)
        
        # Sparse search
        tokenized_query = query.lower().split()
        sparse_scores = self.bm25.get_scores(tokenized_query)
        sparse_indices = np.argsort(sparse_scores)[-top_k*2:][::-1]
        
        # RRF fusion
        rrf_scores = {}
        k = 60
        
        for rank, idx in enumerate(dense_indices[0], 1):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1 / (k + rank)
        
        for rank, idx in enumerate(sparse_indices, 1):
            rrf_scores[idx] = rrf_scores.get(idx, 0) + 1 / (k + rank)
        
        # Get top-k
        sorted_indices = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        results = []
        for idx, score in sorted_indices:
            results.append({
                'text': self.chunks[idx],
                'score': score,
                'metadata': self.metadata[idx]
            })
        
        return results
    
    def retrieve(self, query: str, top_k: int = 5) -> str:
        """Retrieve and format context for RAG."""
        results = self.search(query, top_k)
        
        context = "\n\n".join([
            f"[Source: {r['metadata']['json_file']}]\n{r['text']}"
            for r in results
        ])
        
        return context


# Main execution
if __name__ == "__main__":
    # Configuration
    JSON_DIR = "./crawl_chunks"
    
    # Initialize and build RAG
    rag = SimpleRAG()
    rag.load_documents(JSON_DIR)
    rag.build_index()
    
    # 从 JSONL 读取问题
    JSONL_PATH = "qa_pairs.jsonl"
    queries = []
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line.strip())
            queries.append(data["question"])
    
    print("\n" + "="*70)
    print("RAG SYSTEM - SEARCH RESULTS")
    print("="*70)
    
    for query in queries:
        print(f"\nQuery: {query}")
        print("-" * 70)
        context = rag.retrieve(query, top_k=3)
        print(context)
    #     results = rag.search(query, top_k=3)
        
    #     for i, result in enumerate(results, 1):
    #         print(f"\n{i}. Score: {result['score']:.4f}")
    #         print(f"   Source: {result['metadata']['json_file']}")
    #         print(f"   Text: {result['text'][:200]}...")
        
    #     print("\n" + "="*70)
    
    # # Show formatted context for LLM
    # print("\n\nFORMATTED CONTEXT FOR LLM:")
    # print("="*70)
    # if queries:
    #     context = rag.retrieve(queries[0], top_k=3)
    #     print(context)
