# graph/nodes.py
import random
import json
import os
import uuid
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from .state import GameState, PlayerState
from agents import PlayerAgent, GameModel

# 默认词汇对数据库（中文）
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

# 全局词汇对（可以通过 load_word_pairs 函数设置）
WORD_PAIRS = DEFAULT_WORD_PAIRS.copy()


def set_word_pairs(word_pairs: List[Dict[str, str]]):
    """设置全局词汇对"""
    global WORD_PAIRS
    WORD_PAIRS = word_pairs


def initialize_game(state: GameState) -> GameState:
    """初始化游戏节点"""
    print("🎮 初始化游戏...")
    
    # 生成游戏ID（如果还没有）
    game_id = state.get("game_id")
    if not game_id:
        game_id = str(uuid.uuid4())
        print(f"🆔 生成游戏ID: {game_id}")
    else:
        print(f"🆔 使用游戏ID: {game_id}")
    
    num_players = state.get("num_players",3)
    num_undercover = state.get("num_undercover", 1)
    
    # 从state中获取词汇对，如果没有则使用全局WORD_PAIRS
    word_pairs = state.get("word_pairs", WORD_PAIRS)
    if not word_pairs:
        word_pairs = WORD_PAIRS
    
    # 随机选择词汇对
    word_pair = random.choice(word_pairs)
    
    # 随机分配卧底
    undercover_indices = random.sample(range(num_players), num_undercover)
    
    # 创建玩家（先分配身份）
    players = []
    for i in range(num_players):
        is_undercover = i in undercover_indices
        player = PlayerState(
            player_id=i + 1,
            name=f"PLAYER{i + 1}",
            role="undercover" if is_undercover else "civilian",
            word=word_pair["undercover"] if is_undercover else word_pair["civilian"],
            alive=True,
            description_history=[],
            votes_received=0
        )
        players.append(player)
    
    print(f"✅ 游戏初始化完成：{num_players}名玩家，{num_undercover}名卧底")
    print(f"📝 词汇对：平民-{word_pair['civilian']} vs 卧底-{word_pair['undercover']}")
    
    # 根据配置分配模型（在身份分配之后）
    print("🤖 初始化模型...")
    fixed_model_undercover = state.get("fixed_model_undercover", False)
    undercover_model_config = state.get("undercover_model_config", {})
    civilian_model_config = state.get("civilian_model_config", {})
    default_model_config = state.get("default_model_config", {})
    
    models = []
    for i, player in enumerate(players):
        if fixed_model_undercover:
            # 根据身份分配不同的模型
            if player["role"] == "undercover":
                # 卧底使用指定模型配置
                if undercover_model_config and undercover_model_config.get('model'):
                    model = GameModel(**undercover_model_config)
                    print(f"  玩家{player['player_id']} ({player['role']}) 使用模型: {undercover_model_config.get('model')}")
                else:
                    model = GameModel()
                    print(f"  玩家{player['player_id']} ({player['role']}) 使用模型: 默认模型 (未提供卧底模型配置)")
            else:
                # 平民使用指定模型配置
                if civilian_model_config and civilian_model_config.get('model'):
                    model = GameModel(**civilian_model_config)
                    print(f"  玩家{player['player_id']} ({player['role']}) 使用模型: {civilian_model_config.get('model')}")
                else:
                    model = GameModel()
                    print(f"  玩家{player['player_id']} ({player['role']}) 使用模型: 默认模型 (未提供平民模型配置)")
        else:
            # 所有玩家使用相同模型（使用 default_model_config 如果提供）
            if default_model_config and default_model_config.get('model'):
                model = GameModel(**default_model_config)
                print(f"  玩家{player['player_id']} ({player['role']}) 使用模型: {default_model_config.get('model')}")
            else:
                model = GameModel()
                print(f"  玩家{player['player_id']} ({player['role']}) 使用模型: 默认模型")
        models.append(model)
    
    print(f"✅ 已创建 {len(models)} 个模型实例")
    
    # 创建Agent实例并保存到state中（持久化，让Agent有记忆）
    agents_map = {}
    
    for i, player in enumerate(players):
        # 为每个Agent分配对应的模型实例
        agent = PlayerAgent(
            player_id=player["player_id"],
            name=player["name"],
            word=player["word"],  # Agent只知道自己的词汇，不知道自己是平民还是卧底
            model=models[i]  # 分配模型实例
        )
        agents_map[player["player_id"]] = agent
    
    # 初始化每个agent的player_analyses（为所有其他玩家创建初始分析条目）
    print("📊 初始化玩家分析...")
    for player in players:
        agent = agents_map[player["player_id"]]
        initial_analyses = {}
        
        # Create initial analysis for all other players (status is unknown)
        for other_player in players:
            if other_player["player_id"] != player["player_id"]:
                player_id_str = str(other_player["player_id"])
                initial_analyses[player_id_str] = {
                    "word_guess": "unknown",
                    "word_reason": "The game just started, not enough information to make a judgment yet",
                    "role_guess": "unknown",
                    "role_reason": "The game just started, not enough information to make a judgment yet"
                }
        
        # 添加初始分析条目（round=0表示游戏开始前的初始状态）
        if initial_analyses:
            agent.memory["player_analyses"].append({
                "round": 0,
                "phase": "initial",
                "analyses": initial_analyses
            })
    
    print(f"✅ 已初始化 {len(players)} 个玩家的分析")
    
    return {
        **state,
        "game_id": game_id,  # 明确包含game_id，确保传递到后续状态
        "output_dir": state.get("output_dir", "game_results"),  # 保留output_dir
        "round": 1,
        "phase": "description",
        "players": players,
        "num_players": num_players,
        "num_undercover": num_undercover,
        "current_descriptions": [],
        "current_votes": [],
        "eliminated_players": [],
        "elimination_history": [],
        "winner": None,
        "game_over": False,
        "agents_map": agents_map,  # 保存Agent实例
        "word_pair": word_pair,  # 保存词汇对信息
        # 显式保留模型配置字段
        "fixed_model_undercover": fixed_model_undercover,
        "undercover_model_config": undercover_model_config,
        "civilian_model_config": civilian_model_config,
        "default_model_config": default_model_config,
        "conversation_history": [
            {
                "type": "system",
                "content": f"游戏开始！平民词：{word_pair['civilian']}, 卧底词：{word_pair['undercover']}"
            }
        ]
    }


