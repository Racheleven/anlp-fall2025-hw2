# run_batch_games.py
"""
批量运行游戏脚本
运行多局游戏并记录游戏过程
"""

import os
import json
import uuid
from dotenv import load_dotenv
from graph.workflow import run_game
from graph.nodes import set_word_pairs
from data import load_word_pairs


def load_config(config_file: str = None) -> dict:
    """加载配置文件
    
    Args:
        config_file: 配置文件路径，如果为None则尝试加载 config.json
        
    Returns:
        dict: 配置字典，如果文件不存在则返回空字典
    """
    if config_file is None:
        # 默认尝试加载项目根目录下的 config.json
        config_file = os.path.join(os.path.dirname(__file__), "config.json")
    
    if not os.path.exists(config_file):
        return {}
    
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        # 将 JSON 中的 null 转换为 Python 的 None
        def convert_none(obj):
            if isinstance(obj, dict):
                return {k: convert_none(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_none(item) for item in obj]
            elif obj is None:
                return None
            else:
                return obj
        config = convert_none(config)
        print(f"✅ 已加载配置文件: {config_file}")
        return config
    except Exception as e:
        print(f"⚠️  警告: 加载配置文件失败: {e}")
        return {}


def run_batch_games(num_games: int = 10, num_players: int = 6, num_undercover: int = 1, 
                    exp_name: str = "default", difficulty: str = "default", data_file: str = None,
                    fixed_model_undercover: bool = False, undercover_model: str = None, 
                    civilian_model: str = None, config_file: str = None, random_seed: int = None):
    """批量运行游戏并记录结果
    
    所有游戏结果会自动保存到 results/{exp_name}_result/ 目录下：
    - game_info.json: 所有游戏的基本信息
    - agent_player_{player_id}_memory.json: 每个玩家的完整记忆
    
    Args:
        num_games: 要运行的局数
        num_players: 每局游戏的玩家数量
        num_undercover: 每局游戏的卧底数量
        exp_name: 实验名称，用于创建输出目录
        difficulty: 词汇对难度 ("easy", "medium", "hard", "all", "default")，默认使用内置词汇对
        data_file: 指定数据文件路径（相对于 data 目录），如果指定则优先使用此文件
        fixed_model_undercover: 是否根据身份固定分配模型（默认: False，会被配置文件覆盖）
        undercover_model: 卧底使用的模型名称（会被配置文件覆盖）
        civilian_model: 平民使用的模型名称（会被配置文件覆盖）
        config_file: 配置文件路径，如果指定则从配置文件加载模型配置
        random_seed: 随机种子（整数），如果提供则设置 random.seed() 以确保实验结果可重复
    """
    # 加载环境变量
    load_dotenv()
    
    # 加载配置文件（如果提供）
    config = {}
    if config_file:
        config = load_config(config_file)
    elif os.path.exists(os.path.join(os.path.dirname(__file__), "config.json")):
        # 如果存在默认配置文件，也加载它
        config = load_config()
    
    # 处理随机种子配置
    import random
    random_seeds = None
    if config and "random_seeds" in config:
        # 从配置文件读取随机种子列表
        random_seeds = config["random_seeds"]
        if not isinstance(random_seeds, list):
            print(f"⚠️  警告: config中的random_seeds必须是列表，已忽略")
            random_seeds = None
        elif len(random_seeds) != num_games:
            print(f"⚠️  警告: config中的random_seeds长度({len(random_seeds)})与游戏局数({num_games})不匹配，已忽略")
            random_seeds = None
        else:
            print(f"🎲 从配置文件加载了 {len(random_seeds)} 个随机种子")
    elif random_seed is not None:
        # 如果命令行提供了单个随机种子，生成一个列表（从random_seed开始递增）
        random_seeds = [random_seed + i for i in range(num_games)]
        print(f"🎲 基于命令行参数生成 {len(random_seeds)} 个随机种子: {random_seeds[0]} 到 {random_seeds[-1]}")
    
    # 从配置文件读取模型配置（如果存在）
    if config:
        if "fixed_model_undercover" in config:
            fixed_model_undercover = config["fixed_model_undercover"]
        
        # 构建模型配置字典
        if fixed_model_undercover:
            if "undercover_model" in config:
                undercover_model_config = config["undercover_model"].copy()
            else:
                undercover_model_config = {}
            
            if "civilian_model" in config:
                civilian_model_config = config["civilian_model"].copy()
            else:
                civilian_model_config = {}
        else:
            # 如果 fixed_model_undercover 为 False，使用 default_model
            if "default_model" in config:
                default_model_config = config["default_model"].copy()
            else:
                default_model_config = {}
            undercover_model_config = {}
            civilian_model_config = {}
    else:
        # 没有配置文件，使用命令行参数（向后兼容）
        undercover_model_config = {}
        civilian_model_config = {}
        default_model_config = {}
        
        if fixed_model_undercover:
            if undercover_model:
                undercover_model_config = {"model": undercover_model}
            if civilian_model:
                civilian_model_config = {"model": civilian_model}
    
    # 加载词汇对数据
    if data_file:
        # 从指定文件加载
        data_dir = os.path.join(os.path.dirname(__file__), "data")
        filepath = os.path.join(data_dir, data_file)
        if not os.path.exists(filepath):
            print(f"❌ 错误: 数据文件不存在: {filepath}")
            return
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            # 转换格式
            word_pairs = []
            for pair in data:
                if isinstance(pair, list) and len(pair) >= 2:
                    word_pairs.append({
                        "civilian": pair[0],
                        "undercover": pair[1]
                    })
            print(f"✅ 从 {data_file} 加载了 {len(word_pairs)} 个词汇对")
        except Exception as e:
            print(f"❌ 加载数据文件失败: {e}")
            return
    else:
        # 从 data 目录按难度加载
        word_pairs = load_word_pairs(difficulty=difficulty)
        if not word_pairs:
            print(f"⚠️  警告: 未加载到词汇对，使用默认词汇对")
            word_pairs = load_word_pairs(difficulty="default")
    
    # 选择词汇对
    # 如果提供了随机种子列表，在选择词汇对前先设置第一个随机种子
    if random_seeds is not None and len(random_seeds) > 0:
        random.seed(random_seeds[0])
        print(f"🎲 选择词汇对时使用随机种子: {random_seeds[0]}")
    
    if data_file:
        # 如果指定了 data-file，按顺序读取（可以循环使用）
        selected_word_pairs = []
        for i in range(num_games):
            # 使用模运算实现循环读取
            selected_word_pairs.append(word_pairs[i % len(word_pairs)])
        if num_games <= len(word_pairs):
            print(f"📝 从 {len(word_pairs)} 个词汇对中按顺序选择了前 {num_games} 个词汇对")
        else:
            print(f"📝 从 {len(word_pairs)} 个词汇对中按顺序循环选择了 {num_games} 个词汇对（会重复使用）")
    else:
        # 如果没有指定 data-file，使用随机抽取（保持原有逻辑）
        if len(word_pairs) >= num_games:
            # 随机抽取不重复的词汇对
            selected_word_pairs = random.sample(word_pairs, num_games)
            print(f"📝 从 {len(word_pairs)} 个词汇对中随机抽取了 {num_games} 个不重复的词汇对")
        else:
            # 如果词汇对数量不足，允许重复使用
            selected_word_pairs = [random.choice(word_pairs) for _ in range(num_games)]
            print(f"📝 词汇对数量({len(word_pairs)})少于游戏局数({num_games})，将允许重复使用")
    
    # 创建实验输出目录
    output_dir = f"results/{exp_name}_result"
    os.makedirs(output_dir, exist_ok=True)
    
    # 存储所有游戏的结果（仅用于统计，不保存到文件）
    all_results = []
    
    print("="*70)
    print(f"🎮 批量运行游戏")
    print("="*70)
    print(f"📊 配置:")
    print(f"  - 实验名称: {exp_name}")
    print(f"  - 游戏局数: {num_games}")
    print(f"  - 每局玩家数: {num_players}")
    print(f"  - 每局卧底数: {num_undercover}")
    print(f"  - 可用词汇对数量: {len(word_pairs)}")
    print(f"  - 已选择词汇对数量: {len(selected_word_pairs)}")
    if data_file:
        print(f"  - 数据文件: {data_file}")
    else:
        print(f"  - 难度级别: {difficulty}")
    if random_seeds:
        print(f"  - 随机种子: {random_seeds}")
    elif random_seed is not None:
        print(f"  - 随机种子: {random_seed} (将生成 {num_games} 个种子)")
    if fixed_model_undercover:
        print(f"  - 模型分配: 根据身份分配")
        if undercover_model_config:
            print(f"    - 卧底模型: {undercover_model_config.get('model', '默认模型')}")
        if civilian_model_config:
            print(f"    - 平民模型: {civilian_model_config.get('model', '默认模型')}")
    else:
        print(f"  - 模型分配: 所有玩家使用相同模型")
        if default_model_config:
            print(f"    - 模型: {default_model_config.get('model', '默认模型')}")
            if default_model_config.get('api_key'):
                print(f"      API Key: {default_model_config['api_key'][:20]}...")
            if default_model_config.get('base_url'):
                print(f"      Base URL: {default_model_config['base_url']}")
    print(f"  - 游戏结果保存到: {output_dir}/ 目录")
    print("="*70 + "\n")
    
    # 运行多局游戏
    for game_num in range(1, num_games + 1):
        print(f"\n{'='*70}")
        print(f"🎯 第 {game_num}/{num_games} 局游戏")
        print(f"{'='*70}\n")
        
        try:
            # 为这局游戏设置随机种子（如果提供了随机种子列表）
            if random_seeds is not None:
                seed = random_seeds[game_num - 1]
                random.seed(seed)
                print(f"🎲 第 {game_num} 局游戏使用随机种子: {seed}")
            
            # game_id 使用简单的数字，从 1 到 num_games
            game_id = str(game_num)
            print(f"🆔 游戏ID: {game_id}\n")
            
            # 为这局游戏设置特定的词汇对
            selected_word_pair = selected_word_pairs[game_num - 1]
            # 临时设置全局词汇对为只包含这一个词汇对的列表
            set_word_pairs([selected_word_pair])
            
            # 运行游戏，传递 output_dir 和 game_id
            # 如果 fixed_model_undercover 为 False，使用 default_model_config
            if fixed_model_undercover:
                # 确保配置字典存在且包含 model 字段
                uc_config = undercover_model_config if (undercover_model_config and undercover_model_config.get('model')) else None
                civ_config = civilian_model_config if (civilian_model_config and civilian_model_config.get('model')) else None
                print(f"🔍 调试: 卧底模型配置 = {uc_config}")
                print(f"🔍 调试: 平民模型配置 = {civ_config}")
                result = run_game(
                    num_players=num_players, 
                    num_undercover=num_undercover, 
                    game_id=game_id,
                    output_dir=output_dir,
                    fixed_model_undercover=True,
                    undercover_model_config=uc_config,
                    civilian_model_config=civ_config
                )
            else:
                # 使用默认模型配置
                result = run_game(
                    num_players=num_players, 
                    num_undercover=num_undercover, 
                    game_id=game_id,
                    output_dir=output_dir,
                    fixed_model_undercover=False,
                    undercover_model_config=None,
                    civilian_model_config=None,
                    default_model_config=default_model_config if default_model_config else None
                )
            
            # 提取游戏结果
            game_result = {
                "game_number": game_num,
                "winner": result.get("winner"),
                "final_round": result.get("round"),
                "num_players": result.get("num_players"),
                "num_undercover": result.get("num_undercover"),
                "elimination_history": result.get("elimination_history", []),
                "players": [
                    {
                        "player_id": p.get("player_id"),
                        "name": p.get("name"),
                        "role": p.get("role"),
                        "word": p.get("word"),
                        "alive": p.get("alive")
                    }
                    for p in result.get("players", [])
                ],
                "conversation_history": result.get("conversation_history", [])
            }
            
            all_results.append(game_result)
            
            # 确保结果已保存（游戏结果已在 end_game 节点中保存，这里只是确认）
            # 由于 save_game_results_json 在 end_game 中已经调用，数据应该已经写入
            # 但为了确保数据安全，我们可以强制刷新文件系统缓存
            import sys
            sys.stdout.flush()  # 刷新标准输出
            
            print(f"\n✅ 第 {game_num} 局游戏完成")
            print(f"   💾 游戏结果已保存到: {output_dir}/")
            print(f"   📊 获胜方: {'平民' if result.get('winner') == 'civilian' else '卧底'}")
            print(f"   🎯 游戏ID: {game_id}")

        except Exception as e:
            print(f"\n❌ 第 {game_num} 局游戏出错: {e}")
            import traceback
            traceback.print_exc()
            continue
    

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="批量运行谁是卧底游戏")
    parser.add_argument("--num-games", type=int, default=10, help="要运行的局数 (默认: 10)")
    parser.add_argument("--num-players", type=int, default=6, help="每局游戏的玩家数量 (默认: 6)")
    parser.add_argument("--num-undercover", type=int, default=1, help="每局游戏的卧底数量 (默认: 1)")
    parser.add_argument("--exp", type=str, required=True, help="实验名称 (必需，例如: exp1)")
    parser.add_argument("--difficulty", type=str, default="default", 
                       choices=["easy", "medium", "hard", "all", "default"],
                       help="词汇对难度级别 (默认: default，使用内置词汇对)")
    parser.add_argument("--data-file", type=str, default=None,
                       help="指定数据文件名（相对于 data 目录），例如: easy_keyword_pair.json")
    parser.add_argument("--fixed-model-undercover", action="store_true",
                       help="根据身份固定分配模型（卧底和平民使用不同模型）")
    parser.add_argument("--undercover-model", type=str, default=None,
                       help="卧底使用的模型名称（例如: Qwen/Qwen2.5-7B-Instruct）")
    parser.add_argument("--civilian-model", type=str, default=None,
                       help="平民使用的模型名称（例如: Qwen/Qwen2.5-32B-Instruct）")
    parser.add_argument("--config", type=str, default=None,
                       help="配置文件路径（JSON格式），如果指定则从配置文件加载模型配置")
    parser.add_argument("--random-seed", type=int, default=42,
                       help="随机种子（用于确保实验结果可重复），例如: 42")
    
    args = parser.parse_args()
    
    run_batch_games(
        num_games=args.num_games,
        num_players=args.num_players,
        num_undercover=args.num_undercover,
        exp_name=args.exp,
        difficulty=args.difficulty,
        data_file=args.data_file,
        fixed_model_undercover=args.fixed_model_undercover,
        undercover_model=args.undercover_model,
        civilian_model=args.civilian_model,
        config_file=args.config,
        random_seed=args.random_seed
    )

