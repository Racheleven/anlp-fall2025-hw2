import json
import random


def sample_keyword_pairs(
    input_path="keyword_pair.json",
    output_path="sampled_50_keyword_pair.json",
    k=50,
    seed=None
):
    """
    从 keyword_pair.json 中随机抽取 k 个 pair，保存为新 json
    """
    if seed is not None:
        random.seed(seed)

    # 1. 读取原始数据
    with open(input_path, "r", encoding="utf-8") as f:
        pairs = json.load(f)

    # 2. 数据量检查
    if len(pairs) < k:
        raise ValueError(f"数据只有 {len(pairs)} 条，无法抽取 {k} 条")

    # 3. 随机抽样（不重复）
    sampled_pairs = random.sample(pairs, k)

    # 4. 保存新 JSON
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sampled_pairs, f, ensure_ascii=False, indent=4)

    print(f"✅ 已成功生成 {k} 条数据到：{output_path}")


# =========================
# ✅ 示例调用
# =========================
sample_keyword_pairs(
    input_path="key_word_pair_food_animal.json",              # 你的原始文件
    output_path="key_word_pair_food_animal_50.json",  # 新文件
    k=50,                                        # 抽 50 个
    seed=42                                      # 可选：固定随机种子（保证可复现）
)