def description_phase(state: GameState) -> GameState:
    """描述阶段节点 - 每个agent轮流向所有其他agent说话"""
    print(f"\n💬 第 {state['round']} 轮 - 描述阶段（每个玩家轮流向所有人说话）")
    
    players = state["players"]
    current_descriptions = []
    conversation_history = []
    
    # 使用持久化的Agent实例（从state中获取）
    agents_map = state.get("agents_map", {})

    # 首先确定所有存活玩家的发言顺序
    alive_players_list = [p for p in players if p["alive"]]
    player_speaking_order = {}  # {player_id: speaking_order}
    for idx, p in enumerate(alive_players_list, start=1):
        player_speaking_order[p["player_id"]] = idx
    
    speaking_order = 0
    for player in players:
        if not player["alive"]:
            continue
        
        speaking_order += 1
        agent = agents_map[player["player_id"]]
        
        # 获取 output_dir 和 game_id 用于保存 prompt
        output_dir = state.get("output_dir", "game_results")
        game_id = state.get("game_id", "unknown")
        
        # 生成描述：Agent从记忆中读取历史描述和当前轮次已说过的描述（排除自己），避免重复
        description = agent.generate_description(
            state["round"],
            output_dir=output_dir,  # 传递 output_dir 用于保存 prompt
            game_id=game_id  # 传递 game_id 用于保存 prompt
        )
        
        description_entry = {
            "round": state["round"],  # 添加round字段，用于区分历史描述和当前描述
            "player_id": player["player_id"],
            "description": description,
            "name": player["name"],  # 添加name，用于记忆
        }
        
        current_descriptions.append(description_entry)
        
        # 更新玩家的描述历史
        player["description_history"].append(description)
        
        conversation_history.append({
            "type": "description",
            "round": state["round"],
            "player_id": player["player_id"],
            "content": description
        })
        
        print(f"  {player['name']} 对所有人说: {description}")
        
        # 实时更新所有Agent的记忆，让后续说话的agent能看到前面已说过的描述
        for p in players:
            if not p["alive"]:
                continue
            agents_map[p["player_id"]].add_to_memory(state["round"], descriptions=[description_entry])
        
        # 实时身份审视：让所有其他agent重新审视自己的身份（并发执行）
        reflection_players = [p for p in players if p["alive"] and p["player_id"] != player["player_id"]]
        
        if reflection_players:
            # 获取历史描述（所有之前轮次的描述）
            history_descriptions = []
            if players and agents_map:
                # 使用第一个存活玩家的agent来获取历史描述（所有agent的记忆中历史描述应该是一样的）
                first_alive_player = next((p for p in players if p["alive"]), None)
                if first_alive_player:
                    agent = agents_map[first_alive_player["player_id"]]
                    # 从agent的记忆中获取历史描述
                    for desc in agent.memory.get("all_descriptions", []):
                        if desc.get("round", 0) < state["round"]:
                            history_descriptions.append(desc)
            
            # 定义身份反思函数，用于并发执行
            def process_reflection(reflection_player):
                """处理单个玩家的身份反思（用于并发执行）"""
                if not reflection_player["alive"]:
                    return None
                
                other_agent = agents_map[reflection_player["player_id"]]
                # 获取这个agent的实际发言顺序
                other_speaking_order = player_speaking_order.get(reflection_player["player_id"], 999)
                
                # 合并历史描述和当前描述
                all_descriptions = history_descriptions + current_descriptions
                
                # 获取 output_dir 和 game_id 用于保存 prompt
                output_dir = state.get("output_dir", "game_results")
                game_id = state.get("game_id", "unknown")
                speaker_id = player["player_id"]  # 触发这次 reflection 的发言者ID
                
                # 进行身份审视（静默进行，不打印，结果保存在记忆中）
                reflection_result = other_agent.reflect_on_identity(
                    state["round"],
                    other_speaking_order,
                    all_descriptions,  # 传入所有描述（历史+当前，包括刚发言的玩家）
                    output_dir=output_dir,  # 传递 output_dir 用于保存 prompt
                    game_id=game_id,  # 传递 game_id 用于保存 prompt
                    speaker_id=speaker_id  # 传递触发这次 reflection 的发言者ID
                )     
                # 保存 reflection_result 到文件（已取消输出重定向）
                # if reflection_result and output_dir and game_id:
                #     try:
                #         result_dir = os.path.join(output_dir, "identity_reflection_results")
                #         os.makedirs(result_dir, exist_ok=True)
                #         
                #         # 文件名格式：round_{round_num}_player_{player_id}_after_{speaker_id}_result.json
                #         if speaker_id:
                #             filename = f"round_{state['round']}_player_{reflection_player['player_id']}_after_{speaker_id}_result.json"
                #         else:
                #             filename = f"round_{state['round']}_player_{reflection_player['player_id']}_result.json"
                #         
                #         filepath = os.path.join(result_dir, filename)
                #         
                #         # 构建完整的保存数据（包含元数据和结果）
                #         result_data = {
                #             "game_id": game_id,
                #             "round": state["round"],
                #             "reflection_player_id": reflection_player["player_id"],
                #             "reflection_player_name": reflection_player["name"],
                #             "reflection_player_word": reflection_player.get("word", ""),
                #             "reflection_player_speaking_order": other_speaking_order,
                #             "triggered_after_speaker_id": speaker_id,
                #             "reflection_result": reflection_result
                #         }
                #         
                #         # 写入 JSON 文件
                #         with open(filepath, "w", encoding="utf-8") as f:
                #             json.dump(result_data, f, ensure_ascii=False, indent=2)
                #         
                #         print(f"    💾 已保存 identity reflection result 到: {filepath}")
                #     except Exception as e:
                #         print(f"    ⚠️  保存 identity reflection result 失败: {e}")
                
                return {
                    "player": reflection_player,
                    "reflection_result": reflection_result
                }
            
            # 使用线程池并发执行身份反思
            REFLECTION_TIMEOUT = 120.0  # 身份反思超时时间（秒）
            with ThreadPoolExecutor(max_workers=len(reflection_players)) as executor:
                # 提交所有身份反思任务
                future_to_player = {
                    executor.submit(process_reflection, p): p 
                    for p in reflection_players
                }
                
                # 收集结果（按完成顺序），设置超时
                reflection_results = []
                for future in as_completed(future_to_player, timeout=REFLECTION_TIMEOUT):
                    try:
                        result = future.result(timeout=REFLECTION_TIMEOUT)
                        if result:
                            reflection_results.append(result)
                    except Exception as e:
                        # 如果某个任务超时或失败，记录错误但继续处理其他任务
                        print(f"    ⚠️  身份反思任务超时或失败: {e}")
                        continue
            
            # 可选：打印身份审视结果（用于调试）
            for result in reflection_results:
                p = result["player"]
                reflection_result = result["reflection_result"]
                if reflection_result:
                    print(f"    💭 {p['name']} 重新审视身份: {reflection_result.get('role_guess', 'unknown')} (信心: {reflection_result.get('confidence', 'medium')})")
    
    return {
        **state,
        "game_id": state.get("game_id"),  # 明确保留game_id
        "output_dir": state.get("output_dir", "game_results"),  # 明确保留output_dir
        "phase": "voting",
        "current_descriptions": current_descriptions,
        "agents_map": agents_map,  # 保存更新后的Agent实例
        "conversation_history": conversation_history
    }


