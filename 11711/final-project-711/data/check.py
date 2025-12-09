import json

# ===== 1. 读取 前者：大词表（hard/medium/easy）=====
with open("keyword_difficulty_dataset.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# 收集前者中所有出现过的词
former_words = set()
for group in data.values():   # hard / medium / easy
    for item in group:
        former_words.add(item["spy_word"].strip())
        former_words.add(item["civilian_word"].strip())

print(f"✅ 前者词表总词数: {len(former_words)}")


# ===== 2. 读取 后者：pair 词表 =====
with open("key_word_pair.json", "r", encoding="utf-8") as f:
    pairs = json.load(f)

latter_words = set()
for a, b in pairs:
    latter_words.add(a.strip())
    latter_words.add(b.strip())

print(f"✅ 后者词表总词数: {len(latter_words)}")


# ===== 3. 查找：后者有，但前者没有的词 =====
missing_words = sorted(latter_words - former_words)

print("\n❌ 后者中【前者不存在】的词如下：")
for w in missing_words:
    print(w)

print(f"\n❗ 缺失词总数: {len(missing_words)}")


# ===== 4. 可选：导出为 json 方便你保存 =====
with open("missing_words.json", "w", encoding="utf-8") as f:
    json.dump(missing_words, f, ensure_ascii=False, indent=2)

print("\n📁 已导出：missing_words.json")
