# graph/workflow.py
from langgraph.graph import StateGraph, END
from .state import GameState
from .nodes import (
    initialize_game,
    description_phase,
    voting_phase,
    check_win_condition,
    end_game
)

def create_undercover_workflow() -> StateGraph:
    """创建谁是卧底游戏的工作流"""
    
    # 创建状态图
    workflow = StateGraph(GameState)
    
    # 添加节点
    workflow.add_node("initialize", initialize_game)
    workflow.add_node("description", description_phase)
    workflow.add_node("voting", voting_phase)
    workflow.add_node("check", check_win_condition)
    workflow.add_node("end", end_game)
    
    # 设置入口点
    workflow.set_entry_point("initialize")
    
    # 添加边（流程连接）
    workflow.add_edge("initialize", "description")
    workflow.add_edge("description", "voting")
    workflow.add_edge("voting", "check")
    
    # 条件边：根据游戏是否结束决定下一步
    workflow.add_conditional_edges(
        "check",
        lambda state: "end" if state["game_over"] else "description",
        {
            "description": "description",
            "end": "end"
        }
    )
    
    # 游戏结束后退出
    workflow.add_edge("end", END)
    
    return workflow


def run_game(num_players: int = 6, num_undercover: int = 1, game_id: str = None, output_dir: str = "game_results",
             fixed_model_undercover: bool = False, undercover_model_config: dict = None, 
             civilian_model_config: dict = None, default_model_config: dict = None):
    """运行一局游戏
    
    Args:
        num_players: 玩家数量
        num_undercover: 卧底数量
        game_id: 游戏ID（如果为None则自动生成UUID）
        output_dir: 输出目录（默认: game_results）
        fixed_model_undercover: 是否根据身份固定分配模型（默认: False）
        undercover_model_config: 卧底使用的模型配置字典（例如: {"model": "Qwen/Qwen2.5-7B-Instruct"}）
        civilian_model_config: 平民使用的模型配置字典（例如: {"model": "Qwen/Qwen2.5-32B-Instruct"}）
        default_model_config: 默认模型配置字典（当 fixed_model_undercover=False 时使用）
    """
    import uuid
    
    # 创建工作流
    workflow = create_undercover_workflow()
    app = workflow.compile()
    
    # 生成游戏ID（如果未提供）
    if game_id is None:
        game_id = str(uuid.uuid4())
    
    # 初始化状态
    initial_state = {
        "game_id": game_id,  # 使用提供的或生成的游戏ID
        "output_dir": output_dir,  # 传递输出目录
        "num_players": num_players,
        "num_undercover": num_undercover,
        "round": 0,
        "phase": "init",
        "players": [],
        "current_descriptions": [],
        "current_votes": [],
        "eliminated_players": [],
        "elimination_history": [],
        "winner": None,
        "game_over": False,
        "conversation_history": [],
        "fixed_model_undercover": fixed_model_undercover,
        "undercover_model_config": undercover_model_config or {},
        "civilian_model_config": civilian_model_config or {},
        "default_model_config": default_model_config or {}
    }
    
    # 调试信息：打印模型配置
    if fixed_model_undercover:
        print(f"🔍 调试: fixed_model_undercover = {fixed_model_undercover}")
        print(f"🔍 调试: undercover_model_config = {initial_state['undercover_model_config']}")
        print(f"🔍 调试: civilian_model_config = {initial_state['civilian_model_config']}")
    
    # 运行工作流
    print("="*50)
    print("🎮 谁是卧底 - Multi-Agent System")
    print("="*50)
    
    final_state = None
    for state in app.stream(initial_state):
        final_state = state
    
    return final_state


if __name__ == "__main__":
    # 运行游戏
    result = run_game(num_players=6, num_undercover=1)
    
    print("\n" + "="*50)
    print("📊 游戏统计")
    print("="*50)
    print(f"最终获胜方: {'平民' if result['winner'] == 'civilian' else '卧底'}")
    print(f"游戏结束轮数: 第 {result['round']} 轮")
    print(f"总轮数: {result['round']} 轮")