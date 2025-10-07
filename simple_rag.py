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


def normalize_answer(s: str) -> str:
    """Lower text and remove punctuation, articles and extra whitespace."""
    def remove_articles(text):
        return re.sub(r'\b(a|an|the)\b', ' ', text)

    def white_space_fix(text):
        return ' '.join(text.split())

    def remove_punc(text):
        return re.sub(r'[^\w\s]', '', text)

    def lower(text):
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s))))


def exact_match_score(prediction: str, ground_truth: str) -> bool:
    """Check if normalized prediction exactly matches normalized ground truth."""
    return normalize_answer(prediction) == normalize_answer(ground_truth)


def f1_score(prediction: str, ground_truth: str) -> float:
    """Compute token-level F1 score between prediction and ground truth."""
    pred_tokens = normalize_answer(prediction).split()
    truth_tokens = normalize_answer(ground_truth).split()
    if not pred_tokens and not truth_tokens:
        return 1.0
    if not pred_tokens or not truth_tokens:
        return 0.0

    common = Counter(pred_tokens) & Counter(truth_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0

    precision = num_same / len(pred_tokens)
    recall = num_same / len(truth_tokens)
    f1 = 2 * precision * recall / (precision + recall)
    return f1


def answer_recall(retrieved_texts: List[str], answer: str) -> float:
    """Compute answer recall: whether any retrieved chunk contains the answer."""
    normalized_answer = normalize_answer(answer)
    for text in retrieved_texts:
        if normalized_answer in normalize_answer(text):
            return 1.0
    return 0.0


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


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='RAG System with Configurable Retrieval Strategy')
    parser.add_argument(
        '--strategy',
        type=str,
        default='hybrid',
        choices=['dense', 'sparse', 'hybrid'],
        help='Retrieval strategy: dense (semantic), sparse (BM25), or hybrid (RRF fusion)'
    )
    parser.add_argument(
        '--json_dir',
        type=str,
        default='./crawl_chunks',
        help='Directory containing JSON chunk files'
    )
    parser.add_argument(
        '--jsonl_path',
        type=str,
        default='qa_pairs.jsonl',
        help='Path to JSONL file with QA pairs'
    )
    parser.add_argument(
        '--top_k',
        type=int,
        default=5,
        help='Number of chunks to retrieve'
    )
    parser.add_argument(
        '--model_name',
        type=str,
        default='all-MiniLM-L6-v2',
        help='Sentence transformer model name'
    )
    parser.add_argument(
        '--vllm_url',
        type=str,
        default='http://localhost:8000/v1',
        help='vLLM server URL'
    )
    parser.add_argument(
        '--llm_model',
        type=str,
        default='Qwen/Qwen2.5-32B-Instruct',
        help='LLM model name for generation'
    )
    
    return parser.parse_args()


if __name__ == "__main__":
    from openai import OpenAI
    
    # Parse arguments
    args = parse_args()
    
    print("\n" + "="*70)
    print(f"RAG SYSTEM - Strategy: {args.strategy.upper()}")
    print("="*70)
    
    # Initialize and build RAG
    rag = SimpleRAG(model_name=args.model_name)
    rag.load_documents(args.json_dir)
    rag.build_index()
    
    # Initialize OpenAI client for vLLM
    client = OpenAI(
        api_key="EMPTY",
        base_url=args.vllm_url
    )
    
    print(f"Using {args.llm_model} for generation")
    print(f"Retrieval strategy: {args.strategy}")
    print(f"Top-K: {args.top_k}")
    
    # Load questions
    queries = []
    answers = []
    with open(args.jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line.strip())
            queries.append(data["question"])
            answers.append(data["answers"][0])
    
    # print("\n" + "="*70)
    # print("PROCESSING QUESTIONS")
    # print("="*70)
    
    total = len(queries)
    exact_matches = 0
    f1_scores = []
    recall_scores = []

    for idx, query in enumerate(queries):
        # print(f"\n{'='*10} Question {idx+1}/{total} {'='*10}")
        # print(f"Query: {query}")
        
        # Retrieve context with specified strategy
        context = rag.retrieve(query, top_k=args.top_k, strategy=args.strategy)

        # Prepare prompt
        prompt = f"""You are a knowledgeable assistant.  
Please answer the question below, you can refer to the provided context for answer.  
Return only the final answer, wrapped in \\box{{}}.

Context:
{context}

Question:
{query}

Answer:
"""

        # Call vLLM API
        try:
            completion = client.chat.completions.create(
                model=args.llm_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2048,
                top_p=0.8,
            )
            
            content = completion.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error calling vLLM API: {e}")
            content = ""

        # Extract final answer
        final_answer = content.strip()
        box_match = re.search(r'\\box\{(.*?)\}', final_answer)
        if box_match:
            final_answer = box_match.group(1).strip()

        # Calculate metrics
        ground_truth = answers[idx]
        if ground_truth:
            em = exact_match_score(final_answer, ground_truth)
            exact_matches += em
            f1 = f1_score(final_answer, ground_truth)
            f1_scores.append(f1)

            # Calculate answer recall
            retrieved_texts = [r['text'] for r in rag.search(query, top_k=args.top_k, strategy=args.strategy)]
            recall = answer_recall(retrieved_texts, ground_truth)
            recall_scores.append(recall)
            
            # print(f"Ground Truth: {ground_truth}")
            # print(f"Predicted: {final_answer}")
            # print(f"EM: {em}, F1: {f1:.4f}, Recall: {recall}")

    # Print overall metrics
    if total > 0:
        print("\n" + "="*70)
        print("EVALUATION RESULTS")
        print("="*70)
        print(f"Strategy: {args.strategy.upper()}")
        print(f"Total Questions: {total}")
        print(f"Exact Match Accuracy: {exact_matches / total:.4f}")
        if f1_scores:
            print(f"Average F1 Score: {np.mean(f1_scores):.4f}")
        if recall_scores:
            print(f"Average Answer Recall: {np.mean(recall_scores):.4f}")