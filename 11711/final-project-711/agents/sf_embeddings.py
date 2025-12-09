# agents/sf_embeddings.py
import requests
import numpy as np

class SiliconFlowEmbeddings:
    """
    Lightweight embedding wrapper for SiliconFlow /embeddings endpoint.
    """

    def __init__(self, api_key, base_url="https://api.siliconflow.cn/v1", model="BAAI/bge-m3"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    def embed(self, texts):
        """Return embeddings for single string or list of strings."""
        if isinstance(texts, str):
            texts = [texts]

        url = f"{self.base_url}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,     # 推荐 bge-m3 或 bge-large-zh-v1.5
            "input": texts
        }

        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()

        data = resp.json()
        embeds = [d["embedding"] for d in data["data"]]

        return [np.array(e) for e in embeds]
