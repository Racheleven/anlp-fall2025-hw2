# graph/state.py
from typing import TypedDict, List, Literal, Annotated, Dict, Any
from operator import add

class PlayerState(TypedDict):
    """单个玩家的状态"""
    player_id: int
    name: str
    role: Literal["civilian", "undercover"]
    word: str
    alive: bool
    description_history: List[str]  # 该玩家的历史描述
    votes_received: int  # 本轮收到的票数

class GameState(TypedDict, total=False):
    """游戏全局状态"""
    # 游戏基本信息
    game_id: str  # 游戏唯一ID
    output_dir: str  # 输出目录
    round: int
    phase: Literal["init", "description", "voting", "check", "end"]
    
    # 玩家信息
    players: List[PlayerState]
    num_players: int
    num_undercover: int
    
    # 当前轮次数据
    current_descriptions: List[dict]  # [{"player_id": 1, "description": "..."}]
    current_votes: List[dict]  # [{"voter_id": 1, "target_id": 2}]
    
    # 历史记录
    eliminated_players: List[int]  # 已淘汰玩家ID列表
    elimination_history: List[dict]  # 淘汰历史详情
    
    # 游戏结果
    winner: Literal["civilian", "undercover", None]
    game_over: bool
    
    # 对话历史（用于调试和展示）
    conversation_history: Annotated[List[dict], add]  # 累加操作
    
    # Agent实例映射（持久化保存，让Agent有记忆）
    agents_map: Dict[int, Any]  # {player_id: PlayerAgent实例}
    
    # 模型配置
    fixed_model_undercover: bool  # 是否根据身份固定分配模型
    undercover_model_config: Dict[str, Any]  # 卧底模型配置
    civilian_model_config: Dict[str, Any]  # 平民模型配置
    default_model_config: Dict[str, Any]  # 默认模型配置（当 fixed_model_undercover=False 时使用）
    
    # 词汇对信息（用于保存游戏结果）
    word_pair: Dict[str, str]  # {"civilian": "...", "undercover": "..."}