def voting_phase(state: GameState) -> GameState:
    """投票阶段节点 - 如果有平票，没有人出局，直接进入下一轮"""
    print(f"\n🗳️  第 {state['round']} 轮 - 投票阶段")
    
    players = state["players"]
    descriptions = state["current_descriptions"]
    alive_player_ids = [p["player_id"] for p in players if p["alive"]]
    
    # 使用持久化的Agent实例（从state中获取）
    agents_map = state.get("agents_map", {})
    
    # 如果agents_map为空，重新创建（使用默认模型配置）
    if not agents_map:
        for player in players:
            if not player["alive"]:
                continue
            # 创建默认模型实例
            model = GameModel()
            agent = PlayerAgent(
                player_id=player["player_id"],
                name=player["name"],
                word=player["word"],
                model=model
            )
            agents_map[player["player_id"]] = agent
    
    # 获取 output_dir 和 game_id 用于保存 prompt
    output_dir = state.get("output_dir", "game_results")
    game_id = state.get("game_id", "unknown")
    
    # 定义投票函数，用于并发执行
    def process_vote(player, current_descriptions_list):
        """处理单个玩家的投票（用于并发执行）"""
        if not player["alive"]:
            return None
        
        agent = agents_map[player["player_id"]]
        alive_ids = [p["player_id"] for p in players if p["alive"]]
        
        # 获取投票结果（包含reason和vote_number）
        voting_result = agent.vote(
            alive_ids, 
            current_descriptions_list, 
            state["round"],
            is_tie_break=False,
            tie_players=None,
            output_dir=output_dir,  # 传递 output_dir 用于保存 prompt
            game_id=game_id  # 传递 game_id 用于保存 prompt
        )
        
        # 提取投票目标（vote_number就是玩家ID）
        target_id = voting_result.get("vote_number", 0)
        target_reason = voting_result.get("reason", "No reason")
        
        # 验证target_id有效
        valid_targets = [pid for pid in alive_ids if pid != player["player_id"]]
        
        if target_id not in valid_targets or target_id == player["player_id"]:
            # 如果无效，随机选择一个
            if valid_targets:
                target_id = random.choice(valid_targets)
                target_reason = "Failed to parse response, random vote"
            else:
                target_id = alive_ids[0] if alive_ids else player["player_id"]
                target_reason = "Default vote"
        
        return {
            "player": player,
            "agent": agent,
            "voting_result": voting_result,
            "target_id": target_id,
            "target_reason": target_reason
        }
    
    # 重置投票计数
    for player in players:
        player["votes_received"] = 0
    
    current_votes = []
    alive_players_list = [p for p in players if p["alive"]]
    current_descriptions_list = descriptions.copy()
    conversation_history = []
    
    print(f"  🚀 并发执行 {len(alive_players_list)} 个玩家的投票...")
    
    # 使用线程池并发执行投票
    VOTING_TIMEOUT = 120.0  # 投票超时时间（秒）
    with ThreadPoolExecutor(max_workers=len(alive_players_list)) as executor:
        # 提交所有投票任务
        future_to_player = {
            executor.submit(process_vote, player, current_descriptions_list): player 
            for player in alive_players_list
        }
        
        # 收集结果（按完成顺序），设置超时
        vote_results = []
        for future in as_completed(future_to_player, timeout=VOTING_TIMEOUT):
            try:
                result = future.result(timeout=VOTING_TIMEOUT)
                if result:
                    vote_results.append(result)
            except Exception as e:
                # 如果某个任务超时或失败，记录错误但继续处理其他任务
                print(f"    ⚠️  投票任务超时或失败: {e}")
                continue
    
    # 处理投票结果
    for result in vote_results:
        player = result["player"]
        agent = result["agent"]
        voting_result = result["voting_result"]
        target_id = result["target_id"]
        target_reason = result["target_reason"]
        
        current_votes.append({
            "voter_id": player["player_id"],
            "target_id": target_id,
            "voting_result": voting_result  # 保存reason和vote_number
        })
        
        # 更新被投票者的计数
        target_player = None
        for p in players:
            if p["player_id"] == target_id:
                p["votes_received"] += 1
                target_player = p
                break
        
        # 更新Agent的投票记忆
        # 1. 记录自己投给了谁（包含完整的reason，不包含thinking）
        vote_record = {
            "target_id": target_id,
            "target_name": target_player["name"] if target_player else f"Player {target_id}",
            "vote_number": target_id,
            "reason": target_reason
        }
        # 2. 记录完整分析数据（player_analyses和self_analysis包含所有信息，无需单独存储identity_guesses等）
        player_analyses = voting_result.get("player_analyses")
        self_analysis = voting_result.get("self_analysis")
        # 3. 记录投票阶段的思考过程
        voting_thinking = voting_result.get("thinking", "")
        agent.add_to_memory(
            state["round"], 
            vote_record=vote_record,
            player_analyses=player_analyses,  # 对每个其他玩家的完整分析（包含word_guess和role_guess）
            self_analysis=self_analysis,  # 对自己的完整分析（包含civilian_word_guess和role_guess）
            voting_thinking=voting_thinking  # 投票阶段的思考过程
        )
        
        conversation_history.append({
            "type": "vote",
            "round": state["round"],
            "voter_id": player["player_id"],
            "target_id": target_id,
            "voting_result": voting_result
        })
    
    # 准备所有人的投票记录（用于更新所有Agent的记忆）
    all_votes_list = []
    for vote in current_votes:
        voter_player = next((p for p in players if p["player_id"] == vote["voter_id"]), None)
        target_player = next((p for p in players if p["player_id"] == vote["target_id"]), None)
        all_votes_list.append({
            "voter_id": vote["voter_id"],
            "target_id": vote["target_id"],
            "voter_name": voter_player["name"] if voter_player else f"Player {vote['voter_id']}",
            "target_name": target_player["name"] if target_player else f"Player {vote['target_id']}"
        })
    
    # 更新所有Agent的记忆，添加所有人的投票记录
    for player in players:
        if not player["alive"]:
            continue
        agent = agents_map[player["player_id"]]
        agent.add_to_memory(state["round"], all_votes=all_votes_list)
    
    # 找出得票最多的玩家（用于确定被淘汰的玩家）
    max_votes = max(p["votes_received"] for p in players if p["alive"])
    candidates = [p for p in players if p["alive"] and p["votes_received"] == max_votes]
    
    # 检查是否有平票（多个玩家得票相同且都是最高票）
    if len(candidates) > 1:
        # 有平票，没有人出局，直接进入下一轮
        tie_players_ids = [c["player_id"] for c in candidates]
        print(f"\n⚠️  平票！玩家{tie_players_ids} 都获得了 {max_votes} 票")
        print(f"  ➡️  没有人出局，直接进入下一轮...")
        
        return {
            **state,
            "game_id": state.get("game_id"),  # 明确保留game_id
            "output_dir": state.get("output_dir", "game_results"),  # 明确保留output_dir
            "phase": "check",
            "current_votes": current_votes,
            "current_descriptions": current_descriptions_list,
            "agents_map": agents_map,  # 保存Agent实例
            "conversation_history": conversation_history
        }
    else:
        # 没有平票，确定淘汰玩家
        eliminated = candidates[0]
        eliminated["alive"] = False
        
        print(f"\n❌ 玩家{eliminated['player_id']} ({eliminated['role']}) 被淘汰！")
        
        elimination_history = state.get("elimination_history", [])
        elimination_history.append({
            "round": state["round"],
            "player_id": eliminated["player_id"],
            "role": eliminated["role"],
            "votes": eliminated["votes_received"]
        })
        
        eliminated_players = state.get("eliminated_players", [])
        eliminated_players.append(eliminated["player_id"])
        
        return {
            **state,
            "game_id": state.get("game_id"),  # 明确保留game_id
            "output_dir": state.get("output_dir", "game_results"),  # 明确保留output_dir
            "phase": "check",
            "current_votes": current_votes,
            "current_descriptions": current_descriptions_list,
            "eliminated_players": eliminated_players,
            "elimination_history": elimination_history,
            "agents_map": agents_map,  # 保存Agent实例
            "conversation_history": conversation_history
        }


