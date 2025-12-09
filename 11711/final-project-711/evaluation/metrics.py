# evaluation/metrics.py
"""
评估指标计算模块
适配当前项目的游戏状态结构
"""
import numpy as np
from typing import List, Dict, Any, Optional

# Optional external import (commented for now)
# from bert_score import score as bert_score
# from sentence_transformers import SentenceTransformer, util


def compute_win_rate(game_results: List[Dict[str, Any]], role: str = "civilian") -> float:
    """
    计算指定角色的胜率
    
    Args:
        game_results: 游戏结果列表，每个包含:
            {
                "winner": "civilian" 或 "undercover",
                "players": [...],
                ...
            }
        role: 要计算胜率的角色 ("civilian" 或 "undercover")
    
    Returns:
        win_rate: 胜率 (0.0 - 1.0)
    """
    total_games = len(game_results)
    if total_games == 0:
        return 0.0
    
    wins = sum(1 for g in game_results if g.get("winner") == role)
    return wins / total_games


def compute_detection_rate(
    game_logs: List[Dict[str, Any]], 
    player_id: int
) -> float:
    """
    计算卧底被识别的比例（检测率）
    
    Args:
        game_logs: 游戏日志列表，每个包含:
            {
                "round": 1,
                "current_votes": [{"voter_id": 1, "target_id": 3}, ...],
                "eliminated_players": [3],
                "players": [...],  # 包含角色信息
                ...
            }
        player_id: 玩家ID（假设是卧底）
    
    Returns:
        detection_rate: 检测率 (0.0 - 1.0)
    """
    total_rounds = 0
    detected_rounds = 0
    
    for log in game_logs:
        # 检查该玩家是否是卧底
        players = log.get("players", [])
        player = next((p for p in players if p.get("player_id") == player_id), None)
        
        if not player or player.get("role") != "undercover":
            continue
        
        total_rounds += 1
        
        # 检查该玩家是否被投票淘汰
        eliminated = log.get("eliminated_players", [])
        if player_id in eliminated:
            detected_rounds += 1
    
    return detected_rounds / total_rounds if total_rounds > 0 else 0.0


def compute_linguistic_coherence(
    descriptions: List[str], 
    reference: str,
    use_advanced: bool = False
) -> float:
    """
    计算语言连贯性（描述与参考文本的相似度）
    
    Args:
        descriptions: 描述列表
        reference: 参考文本（通常是平民词或标准描述）
        use_advanced: 是否使用高级方法（BERTScore等），需要额外依赖
    
    Returns:
        coherence_score: 平均相似度分数 (0.0 - 1.0)
    """
    if not descriptions:
        return 0.0
    
    if use_advanced:
        # TODO: 使用 BERTScore 或 SentenceTransformer
        # from bert_score import score as bert_score
        # P, R, F1 = bert_score(descriptions, [reference] * len(descriptions), lang='en')
        # return float(F1.mean())
        pass
    
    # 简单方法：基于词汇重叠
    reference_words = set(reference.lower().split())
    if not reference_words:
        return 0.0
    
    similarities = []
    for desc in descriptions:
        desc_words = set(desc.lower().split())
        if desc_words:
            overlap = len(desc_words & reference_words)
            similarity = overlap / len(reference_words)
            similarities.append(similarity)
    
    return np.mean(similarities) if similarities else 0.0


def compute_persuasion_score(utterances: List[str]) -> float:
    """
    计算说服力分数
    
    Args:
        utterances: 玩家的话语列表
    
    Returns:
        persuasion_score: 平均说服力分数 (0.0 - 1.0)
    """
    # TODO: 使用 GPT-4 或其他模型进行评分
    # Placeholder: 返回默认分数
    if not utterances:
        return 0.0
    return 0.5  # 占位符


