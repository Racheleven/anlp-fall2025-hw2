# data/word_pairs.py
"""词汇对数据加载模块"""
import json
import os
from typing import List, Dict, Literal

# 默认词汇对（中文）
DEFAULT_WORD_PAIRS = [
    {"civilian": "苹果", "undercover": "梨"},
    {"civilian": "牛奶", "undercover": "豆浆"},
    {"civilian": "包子", "undercover": "饺子"},
    {"civilian": "眉毛", "undercover": "睫毛"},
    {"civilian": "医生", "undercover": "护士"},
    {"civilian": "玫瑰", "undercover": "月季"},
    {"civilian": "饼干", "undercover": "薯片"},
    {"civilian": "西瓜", "undercover": "哈密瓜"},
]


def load_word_pairs(
    difficulty: Literal["easy", "medium", "hard", "all", "default"] = "default",
    data_dir: str = None
) -> List[Dict[str, str]]:
    """
    加载词汇对数据
    
    Args:
        difficulty: 难度级别 ("easy", "medium", "hard", "all", "default")
        data_dir: 数据目录路径，如果为None则使用默认路径
    
    Returns:
        List[Dict[str, str]]: 词汇对列表，格式为 [{"civilian": "...", "undercover": "..."}, ...]
    """
    if difficulty == "default":
        return DEFAULT_WORD_PAIRS.copy()
    
    if data_dir is None:
        # 默认使用当前 data 目录
        data_dir = os.path.dirname(__file__)
    
    word_pairs = []
    
    if difficulty == "all":
        # 加载所有难度的数据
        for diff in ["easy", "medium", "hard"]:
            pairs = _load_json_word_pairs(data_dir, diff)
            word_pairs.extend(pairs)
    else:
        # 加载指定难度的数据
        word_pairs = _load_json_word_pairs(data_dir, difficulty)
    
    return word_pairs


def _load_json_word_pairs(data_dir: str, difficulty: str) -> List[Dict[str, str]]:
    """从JSON文件加载词汇对"""
    # 文件名映射
    filename_map = {
        "easy": "easy_keyword_pair.json",
        "medium": "midium_keyword_pair.json",  # 注意原文件名拼写
        "hard": "hard_keyword_pair.json",
    }
    
    filename = filename_map.get(difficulty)
    if not filename:
        return []
    
    filepath = os.path.join(data_dir, filename)
    
    if not os.path.exists(filepath):
        print(f"⚠️  警告: 文件不存在 {filepath}")
        return []
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 转换格式: [["word1", "word2"], ...] -> [{"civilian": "word1", "undercover": "word2"}, ...]
        word_pairs = []
        for pair in data:
            if isinstance(pair, list) and len(pair) >= 2:
                word_pairs.append({
                    "civilian": pair[0],
                    "undercover": pair[1]
                })
        
        print(f"✅ 已加载 {len(word_pairs)} 个 {difficulty} 难度的词汇对")
        return word_pairs
    
    except Exception as e:
        print(f"❌ 加载词汇对失败: {e}")
        return []


def get_word_pairs_by_difficulty(
    data_dir: str = None
) -> Dict[str, List[Dict[str, str]]]:
    """
    获取按难度分类的词汇对
    
    Returns:
        Dict[str, List[Dict]]: {"easy": [...], "medium": [...], "hard": [...]}
    """
    if data_dir is None:
        # 默认使用当前 data 目录
        data_dir = os.path.dirname(__file__)
    
    result = {}
    for difficulty in ["easy", "medium", "hard"]:
        result[difficulty] = _load_json_word_pairs(data_dir, difficulty)
    
    return result