def check_win_condition(state: GameState) -> GameState:
    """检查胜利条件节点"""
    print(f"\n🎯 检查胜利条件...")
    
    # 不再保存txt格式的记忆文件，所有信息已保存在JSON格式中
    # save_agent_memories(state)  # 已禁用
    
    players = state["players"]
    
    alive_civilians = sum(1 for p in players if p["alive"] and p["role"] == "civilian")
    alive_undercover = sum(1 for p in players if p["alive"] and p["role"] == "undercover")
    
    print(f"  存活平民: {alive_civilians}, 存活卧底: {alive_undercover}")
    
    game_over = False
    winner = None
    
    if alive_undercover == 0:
        # 所有卧底被淘汰，平民胜利
        game_over = True
        winner = "civilian"
        print(f"🎉 平民胜利！游戏在第 {state['round']} 轮结束")
    elif alive_undercover >= alive_civilians:
        # 卧底数量 >= 平民数量，卧底胜利
        game_over = True
        winner = "undercover"
        print(f"🎉 卧底胜利！游戏在第 {state['round']} 轮结束")
    else:
        # 游戏继续，进行投票后的身份反思
        print("➡️  游戏继续，进入投票后身份反思阶段...")
        
        # 投票后的身份反思：让所有存活玩家基于投票行为重新审视身份
        agents_map = state.get("agents_map", {})
        current_votes = state.get("current_votes", [])
        output_dir = state.get("output_dir", "game_results")
        game_id = state.get("game_id", "unknown")
        
        # 确定被淘汰的玩家（从上一轮的投票结果中获取）
        eliminated_player = None
        elimination_history = state.get("elimination_history", [])
        if elimination_history:
            last_elimination = elimination_history[-1]
            if last_elimination.get("round") == state["round"]:
                eliminated_player = {
                    "player_id": last_elimination.get("player_id"),
                    "name": f"Player {last_elimination.get('player_id')}",
                    "role": last_elimination.get("role")
                }
        
        alive_players_for_reflection = [p for p in players if p["alive"]]
        
        # 定义投票后身份反思函数，用于并发执行
        def process_voting_reflection(reflection_player):
            """处理单个玩家的投票后身份反思（用于并发执行）"""
            if not reflection_player["alive"]:
                return None
            
            other_agent = agents_map[reflection_player["player_id"]]
            
            # 准备投票结果列表（包含 voter_name 和 target_name）
            votes_for_reflection = []
            for vote in current_votes:
                voter_player = next((p for p in players if p["player_id"] == vote["voter_id"]), None)
                target_player = next((p for p in players if p["player_id"] == vote["target_id"]), None)
                votes_for_reflection.append({
                    "voter_id": vote["voter_id"],
                    "target_id": vote["target_id"],
                    "voter_name": voter_player["name"] if voter_player else f"Player {vote['voter_id']}",
                    "target_name": target_player["name"] if target_player else f"Player {vote['target_id']}"
                })
            
            # 进行投票后的身份审视
            reflection_result = other_agent.reflect_on_identity_after_voting(
                state["round"],
                votes_for_reflection,
                eliminated_player=eliminated_player,
                output_dir=output_dir,
                game_id=game_id
            )
            
            return {
                "player": reflection_player,
                "reflection_result": reflection_result
            }
        
        # 使用线程池并发执行投票后身份反思
        if alive_players_for_reflection and agents_map:
            REFLECTION_TIMEOUT = 120.0  # 身份反思超时时间（秒）
            with ThreadPoolExecutor(max_workers=len(alive_players_for_reflection)) as executor:
                # 提交所有投票后身份反思任务
                future_to_player = {
                    executor.submit(process_voting_reflection, p): p 
                    for p in alive_players_for_reflection
                }
                
                # 收集结果（按完成顺序），设置超时
                voting_reflection_results = []
                for future in as_completed(future_to_player, timeout=REFLECTION_TIMEOUT):
                    try:
                        result = future.result(timeout=REFLECTION_TIMEOUT)
                        if result:
                            voting_reflection_results.append(result)
                    except Exception as e:
                        # 如果某个任务超时或失败，记录错误但继续处理其他任务
                        print(f"    ⚠️  投票后身份反思任务超时或失败: {e}")
                        continue
                
                # 可选：打印投票后身份审视结果（用于调试）
                for result in voting_reflection_results:
                    p = result["player"]
                    reflection_result = result["reflection_result"]
                    if reflection_result:
                        print(f"    💭 {p['name']} 投票后重新审视身份: {reflection_result.get('self_analysis', {}).get('role_guess', 'unknown')} (信心: {reflection_result.get('self_analysis', {}).get('confidence', 'medium')})")
        
        # 更新 agents_map（确保反思后的记忆被保存）
        state["agents_map"] = agents_map
    
    return {
        **state,
        "game_id": state.get("game_id"),  # 明确保留game_id
        "output_dir": state.get("output_dir", "game_results"),  # 明确保留output_dir
        "phase": "end" if game_over else "description",
        "round": state["round"] + (0 if game_over else 1),
        "game_over": game_over,
        "winner": winner,
        "agents_map": state.get("agents_map", {}),  # 明确保留agents_map，确保记忆不丢失
        "conversation_history": [{
            "type": "check",
            "round": state["round"],
            "alive_civilians": alive_civilians,
            "alive_undercover": alive_undercover,
            "game_over": game_over,
            "winner": winner
        }]
    }


