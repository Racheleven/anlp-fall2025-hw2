import json
import os
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


# Main executionimport json
import re
import numpy as np
from openai import OpenAI

if __name__ == "__main__":
    # Configuration
    JSON_DIR = "./crawl_chunks"
    
    # Initialize and build RAG
    rag = SimpleRAG()
    rag.load_documents(JSON_DIR)
    rag.build_index()
    
    # Initialize OpenAI client for vLLM
    # 默认 vLLM 的 OpenAI 兼容服务运行在 http://localhost:8000/v1
    client = OpenAI(
        api_key="EMPTY",  # vLLM 不需要真实的 API key
        base_url="http://localhost:8000/v1"  # 修改为你的 vLLM 服务地址
    )
    
    model_name = "Qwen/Qwen2.5-32B-Instruct"  # 使用你 vLLM serve 时指定的模型名称
    print(f"Using {model_name} for generation")
    # 从 JSONL 读取问题
    JSONL_PATH = "qa_pairs.jsonl"
    queries = []
    answers = []
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line.strip())
            queries.append(data["question"])
            answers.append(data["answers"][0])
    
    print("\n" + "="*70)
    print("RAG SYSTEM - SEARCH RESULTS")
    print("="*70)
    
    total = len(queries)
    exact_matches = 0
    f1_scores = []
    recall_scores = []

    for idx, query in enumerate(queries):
        print(f"==========={idx}================")
        context = rag.retrieve(query, top_k=5)

        # 准备 prompt
        prompt = f"""You are a knowledgeable assistant.  
Please answer the question below, you can refer to the provided context for answer.  
Return only the final answer, wrapped in \\box{{}}.

Context:
{context}

Question:
{query}

Answer:
"""

        # 使用 OpenAI API 调用 vLLM
        try:
            completion = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2048,  # 根据需要调整
                top_p=0.8,
            )
            
            # 获取生成的内容
            content = completion.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Error calling vLLM API: {e}")
            content = ""

        # 提取最终答案
        final_answer = content.strip()
        # 尝试提取 \\box{} 中的内容
        box_match = re.search(r'\\box\{(.*?)\}', final_answer)
        if box_match:
            final_answer = box_match.group(1).strip()

        # 计算指标
        ground_truth = answers[idx]
        if ground_truth:
            em = exact_match_score(final_answer, ground_truth)
            exact_matches += em
            f1 = f1_score(final_answer, ground_truth)
            f1_scores.append(f1)

            # 计算 answer recall
            retrieved_texts = [r['text'] for r in rag.search(query, top_k=3)]
            recall = answer_recall(retrieved_texts, ground_truth)
            recall_scores.append(recall)
            
            print(f"\nGround Truth: {ground_truth}")
            print(f"Predicted Answer: {final_answer}")

    # 打印整体指标
    if total > 0:
        print("\n" + "="*70)
        print("EVALUATION RESULTS")
        print("="*70)
        print(f"Total Questions: {total}")
        print(f"Exact Match Accuracy: {exact_matches / total:.4f}")
        if f1_scores:
            print(f"Average F1 Score: {np.mean(f1_scores):.4f}")
        if recall_scores:
            print(f"Average Answer Recall: {np.mean(recall_scores):.4f}")