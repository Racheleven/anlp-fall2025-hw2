import os
import json
import requests
import numpy as np
from typing import List, Dict

# =========================
# 1️⃣ 你的 SiliconFlow Embedding 封装（与你提供的一致）
# =========================

class SiliconFlowEmbeddings:
    """
    Lightweight embedding wrapper for SiliconFlow /embeddings endpoint.
    """

    def __init__(self, api_key, base_url="https://api.siliconflow.cn/v1", model="BAAI/bge-m3"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def embed(self, texts):
        if isinstance(texts, str):
            texts = [texts]

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "input": texts
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()

        data = resp.json()
        embeds = [d["embedding"] for d in data["data"]]

        return [np.array(e) for e in embeds]


# =========================
# 2️⃣ GPT 调用（基于 Chat Completions 接口）
# =========================

class SimpleGPTClient:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def invoke(self, prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=60)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


def describe_word_with_gpt(llm: SimpleGPTClient, word: str) -> str:
    prompt = f"""
Please describe the following word in 2-3 concise sentences.
Focus on its core meaning, typical usage, and distinguishing characteristics.

Word: {word}
"""
    return llm.invoke(prompt)


# =========================
# 3️⃣ 工具函数
# =========================

def cosine_similarity(a, b):
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def load_keyword_pairs(path: str):
    with open(path, "r", encoding="utf-8") as f:
        pairs = json.load(f)
    print(f"✅ Loaded {len(pairs)} keyword pairs")
    return pairs


# =========================
# 4️⃣ 核心打分函数（600 组全部打分）
# =========================

def score_keyword_pairs_with_gpt_and_embedding(
    keyword_pairs: List[List[str]],
    gpt_model: SimpleGPTClient,
    embed_model: SiliconFlowEmbeddings
) -> List[Dict]:

    results = []

    for i, (spy_word, civ_word) in enumerate(keyword_pairs):
        print(f"Scoring {i+1}/{len(keyword_pairs)}: {spy_word} vs {civ_word}")

        try:
            spy_desc = describe_word_with_gpt(gpt_model, spy_word)
            civ_desc = describe_word_with_gpt(gpt_model, civ_word)

            emb_spy, emb_civ = embed_model.embed([spy_desc, civ_desc])
            sim = cosine_similarity(emb_spy, emb_civ)

            results.append({
                "spy_word": spy_word,
                "civilian_word": civ_word,
                "spy_desc": spy_desc,
                "civilian_desc": civ_desc,
                "cosine_similarity": sim
            })

        except Exception as e:
            print("❌ Error on:", spy_word, civ_word, str(e))

    return results


# =========================
# 5️⃣ 难度划分（hard / medium / easy 各 200）
# =========================

def split_difficulty_levels(scored_pairs: List[Dict]) -> Dict[str, List[Dict]]:
    scored_pairs = sorted(
        scored_pairs,
        key=lambda x: x["cosine_similarity"],
        reverse=True
    )

    hard = scored_pairs[:200]
    medium = scored_pairs[200:400]
    easy = scored_pairs[400:600]

    return {
        "hard": hard,
        "medium": medium,
        "easy": easy
    }


# =========================
# 6️⃣ 一键运行 Pipeline
# =========================

def build_difficulty_keyword_dataset(
    keyword_pair_path: str,
    gpt_model,
    embed_model,
    save_path: str = "keyword_difficulty_dataset.json",
    full_sorted_save_path: str = "keyword_full_sorted_by_similarity.json",
):
    pairs = load_keyword_pairs(keyword_pair_path)

    scored = score_keyword_pairs_with_gpt_and_embedding(
        keyword_pairs=pairs,
        gpt_model=gpt_model,
        embed_model=embed_model
    )

    # ✅ 新增：全量排序并保存（600条）
    save_full_sorted_results(scored, full_sorted_save_path)

    split = split_difficulty_levels(scored)

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(split, f, indent=2, ensure_ascii=False)

    print(f"✅ Difficulty dataset saved to: {save_path}")
    print(f"✅ Full sorted dataset saved to: {full_sorted_save_path}")
    print("✅ hard:", len(split["hard"]))
    print("✅ medium:", len(split["medium"]))
    print("✅ easy:", len(split["easy"]))

    return split


def save_full_sorted_results(scored_pairs, save_path="keyword_full_sorted_by_similarity_miss.json"):
    """
    将全部 600 条词对结果按 cosine similarity 从高到低排序后保存
    """
    sorted_all = sorted(
        scored_pairs,
        key=lambda x: x["cosine_similarity"],
        reverse=True
    )

    with open(save_path, "w", encoding="utf-8") as f:
        json.dump(sorted_all, f, indent=2, ensure_ascii=False)

    print(f"✅ Full sorted result saved to: {save_path}")
    return sorted_all

# =========================
# 7️⃣主函数入口
# =========================

if __name__ == "__main__":

    # ✅ 你的 API Key 请放在系统环境变量中
    GPT_KEY = "sk-5xFBXEPO4--OrbIPV3yU8A"
    QWEN_KEY = "sk-amcjzxomyzuispivnvvtgszrnxijmxpkmewbvlviffgborlg"

    assert GPT_KEY is not None, "❌ 请先在系统中设置环境变量 GPT_KEY"
    assert QWEN_KEY is not None, "❌ 请先在系统中设置环境变量 QWEN_KEY"

    # ✅ 初始化 GPT（你 CMU 的 gateway）
    gpt_model = SimpleGPTClient(
        api_key=GPT_KEY,
        base_url="https://ai-gateway.andrew.cmu.edu/v1",
        model="gpt-4o-mini-2024-07-18"
    )

    # ✅ 初始化 Embedding（SiliconFlow）
    embed_model = SiliconFlowEmbeddings(
        api_key=QWEN_KEY,
        model="BAAI/bge-m3"
    )

    # ✅ 一键构建难度数据集
    build_difficulty_keyword_dataset(
        keyword_pair_path="key_word_pair.json",  
        gpt_model=gpt_model,
        embed_model=embed_model,
        save_path="keyword_difficulty_dataset.json"
    )
