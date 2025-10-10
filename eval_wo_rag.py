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
from simple_rag import SimpleRAG

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


def answer_recall(prediction: str, ground_truth: str) -> float:
    """Compute recall between model prediction and ground truth answer."""
    pred_tokens = normalize_answer(prediction).split()
    gt_tokens = normalize_answer(ground_truth).split()

    if not gt_tokens:
        return 0.0  # avoid divide by zero

    # overlap count = number of common tokens
    common = set(pred_tokens) & set(gt_tokens)
    recall = len(common) / len(set(gt_tokens))
    return recall


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
    parser.add_argument(
        '--output_file',
        type=str,
        default='rag_results.jsonl',
        help='Output JSONL file to save model responses'
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
    print(f"Output file: {args.output_file}")
    
    # Load questions
    queries = []
    answers = []
    with open(args.jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line.strip())
            queries.append(data["question"])
            answers.append(data["answers"][0])
    
    # Open output file for writing
    output_file = open(args.output_file, 'w', encoding='utf-8')
    
    total = len(queries)
    exact_matches = 0
    f1_scores = []
    recall_scores = []

    for idx, query in enumerate(queries):
        # Retrieve context with specified strategy
        retrieved_results = rag.search(query, top_k=args.top_k, strategy=args.strategy)
        context = rag.retrieve(query, top_k=args.top_k, strategy=args.strategy)

#         # Prepare prompt
        prompt = f"""You are a factual QA assistant with deep knowledge of Carnegie Mellon University (CMU) and Pittsburgh.  
Return only the final answer, wrapped in \\box{{}}.

Question:
{query}

Answer:
"""
        # prompt = f"""You are a factual QA assistant with deep knowledge of Carnegie Mellon University (CMU) and Pittsburgh.  
        #     Using the retrieved context and the user’s query, provide an accurate, fact-based answer.

        #     <input>
        #     Retrieved context:
        #     {context}

        #     User query:
        #     {query}
        #     </input>

        #     <instruction>
        #     - If the answer is explicitly mentioned in the context, stay strictly faithful to it.  
        #     - If the context does not contain the answer, respond based on your own reliable knowledge.  
        #     - Keep your response concise and factual, without unnecessary explanations.  
        #     - Return **only** the final answer, wrapped in \\box{{}}.
        #     </instruction>

        #     <output example>
        #     \\box{{1900}}
        #     </output example>

        #     <output format>
        #     \\box{{}}.
        #     </output format>

        #     Now generate your answer:
        #     """
        # Call vLLM API
        try:
            completion = client.chat.completions.create(
                model=args.llm_model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
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
        # box_match = re.search(r'\\box\{\{(.*?)\}\}', final_answer)
        extracted_answer = box_match.group(1).strip() if box_match else final_answer

        # Calculate metrics
        ground_truth = answers[idx]
        em = 0
        f1 = 0.0
        recall = 0.0
        
        if ground_truth:
            em = exact_match_score(extracted_answer, ground_truth)
            exact_matches += em
            f1 = f1_score(extracted_answer, ground_truth)
            f1_scores.append(f1)

            # Calculate answer recall
            retrieved_texts = [r['text'] for r in retrieved_results]
            recall = answer_recall(extracted_answer, ground_truth)
            recall_scores.append(recall)
        
        # Prepare output record
        output_record = {
            'question_id': idx,
            'question': query,
            'ground_truth': ground_truth,
            'raw_response': content,
            'extracted_answer': extracted_answer,
            'retrieved_contexts': [
                {
                    'text': r['text'],
                    'score': r['score'],
                    'source': r['metadata']['json_file']
                }
                for r in retrieved_results
            ],
            'metrics': {
                'exact_match': bool(em),
                'f1_score': float(f1),
                'answer_recall': float(recall)
            },
            'config': {
                'strategy': args.strategy,
                'top_k': args.top_k,
                'model': args.llm_model
            }
        }
        
        # Write to output file
        output_file.write(json.dumps(output_record, ensure_ascii=False) + '\n')
        output_file.flush()  # Ensure data is written immediately
        
        # Print progress
        if (idx + 1) % 10 == 0 or (idx + 1) == total:
            print(f"Processed {idx + 1}/{total} questions...")

    # Close output file
    output_file.close()
    print(f"\nResults saved to: {args.output_file}")

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
    
    summary_path = "/home/gefeig/code/11711/anlp-fall2025-hw2/rag_wo.txt"
    with open(summary_path, "a", encoding="utf-8") as f:
        f.write(f"Model: {args.llm_model}\n")
        f.write(f"Top-K: {args.top_k}\n")
        f.write(f"json_dir: {args.json_dir}\n")
        f.write(f"Strategy: {args.strategy.upper()}\n")
        f.write(f"Total Questions: {total}\n")
        f.write(f"Exact Match Accuracy: {exact_matches / total:.4f}\n")
        if f1_scores:
            f.write(f"Average F1 Score: {np.mean(f1_scores):.4f}\n")
        if recall_scores:
            f.write(f"Average Answer Recall: {np.mean(recall_scores):.4f}\n")
        f.write("="*60 + "\n")
    print(f"Summary written to {summary_path}")
