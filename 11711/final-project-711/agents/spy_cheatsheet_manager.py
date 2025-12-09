# agents/spy_cheatsheet_manager.py
import json
import os
from agents.retrieval_engine import RetrievalEngine

MAX_CHEATSHEET_SIZE = 10

class SpyCheatSheetManager:
    def __init__(self, path="cheatsheet_memory.json", api_key=None, base_url=None,prefix="default"):
        self.path = path
        self.pool = []
        self.prefix = prefix

        # load texts
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                self.pool = json.load(f)

        # RetrievalEngine will automatically load FAISS index if exists
        self.engine = RetrievalEngine(api_key=api_key, base_url=base_url,prefix=self.prefix)

        # If no FAISS index exists but pool has content → build once
        if self.engine.index is None and len(self.pool) > 0:
            print("[SpyCheatSheetManager] No index found, building new index...")
            for item in self.pool:
                self.engine.add(item)

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.pool, f, ensure_ascii=False, indent=2)

    def add_item(self, text):
        if text in self.pool:
            return

        self.pool.append(text)
        if len(self.pool) > MAX_CHEATSHEET_SIZE:
            self.pool = self.pool[-MAX_CHEATSHEET_SIZE:]

        self.save()

        # let RetrievalEngine rebuild + save FAISS
        self.engine.add(text)

    def retrieve(self, query, top_k=5):
        return self.engine.search(query, top_k)



