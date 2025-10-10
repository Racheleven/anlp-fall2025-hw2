import json
import os
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
from transformers import AutoModelForCausalLM, AutoTokenizer
import re
from collections import Counter
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
    
    def search(self, query: str, top_k: int = 5, strategy: str = "hybrid", alpha: float = 0.5) -> List[Dict]:
        """
        Search with configurable strategy.
        
        Args:
            query: Search query
            top_k: Number of results
            strategy: "dense", "sparse", or "hybrid"
            alpha: Weight for dense in hybrid mode (not used in RRF)
            
        Returns:
            List of dicts with 'text', 'score', and 'metadata'
        """
        if strategy == "dense":
            return self._search_dense(query, top_k)
        elif strategy == "sparse":
            return self._search_sparse(query, top_k)
        elif strategy == "hybrid":
            return self._search_hybrid(query, top_k)
        else:
            raise ValueError(f"Unknown strategy: {strategy}. Use 'dense', 'sparse', or 'hybrid'")
    
    def _search_dense(self, query: str, top_k: int) -> List[Dict]:
        """Dense (semantic) search only."""
        query_emb = self.model.encode([query])
        faiss.normalize_L2(query_emb)
        scores, indices = self.faiss_index.search(query_emb, top_k)
        
        results = []
        for idx, score in zip(indices[0], scores[0]):
            results.append({
                'text': self.chunks[idx],
                'score': float(score),
                'metadata': self.metadata[idx]
            })
        
        return results
    
    def _search_sparse(self, query: str, top_k: int) -> List[Dict]:
        """Sparse (BM25) search only."""
        tokenized_query = query.lower().split()
        scores = self.bm25.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[-top_k:][::-1]
        
        results = []
        for idx in top_indices:
            results.append({
                'text': self.chunks[idx],
                'score': float(scores[idx]),
                'metadata': self.metadata[idx]
            })
        
        return results
    
    def _search_hybrid(self, query: str, top_k: int) -> List[Dict]:
        """Hybrid search with RRF fusion."""
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
    
    def retrieve(self, query: str, top_k: int = 5, strategy: str = "hybrid") -> str:
        """Retrieve and format context for RAG."""
        results = self.search(query, top_k, strategy=strategy)
        
        context = "\n\n".join([
            f"[Source: {r['metadata']['json_file']}]\n{r['text']}"
            for r in results
        ])
        
        return context