def compute_tom_scores(
    predictions: Dict[str, Any], 
    ground_truth: Dict[str, Any]
) -> Dict[str, float]:
    """
    计算心理理论（Theory of Mind）分数
    
    Args:
        predictions: Agent的预测，格式:
            {
                "1-word": {player_id: "word", ...},  # 预测其他玩家的词
                "1-identity": {player_id: "civilian", ...},  # 预测其他玩家的身份
                "2-word": {player_id: "word", ...},  # 预测其他玩家认为我的词是什么
                "2-identity": {player_id: "civilian", ...}  # 预测其他玩家认为我的身份是什么
            }
        
        ground_truth: 真实情况，格式:
            {
                "true_words": {player_id: "word", ...},
                "true_identities": {player_id: "civilian", ...},
                "host_inferences": {
                    "word_beliefs": {player_id: "word", ...},
                    "identity_beliefs": {player_id: "civilian", ...}
                }
            }
    
    Returns:
        scores: ToM任务到准确率的映射
    """
    scores = {}
    
    # 1-Word accuracy: 预测其他玩家的词
    true_words = ground_truth.get("true_words", {})
    pred_words = predictions.get("1-word", {})
    if true_words and pred_words:
        correct = sum(1 for pid in true_words 
                     if pred_words.get(pid) == true_words.get(pid))
        scores["1-Word"] = correct / len(true_words) if true_words else 0.0
    else:
        scores["1-Word"] = 0.0
    
    # 1-Identity accuracy: 预测其他玩家的身份
    true_ids = ground_truth.get("true_identities", {})
    pred_ids = predictions.get("1-identity", {})
    if true_ids and pred_ids:
        correct = sum(1 for pid in true_ids 
                     if pred_ids.get(pid) == true_ids.get(pid))
        scores["1-Identity"] = correct / len(true_ids) if true_ids else 0.0
    else:
        scores["1-Identity"] = 0.0
    
    # 2-Word accuracy: 预测其他玩家认为我的词是什么
    host_2w = ground_truth.get("host_inferences", {}).get("word_beliefs", {})
    pred_2w = predictions.get("2-word", {})
    if host_2w and pred_2w:
        correct = sum(1 for pid in host_2w 
                     if pred_2w.get(pid) == host_2w.get(pid))
        scores["2-Word"] = correct / len(host_2w) if host_2w else 0.0
    else:
        scores["2-Word"] = 0.0
    
    # 2-Identity accuracy: 预测其他玩家认为我的身份是什么
    host_2i = ground_truth.get("host_inferences", {}).get("identity_beliefs", {})
    pred_2i = predictions.get("2-identity", {})
    if host_2i and pred_2i:
        correct = sum(1 for pid in host_2i 
                     if pred_2i.get(pid) == host_2i.get(pid))
        scores["2-Identity"] = correct / len(host_2i) if host_2i else 0.0
    else:
        scores["2-Identity"] = 0.0
    
    return scores


def evaluate_game_result(game_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    评估单局游戏结果，计算所有指标
    
    Args:
        game_state: 游戏最终状态，包含:
            - winner: "civilian" 或 "undercover"
            - players: 玩家列表
            - elimination_history: 淘汰历史
            - conversation_history: 对话历史
            - current_descriptions: 当前轮描述
            - current_votes: 当前轮投票
    
    Returns:
        metrics: 包含所有评估指标的字典
    """
    metrics = {}
    
    # 1. 胜率（针对单局游戏，就是是否获胜）
    winner = game_state.get("winner")
    metrics["civilian_won"] = (winner == "civilian")
    metrics["undercover_won"] = (winner == "undercover")
    
    # 2. 检测率（卧底是否被识别）
    players = game_state.get("players", [])
    undercover_players = [p for p in players if p.get("role") == "undercover"]
    eliminated = game_state.get("eliminated_players", [])
    
    if undercover_players:
        detected = sum(1 for p in undercover_players if p["player_id"] in eliminated)
        metrics["detection_rate"] = detected / len(undercover_players)
    else:
        metrics["detection_rate"] = 0.0
    
    # 3. 语言连贯性（基于描述）
    descriptions = game_state.get("current_descriptions", [])
    if descriptions:
        # 使用平民词作为参考
        civilian_word = next(
            (p.get("word") for p in players if p.get("role") == "civilian"), 
            ""
        )
        desc_texts = [d.get("description", "") for d in descriptions]
        metrics["linguistic_coherence"] = compute_linguistic_coherence(
            desc_texts, 
            civilian_word
        )
    else:
        metrics["linguistic_coherence"] = 0.0
    
    # 4. 游戏统计
    metrics["total_rounds"] = game_state.get("round", 0)
    metrics["num_players"] = len(players)
    metrics["num_undercover"] = len(undercover_players)
    metrics["elimination_history"] = game_state.get("elimination_history", [])
    
    return metrics


def evaluate_batch_games(game_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    批量评估多局游戏
    
    Args:
        game_results: 多局游戏的结果列表
    
    Returns:
        summary: 汇总的评估指标
    """
    if not game_results:
        return {}
    
    # 计算胜率
    civilian_wins = sum(1 for g in game_results if g.get("winner") == "civilian")
    undercover_wins = sum(1 for g in game_results if g.get("winner") == "undercover")
    total_games = len(game_results)
    
    # 计算平均检测率
    detection_rates = []
    for game in game_results:
        metrics = evaluate_game_result(game)
        detection_rates.append(metrics.get("detection_rate", 0.0))
    
    # 计算平均语言连贯性
    coherence_scores = []
    for game in game_results:
        metrics = evaluate_game_result(game)
        coherence_scores.append(metrics.get("linguistic_coherence", 0.0))
    
    # 计算平均轮数
    avg_rounds = np.mean([g.get("round", 0) for g in game_results])
    
    return {
        "total_games": total_games,
        "civilian_win_rate": civilian_wins / total_games,
        "undercover_win_rate": undercover_wins / total_games,
        "avg_detection_rate": np.mean(detection_rates) if detection_rates else 0.0,
        "avg_linguistic_coherence": np.mean(coherence_scores) if coherence_scores else 0.0,
        "avg_rounds": avg_rounds,
    }