def save_game_results_json(state: GameState, output_dir: str = None):
    """保存游戏结果到JSON文件
    
    多局游戏时，所有游戏信息追加到同一个文件中，通过game_id区分：
    1. game_info.json - 所有游戏的基本信息（字典格式，key为game_id）
    2. agent_player_{player_id}_memory.json - 每个Agent的所有游戏记忆（字典格式，key为game_id）
    """
    game_id = state.get("game_id")
    if not game_id:
        # 如果game_id不存在，生成一个并打印警告
        game_id = str(uuid.uuid4())
        print(f"⚠️  警告: state中未找到game_id，已生成新的game_id: {game_id}")
    else:
        print(f"✅ 使用game_id: {game_id}")
    
    # 从state中获取output_dir，如果没有则使用默认值
    if output_dir is None:
        output_dir = state.get("output_dir", "game_results")
    
    print(f"🔍 调试: save_game_results_json 使用的 output_dir = {output_dir}")
    
    agents_map = state.get("agents_map", {})
    players = state.get("players", [])
    word_pair = state.get("word_pair", {})
    final_round = state.get("round", 0)
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 输出目录: {os.path.abspath(output_dir)}")
    
    # 1. 保存游戏信息（追加到game_info.json）
    # 构建玩家信息，包含模型信息
    players_info = []
    for p in players:
        player_id = p.get("player_id")
        player_info = {
            "player_id": player_id,
            "name": p.get("name"),
            "role": p.get("role"),
            "word": p.get("word"),
            "alive": p.get("alive")
        }
        
        # 添加模型信息
        agent = agents_map.get(player_id)
        if agent and hasattr(agent, 'model') and agent.model:
            model = agent.model
            player_info["model"] = {
                "model_name": getattr(model, 'model_name', 'unknown'),
                "base_url": getattr(model, 'base_url', 'unknown'),
                "temperature": getattr(model, 'temperature', None)
            }
        else:
            player_info["model"] = None
        
        players_info.append(player_info)
    
    game_info = {
        "game_id": game_id,
        "civilian_word": word_pair.get("civilian", ""),
        "undercover_word": word_pair.get("undercover", ""),
        "num_players": state.get("num_players", 0),
        "num_undercover": state.get("num_undercover", 0),
        "final_round": final_round,  # 游戏结束的轮数
        "winner": state.get("winner"),
        "players": players_info,  # 包含所有玩家的完整信息（包括role、word、model等），可根据role字段筛选
        "elimination_history": state.get("elimination_history", [])
    }
    
    game_info_file = os.path.join(output_dir, "game_info.json")
    # 读取现有数据（如果存在）
    all_games_info = {}
    if os.path.exists(game_info_file):
        try:
            with open(game_info_file, "r", encoding="utf-8") as f:
                all_games_info = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            all_games_info = {}
    
    # 添加当前游戏信息
    all_games_info[game_id] = game_info
    
    # 写入文件并立即刷新到磁盘
    with open(game_info_file, "w", encoding="utf-8") as f:
        json.dump(all_games_info, f, ensure_ascii=False, indent=2)
        f.flush()  # 立即刷新到磁盘
        os.fsync(f.fileno())  # 强制同步到磁盘
    print(f"💾 游戏信息已保存到: {game_info_file} (game_id: {game_id})")
    
    # 2. 保存每个Agent的完整记忆（追加到对应的player文件中）
    for player in players:
        player_id = player.get("player_id")
        agent = agents_map.get(player_id)
        
        if agent is None:
            continue
        
        agent_memory = {
            "game_id": game_id,
            "player_id": player_id,
            "name": player.get("name"),
            "role": player.get("role"),
            "word": player.get("word"),
            "alive": player.get("alive"),
            "memory": {
                "all_descriptions": agent.memory.get("all_descriptions", []),
                "description_thinking_history": agent.memory.get("description_thinking_history", []),  # 每轮描述前的思考和描述
                "voting_history": agent.memory.get("voting_history", []),
                "voting_thinking_history": agent.memory.get("voting_thinking_history", []),  # 投票阶段的思考过程
                "all_votes_history": agent.memory.get("all_votes_history", []),
                "player_analyses": agent.memory.get("player_analyses", []),  # 对每个其他玩家的完整分析（包含word_guess和role_guess）
                "self_analyses": agent.memory.get("self_analyses", [])  # 对自己的完整分析（包含civilian_word_guess和role_guess）
            }
        }
        
        agent_memory_file = os.path.join(output_dir, f"agent_player_{player_id}_memory.json")
        # 读取现有数据（如果存在）
        all_games_memory = {}
        if os.path.exists(agent_memory_file):
            try:
                with open(agent_memory_file, "r", encoding="utf-8") as f:
                    all_games_memory = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                all_games_memory = {}
        
        # 添加当前游戏的记忆
        all_games_memory[game_id] = agent_memory
        
        # 写入文件并立即刷新到磁盘
        with open(agent_memory_file, "w", encoding="utf-8") as f:
            json.dump(all_games_memory, f, ensure_ascii=False, indent=2)
            f.flush()  # 立即刷新到磁盘
            os.fsync(f.fileno())  # 强制同步到磁盘
        print(f"💾 Agent {player_id} 记忆已保存到: {agent_memory_file} (game_id: {game_id})")


