# agents/retrieval_engine.py
import numpy as np
import faiss
import os
from agents.sf_embeddings import SiliconFlowEmbeddings

# 降维后的维度，可调节
PCA_DIM = 128
# INDEX_PATH = "cheatsheet.index"
# TEXT_PATH = "cheatsheet_texts.json"
# PCA_PATH = "cheatsheet_pca.npy"


class RetrievalEngine:
    def __init__(self, api_key, base_url, embedding_model="BAAI/bge-m3",prefix="default"):
        self.embedder = SiliconFlowEmbeddings(
            api_key=api_key,
            base_url=base_url,
            model=embedding_model
        )
        self.prefix = prefix
        self.pool_text = []
        self.embedding_cache = {}
        self.index = None
        self.pca_matrix = None   # PCA 降维矩阵
        self.INDEX_PATH = f"{self.prefix}_cheatsheet.index"
        self.TEXT_PATH = f"{self.prefix}_cheatsheet_texts.json"
        self.PCA_PATH = f"{self.prefix}_cheatsheet_pca.npy"
        # 尝试直接加载保存的索引
        self._try_load_index()

    # ------------------------------
    #  PCA 工具
    # ------------------------------
    def _fit_pca(self, matrix):
        """Fit PCA matrix using SVD"""
        U, S, Vt = np.linalg.svd(matrix - matrix.mean(0), full_matrices=False)
        pca = Vt[:PCA_DIM]   # 选取前 PCA_DIM 主成分
        np.save(self.PCA_PATH, pca)
        return pca

    def _apply_pca(self, vec):
        if self.pca_matrix is None:
            return vec.astype("float32")
        return vec @ self.pca_matrix.T

    # ------------------------------
    # 保存 / 加载索引
    # ------------------------------
    def _try_load_index(self):
        """Load FAISS index + text list + PCA if exists."""
        import json

        if not os.path.exists(self.INDEX_PATH) or not os.path.exists(self.TEXT_PATH):
            return

        # load pca
        if os.path.exists(self.PCA_PATH):
            self.pca_matrix = np.load(self.PCA_PATH)

        # load FAISS
        self.index = faiss.read_index(self.INDEX_PATH)

        # load text list
        with open(self.TEXT_PATH, "r", encoding="utf-8") as f:
            self.pool_text = json.load(f)

        print("[RetrievalEngine] Successfully loaded cached FAISS index.")

    def _save_index(self):
        """Save FAISS + texts + PCA matrix"""
        import json

        faiss.write_index(self.index, self.INDEX_PATH)

        with open(self.TEXT_PATH, "w", encoding="utf-8") as f:
            json.dump(self.pool_text, f, ensure_ascii=False, indent=2)

        if self.pca_matrix is not None:
            np.save(self.PCA_PATH, self.pca_matrix)

        print("[RetrievalEngine] Index saved to disk.")

    # ------------------------------
    # 获取 embedding（含缓存 + PCA）
    # ------------------------------
    def _get_embedding(self, text):
        if text in self.embedding_cache:
            return self.embedding_cache[text]

        emb = self.embedder.embed(text)[0].astype("float32")

        # Apply PCA if exists
        if self.pca_matrix is not None:
            emb = self._apply_pca(emb)

        self.embedding_cache[text] = emb
        return emb

    # ------------------------------
    # 构建索引（第一次构建）
    # ------------------------------
    def _build_index(self):
        emb_matrix = np.array([self._get_embedding(t) for t in self.pool_text])

        # Fit PCA only on first build
        if self.pca_matrix is None and emb_matrix.shape[0] >= PCA_DIM:
            self.pca_matrix = self._fit_pca(emb_matrix)
            emb_matrix = emb_matrix @ self.pca_matrix.T

        dim = emb_matrix.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(emb_matrix)

        self._save_index()

    # ------------------------------
    # 添加新的记忆条目
    # ------------------------------
    def add(self, text: str):
        if text in self.pool_text:
            return

        self.pool_text.append(text)

        # rebuild full index anytime new strategy added
        self._build_index()

    # ------------------------------
    # 搜索
    # ------------------------------
    def search(self, query: str, top_k: int = 5):
        if self.index is None or len(self.pool_text) == 0:
            return []

        q_vec = self._get_embedding(query).reshape(1, -1)
        scores, indices = self.index.search(q_vec, top_k)

        results = []
        for idx in indices[0]:
            if idx == -1:
                continue
            results.append(self.pool_text[idx])

        return results

