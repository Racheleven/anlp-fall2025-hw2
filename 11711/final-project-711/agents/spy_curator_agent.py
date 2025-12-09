# agents/spy_curator_agent.py
import json

CURATOR_TEMPLATE = """
You are the SpyGame Dynamic Cheatsheet Curator (Retrieval + Synthesis Mode).

You are given:
1. Retrieved memory items (summaries of past failures/successes):
{retrieved}

2. Current game log:
{game_log}

Task:
- Integrate retrieved items with new insights from the current game.
- Extract reusable strategies.
- Each strategy must be one line.
- DO NOT output JSON. Output plain text lines only.
"""

class SpyCuratorAgent:
    def __init__(self, llm):
        self.llm = llm

    def summarize(self, retrieved_items, game_log):
        retr = "\n".join(f"- {x}" for x in retrieved_items)
        prompt = CURATOR_TEMPLATE.format(
            retrieved=retr,
            game_log=json.dumps(game_log, ensure_ascii=False)
        )
        resp = self.llm.invoke(prompt)
        lines = resp.content.strip().split("\n")
        return [l.replace("-", "").strip() for l in lines if l.strip()]
