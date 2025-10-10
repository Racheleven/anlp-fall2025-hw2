import json
import csv
import re
from pathlib import Path
from simple_rag import SimpleRAG
from openai import OpenAI

def extract_questions_from_csv(csv_path: str):
    """Extract questions from CSV file (every other row starting from row 3)."""
    questions = {}
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
        
        # Start from row 2 (index 2, which is the third row)
        # Take every other row
        for i in range( len(rows), 2):
            if i < len(rows) and rows[i]:
                question_num = (i - 2) // 2 + 1  # Calculate question number
                question_text = rows[i][0] if rows[i] else ""
                if question_text.strip():
                    questions[str(question_num)] = question_text.strip()
    
    return questions


def main():
    # Configuration
    json_dir = '/home/gefeig/code/11711/anlp-fall2025-hw2/crawl_chunks/hybrid'
    model_name = 'all-MiniLM-L6-v2'
    vllm_url = 'http://localhost:8000/v1'
    llm_model = 'Qwen/Qwen2.5-32B-Instruct'
    top_k = 5
    strategy = 'hybrid'
    test_csv_path = '/home/gefeig/code/11711/anlp-fall2025-hw2/test_set_Day1.csv'
    output_json_path = './data/test_answers.json'
    
    print("="*70)
    print("RAG INFERENCE ON TEST SET")
    print("="*70)
    
    # Extract questions from CSV
    print(f"\nLoading questions from: {test_csv_path}")
    questions = extract_questions_from_csv(test_csv_path)
    print(f"Found {len(questions)} questions")
    
    # Initialize RAG system
    print(f"\nInitializing RAG system...")
    rag = SimpleRAG(model_name=model_name)
    rag.load_documents(json_dir)
    rag.build_index()
    
    # Initialize OpenAI client for vLLM
    client = OpenAI(
        api_key="EMPTY",
        base_url=vllm_url
    )
    
    print(f"\nUsing {llm_model} for generation")
    print(f"Retrieval strategy: {strategy}")
    print(f"Top-K: {top_k}")
    
    # Process each question
    answers = {}
    total = len(questions)
    
    for q_num, query in questions.items():
        print(f"\nProcessing question {q_num}/{total}: {query[:80]}...")
        
        # Retrieve context
        context = rag.retrieve(query, top_k=top_k, strategy=strategy)
        
        # Prepare prompt
        prompt = f"""You are a factual QA assistant with deep knowledge of Carnegie Mellon University (CMU) and Pittsburgh.  
Please answer the question below, you can refer to the provided context for answer. 
If the answer is not found in the context, try to answer the question based on your knowledge.
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
                model=llm_model,
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
        extracted_answer = box_match.group(1).strip() if box_match else final_answer
        
        # Store answer
        answers[q_num] = extracted_answer
        
        print(f"Answer: {extracted_answer}")
    
    # Save to JSON file
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(answers, f, ensure_ascii=False, indent=4)
    
    print("\n" + "="*70)
    print(f"COMPLETED! Answers saved to: {output_json_path}")
    print(f"Total questions processed: {len(answers)}")
    print("="*70)


if __name__ == "__main__":
    main()