def end_game(state: GameState) -> GameState:
    """游戏结束节点"""
    print(f"\n" + "="*50)
    print("🏁 游戏结束")
    print("="*50)
    
    # 游戏结束的轮数就是当前轮数（因为游戏在check_win_condition时结束，round没有增加）
    final_round = state['round']
    
    print(f"\n🏆 获胜方: {'平民' if state['winner'] == 'civilian' else '卧底'}")
    print(f"📊 游戏结束轮数: 第 {final_round} 轮")
    
    print(f"\n👥 玩家信息:")
    for player in state["players"]:
        status = "✅ 存活" if player["alive"] else "❌ 淘汰"
        role_icon = "🕵️" if player["role"] == "undercover" else "👤"
        print(f"  {role_icon} {player['name']} ({player['role']}) - {player['word']} - {status}")
    
    print(f"\n📜 淘汰历史:")
    for elim in state["elimination_history"]:
        print(f"  第{elim['round']}轮: 玩家{elim['player_id']} ({elim['role']}) 被淘汰")
    
    # 保存JSON格式的游戏结果
    print(f"\n💾 保存游戏结果到JSON文件...")
    print(f"🔍 调试: end_game 节点中的 game_id = {state.get('game_id', 'NOT FOUND')}")
    print(f"🔍 调试: end_game 节点中的 output_dir = {state.get('output_dir', 'NOT FOUND')}")
    save_game_results_json(state)
    
    return {
        **state,
        "game_id": state.get("game_id"),  # 明确保留game_id
        "output_dir": state.get("output_dir", "game_results"),  # 明确保留output_dir
        "conversation_history": [{
            "type": "end",
            "winner": state["winner"],
            "final_round": state["round"]
        }]
    }