# evaluation/__init__.py
"""评估模块"""
from .metrics import (
    compute_win_rate,
    compute_detection_rate,
    compute_linguistic_coherence,
    compute_persuasion_score,
    compute_tom_scores,
    evaluate_game_result,
    evaluate_batch_games
)

__all__ = [
    "compute_win_rate",
    "compute_detection_rate",
    "compute_linguistic_coherence",
    "compute_persuasion_score",
    "compute_tom_scores",
    "evaluate_game_result",
    "evaluate_batch_games"
]

