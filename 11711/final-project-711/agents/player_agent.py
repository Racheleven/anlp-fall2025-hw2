# agents/player_agent.py
from typing import List, Dict, Optional
from langchain_core.messages import HumanMessage
from .model import GameModel
import json_repair
import json
import os

from prompts import (
    get_description_user_prompt,
    get_voting_user_prompt
)
from prompts.identity_reflection_prompts import get_identity_reflection_prompt, get_identity_reflection_after_voting_prompt


class PlayerAgent:
    """玩家智能体 - 不知道自己是平民还是卧底，需要通过描述推测"""
    def _normalize_player_id(self, key):
        """把各种形式的玩家 ID（例如 'player_1' / '1'）转换为整数 1"""
        if isinstance(key, int):
            return key
        if isinstance(key, str):
            cleaned = (
                key.lower()
                .replace("player_", "")
                .replace("player ", "")
                .replace("玩家", "")
                .strip()
            )
            return int(cleaned)
        raise ValueError(f"无法解析 player_id: {key}")
    def __init__(self, player_id: int, name: str, word: str, model: Optional[GameModel] = None):
        """初始化玩家智能体
        
        Args:
            player_id: 玩家ID
            name: 玩家名称
            word: 玩家的词汇
            model: GameModel实例，如果为None则使用默认配置创建
        """
        self.player_id = player_id
        self.name = name
        self.word = word  # 玩家只知道自己的词汇，不知道自己是平民还是卧底
        
        # 如果提供了model实例，使用它的LLM；否则创建默认的GameModel
        if model is not None:
            self.model = model
            self.llm = model.get_llm()
        else:
            # 默认配置（向后兼容）
            self.model = GameModel()
            self.llm = self.model.get_llm()
        
        # 记忆系统：存储所有历史对话、投票记录和推理过程
        self.memory = {
            "all_descriptions": [],  # 存储所有轮次中所有玩家的描述
            # 格式: [{"round": 1, "player_id": 1, "description": "...", "name": "玩家1"}, ...]
            "description_thinking_history": [],  # 存储每轮描述前的思考和描述
            # 格式: [{"round": 1, "thinking": "在给出最终描述前的思考", "description": "描述内容"}, ...]
            "voting_history": [],  # 存储自己的投票历史（投给了谁，包含完整的reason）
            # 格式: [{"round": 1, "target_id": 2, "target_name": "玩家2", "vote_number": 1, "reason": "..."}, ...]
            "voting_thinking_history": [],  # 存储投票阶段的思考过程
            # 格式: [{"round": 1, "thinking": "在做出最终投票决策前的思考过程..."}, ...]
            "all_votes_history": [],  # 存储所有人的投票记录
            # 格式: [{"round": 1, "votes": [{"voter_id": 1, "target_id": 2, "voter_name": "玩家1", "target_name": "玩家2"}, ...]}, ...]
            "player_analyses": [],  # 存储每轮对每个其他玩家的完整分析（包含word_guess, role_guess等）
            # 格式: [{"round": 1, "analyses": {"1": {"word_guess": "...", "word_reason": "...", "role_guess": "...", "role_reason": "..."}, ...}}, ...]
            "self_analyses": [],  # 存储每轮对自己的完整分析（新格式）
            # 格式: [{"round": 1, "analysis": {"role_guess": "...", "role_reason": "..."}}, ...]
        }
    
    def add_to_memory(self, round_num: int, descriptions: List[dict] = None, 
                     vote_record: dict = None, all_votes: List[dict] = None,
                     player_analyses: Dict[int, dict] = None, self_analysis: dict = None,
                     voting_thinking: str = None):
        """将本轮所有玩家的描述、投票记录和所有投票添加到记忆中
        
        Args:
            round_num: 轮次编号
            descriptions: 描述列表，格式: [{"player_id": 1, "description": "...", "name": "玩家1"}, ...]
            vote_record: 自己的投票记录，格式: {"target_id": 2, "target_name": "玩家2", "vote_number": 1, "reason": "..."}
            all_votes: 所有人的投票记录，格式: [{"voter_id": 1, "target_id": 2, "voter_name": "玩家1", "target_name": "玩家2"}, ...]
            player_analyses: 对每个其他玩家的完整分析，格式: {"1": {"word_guess": "...", "word_reason": "...", "role_guess": "...", "role_reason": "..."}, ...}
            self_analysis: 对自己的完整分析，格式: {"role_guess": "...", "role_reason": "..."}
            voting_thinking: 投票阶段的思考过程（字符串）
        """
        if descriptions:
            for desc in descriptions:
                memory_entry = {
                    "round": round_num,
                    "player_id": desc["player_id"],
                    "description": desc["description"],
                    "name": desc.get("name", f"玩家{desc['player_id']}")
                }
                self.memory["all_descriptions"].append(memory_entry)
        
        if vote_record:
            voting_entry = {
                "round": round_num,
                "target_id": vote_record["target_id"],
                "target_name": vote_record.get("target_name", f"玩家{vote_record['target_id']}"),
                "vote_number": vote_record.get("vote_number", 1),
                "reason": vote_record.get("reason", "无理由")
            }
            self.memory["voting_history"].append(voting_entry)
        
        if all_votes:
            votes_entry = {
                "round": round_num,
                "votes": all_votes  # [{"voter_id": int, "target_id": int, "voter_name": str, "target_name": str}, ...]
            }
            self.memory["all_votes_history"].append(votes_entry)
        
        if player_analyses is not None:
            # 查找当前轮是否已有条目
            existing_entry = None
            for entry in self.memory["player_analyses"]:
                if entry.get("round") == round_num:
                    existing_entry = entry
                    break
            if existing_entry:
                # 如果存在当前轮的条目，按玩家ID更新分析（相同key则更新value）
                existing_analyses = existing_entry.get("analyses", {})
                # 更新或添加每个玩家的分析
                for player_id, analysis in player_analyses.items():
                    existing_analyses[player_id] = analysis
                existing_entry["analyses"] = existing_analyses
            else:
                # 如果不存在当前轮的条目，创建新条目
                analyses_entry = {
                    "round": round_num,
                    "analyses": player_analyses.copy()  # {player_id: {"word_guess": str, "word_reason": str, "role_guess": str, "role_reason": str}, ...}
                }
                self.memory["player_analyses"].append(analyses_entry)
        
        if self_analysis is not None:
            # 先移除当前轮的所有旧条目（防止重复）
            self.memory["self_analyses"] = [
                a for a in self.memory["self_analyses"] 
                if a.get("round") != round_num
            ]
            # 添加新分析
            self_analysis_entry = {
                "round": round_num,
                "analysis": self_analysis  # {"role_guess": str, "role_reason": str}
            }
            self.memory["self_analyses"].append(self_analysis_entry)
        
        if voting_thinking is not None:
            # 先移除当前轮的所有旧条目（防止重复）
            self.memory["voting_thinking_history"] = [
                t for t in self.memory["voting_thinking_history"] 
                if t.get("round") != round_num
            ]
            # 添加新的思考记录
            thinking_entry = {
                "round": round_num,
                "thinking": voting_thinking
            }
            self.memory["voting_thinking_history"].append(thinking_entry)
        
    def generate_description(self, round_num: int, output_dir: str = None, game_id: str = None) -> str:
        """生成对词汇的描述 - 玩家不知道自己的身份，需要通过其他人的描述推测
        
        Args:
            round_num: 当前轮次
            output_dir: 输出目录，用于保存 prompt（可选）
            game_id: 游戏ID，用于保存 prompt（可选）
        
        Returns:
            str: 描述文本（从JSON响应中提取）
        """
        # 从记忆中获取所有历史（排除当前轮）
        all_history = [h for h in self.memory["all_descriptions"] 
                      if h["round"] < round_num]
        history_text = self._format_history_from_memory(all_history)
        
        # 从记忆中获取当前轮次已经说过的描述（排除自己）
        current_round_descriptions = [
            h for h in self.memory["all_descriptions"] 
            if h["round"] == round_num and h["player_id"] != self.player_id
        ]
        
        # 格式化当前轮次已说过的描述
        current_descriptions_text = ""
        if current_round_descriptions:
            lines = []
            for desc in current_round_descriptions:
                name = desc.get("name", f"玩家{desc['player_id']}")
                lines.append(f"  {name}: {desc['description']}")
            current_descriptions_text = "\n".join(lines)
        
        # 获取身份猜测（从记忆中）
        # 在描述阶段开始时，应该显示上一轮的分析（因为当前轮次还没有进行分析）
        # 如果当前轮次已经有分析，则显示当前轮次的分析；否则显示最近一轮的分析
        # 传入 None 让方法自动推断所有玩家，确保包含所有玩家（除了自己）
        current_self_guess_text = self._format_current_self_analysis_from_memory(round_num)
        current_player_guesses_text = self._format_current_player_analyses_from_memory(round_num, None)
        
        user_prompt = get_description_user_prompt(
            self.word, history_text, current_descriptions_text,
            self.player_id, round_num, current_self_guess_text, current_player_guesses_text
        )

        #保存 prompt 到文件（已取消输出重定向）
        # if output_dir and game_id:
        #     try:
        #         prompt_dir = os.path.join(output_dir, "description_prompts")
        #         os.makedirs(prompt_dir, exist_ok=True)
                
        #         # 文件名格式：round_{round_num}_player_{player_id}_description.txt
        #         filename = f"round_{round_num}_player_{self.player_id}_description.txt"
        #         filepath = os.path.join(prompt_dir, filename)
                
        #         # 写入 prompt 内容，包含元数据
        #         with open(filepath, "w", encoding="utf-8") as f:
        #             f.write(f"# Description Prompt\n")
        #             f.write(f"# Game ID: {game_id}\n")
        #             f.write(f"# Round: {round_num}\n")
        #             f.write(f"# Player ID: {self.player_id}\n")
        #             f.write(f"# Player Name: {self.name}\n")
        #             f.write(f"# Player Word: {self.word}\n")
        #             f.write(f"# ==========================================\n\n")
        #             f.write(user_prompt)
                
        #         print(f"    💾 已保存 description prompt 到: {filepath}")
        #     except Exception as e:
        #         print(f"    ⚠️  保存 description prompt 失败: {e}")

        messages = [
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
        except Exception as e:
            # 如果LLM调用超时或失败，返回默认描述
            print(f"    ⚠️  玩家{self.player_id} 描述生成失败: {e}")
            default_description = f"This is a description related to {self.word}."
            # 即使失败，也记录到memory中
            self.memory["description_thinking_history"] = [
                entry for entry in self.memory["description_thinking_history"]
                if entry.get("round") != round_num
            ]
            self.memory["description_thinking_history"].append({
                "round": round_num,
                "thinking": f"LLM调用失败: {e}",
                "description": default_description
            })
            return default_description
        
        # 解析JSON响应，提取"thinking"和"word_description"字段
        thinking = ""
        description = ""
        
        try:
            # 尝试直接解析
            data = json.loads(response_text)
            thinking = data.get("thinking", "")
            description = data.get("word_description", data.get("描述", response_text))  # 支持新旧字段名
            description = description.strip() if description else response_text.strip()
        except json.JSONDecodeError:
            # 如果失败，尝试修复JSON
            try:
                repaired_json = json_repair.repair_json(response_text)
                data = json.loads(repaired_json)
                thinking = data.get("thinking", "")
                description = data.get("word_description", data.get("描述", response_text))  # 支持新旧字段名
                description = description.strip() if description else response_text.strip()
            except Exception:
                # 如果都失败，返回原始响应
                description = response_text.strip()
        
        # 保存思考和描述到记忆中
        # 先移除当前轮的所有旧条目（防止重复）
        self.memory["description_thinking_history"] = [
            entry for entry in self.memory["description_thinking_history"]
            if entry.get("round") != round_num
        ]
        # 添加新条目
        self.memory["description_thinking_history"].append({
            "round": round_num,
            "thinking": thinking,
            "description": description
        })
        
        return description
    
    def reflect_on_identity(self, round_num: int, speaking_order: int, 
                           all_descriptions: List[dict], 
                           output_dir: str = None, game_id: str = None, 
                           speaker_id: int = None) -> Optional[dict]:
        """在描述阶段重新审视自己的身份（每个agent在每个其他agent发言后都会调用）
        
        Args:
            round_num: 当前轮次
            speaking_order: 当前玩家的发言顺序（1=第一个，2=第二个，3=第三个...）
            all_descriptions: 所有描述列表（历史+当前，包括刚发言的玩家）
            output_dir: 输出目录，用于保存 prompt（可选）
            game_id: 游戏ID，用于保存 prompt（可选）
            speaker_id: 触发这次 reflection 的发言者ID（可选）
        
        Returns:
            dict: {"role_guess": "civilian"/"undercover"/"unknown", "role_reason": "...", "confidence": "high"/"medium"/"low"}
            如果解析失败或没有前面玩家的描述，返回None
        """
        # 如果没有描述，无法进行身份审视
        if not all_descriptions or len(all_descriptions) == 0:
            return None
        
        # 分离历史描述和当前轮描述
        history_descriptions = [d for d in all_descriptions if d.get("round", round_num) < round_num]
        current_descriptions = [d for d in all_descriptions if d.get("round", round_num) == round_num]
        
        # 如果没有当前轮的描述，无法进行身份审视
        if not current_descriptions or len(current_descriptions) == 0:
            return None
        
        # 格式化历史描述（包含投票和淘汰信息）
        history_text = self._format_history_with_votes_and_eliminations(history_descriptions, round_num)
        
        # Format descriptions already spoken in current round
        current_desc_text = "\n".join([
            f"Player {d['player_id']}: {d['description']}"
            for d in current_descriptions
        ])
        
        if not current_desc_text:
            return None
        
        # 获取当前轮次的旧 self_analysis（如果存在），用于基于旧判断更新
        previous_self_analysis = None
        for analysis in self.memory["self_analyses"]:
            if analysis.get("round") == round_num:
                previous_self_analysis = analysis.get("analysis")
                break
        
        # 获取身份猜测（格式化后的文本，用于显示在 prompt 中）
        # 在身份反思时，应该基于上一轮或当前轮已有的分析进行更新
        # 如果当前轮次已经有分析，显示当前轮次的分析；否则显示最近一轮的分析
        current_self_guess_text = self._format_current_self_analysis_from_memory(round_num)
        
        # 获取对其他玩家的分析
        # 传入 None 让方法自动推断所有玩家，确保包含所有玩家（除了自己）
        current_player_guesses_text = self._format_current_player_analyses_from_memory(round_num, None)
        
        # 生成身份审视的 prompt（包含之前的判断和当前的身份猜测，如果有的话）
        reflection_prompt = get_identity_reflection_prompt(
            self.word, history_text, current_desc_text, 
            round_num, self.player_id, speaking_order,
            previous_self_analysis=previous_self_analysis,
            current_self_guess_text=current_self_guess_text,
            current_player_guesses_text=current_player_guesses_text
        )
        
        # 保存 prompt 到文件（已取消输出重定向）
        # if output_dir and game_id:
        #     try:
        #         prompt_dir = os.path.join(output_dir, "identity_reflection_prompts")
        #         os.makedirs(prompt_dir, exist_ok=True)
        #         
        #         # 文件名格式：round_{round_num}_player_{player_id}_after_{speaker_id}.txt
        #         if speaker_id:
        #             filename = f"round_{round_num}_player_{self.player_id}_after_{speaker_id}.txt"
        #         else:
        #             filename = f"round_{round_num}_player_{self.player_id}.txt"
        #         
        #         filepath = os.path.join(prompt_dir, filename)
        #         
        #         # 写入 prompt 内容，包含元数据
        #         with open(filepath, "w", encoding="utf-8") as f:
        #             f.write(f"# Identity Reflection Prompt\n")
        #             f.write(f"# Game ID: {game_id}\n")
        #             f.write(f"# Round: {round_num}\n")
        #             f.write(f"# Reflection Player ID: {self.player_id}\n")
        #             f.write(f"# Reflection Player Name: {self.name}\n")
        #             f.write(f"# Reflection Player Word: {self.word}\n")
        #             f.write(f"# Reflection Player Speaking Order: {speaking_order}\n")
        #             if speaker_id:
        #                 f.write(f"# Triggered After Speaker ID: {speaker_id}\n")
        #             f.write(f"# ==========================================\n\n")
        #             f.write(reflection_prompt)
        #         
        #         print(f"    💾 已保存 identity reflection prompt 到: {filepath}")
        #     except Exception as e:
        #         print(f"    ⚠️  保存 identity reflection prompt 失败: {e}")
        
        messages = [
            HumanMessage(content=reflection_prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)

            response_text = response.content.strip()
        except Exception as e:
            # 如果LLM调用超时或失败，返回None（不影响游戏流程）
            print(f"    ⚠️  玩家{self.player_id} 身份反思失败: {e}")
            return None
        
        # 解析JSON响应
        try:
            # 尝试直接解析
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # 如果失败，尝试修复JSON
            try:
                repaired_json = json_repair.repair_json(response_text)
                result = json.loads(repaired_json)
            except Exception:
                # 如果都失败，返回None
                return None
        
        # 验证结果格式（新格式包含 player_analyses 和 self_analysis）
        try:
            if "self_analysis" in result:
                self_analysis_data = result.get("self_analysis", {})
                # player_analyses_data = result.get("player_analyses", {})
                player_analyses_data_raw = result.get("player_analyses", {})
                player_analyses_data = {}

                for key, val in player_analyses_data_raw.items():
                    try:
                        clean_id = self._normalize_player_id(key)
                        player_analyses_data[str(clean_id)] = val
                    except Exception:
                        pass
                # 保存自己的分析到记忆中
                self_analysis = {
                    "role_guess": self_analysis_data.get("role_guess", "unknown"),
                    "role_reason": self_analysis_data.get("role_reason", ""),
                    "confidence": self_analysis_data.get("confidence", "medium"),
                    "speaking_order": speaking_order,
                    "phase": "description_reflection"
                }
                
                # 更新记忆中的self_analyses（如果当前轮还没有，则添加；如果有，则更新）
                # 先移除当前轮的所有旧条目（防止重复）
                self.memory["self_analyses"] = [
                    a for a in self.memory["self_analyses"] 
                    if a.get("round") != round_num
                ]
                # 添加新分析
                self.memory["self_analyses"].append({
                    "round": round_num,
                    "analysis": self_analysis
                })
                
                # 保存对其他玩家的分析到记忆中
                if player_analyses_data:
                    # 更新记忆中的player_analyses（按玩家ID更新，区分阶段）
                    # 先找到当前轮、当前阶段的所有现有分析
                    phase = "description_reflection"
                    existing_analyses_dict = {}
                    for analysis in self.memory["player_analyses"]:
                        if analysis.get("round") == round_num and analysis.get("phase") == phase:
                            # 合并所有现有分析
                            existing_analyses_dict.update(analysis.get("analyses", {}))
                    
                    # 移除当前轮、当前阶段的所有旧条目（防止重复）
                    self.memory["player_analyses"] = [
                        a for a in self.memory["player_analyses"] 
                        if not (a.get("round") == round_num and a.get("phase") == phase)
                    ]
                    
                    # 合并旧数据和新数据（按玩家ID更新）
                    if existing_analyses_dict:
                        existing_analyses_dict.update(player_analyses_data)
                        final_analyses = existing_analyses_dict
                    else:
                        final_analyses = player_analyses_data
                    
                    # 确保被淘汰的玩家被标记为 "eliminated"
                    eliminated_players = self._get_eliminated_players_from_memory(round_num + 1)  # +1 因为要包含当前轮次
                    for eliminated_id in eliminated_players:
                        eliminated_id_str = str(eliminated_id)
                        if eliminated_id_str in final_analyses:
                            final_analyses[eliminated_id_str]["role_guess"] = "eliminated"
                    
                    # 添加分析（包含phase字段，区分阶段）
                    self.memory["player_analyses"].append({
                        "round": round_num,
                        "phase": phase,
                        "analyses": final_analyses
                    })
                
                return result
            else:
                return None
        except Exception as e:
            # 如果解析失败，返回None（不影响游戏流程）
            print(f"    ⚠️  玩家{self.player_id} 身份反思结果解析失败: {e}")
            return None
    
    def reflect_on_identity_after_voting(self, round_num: int, 
                                        current_votes: List[dict],
                                        eliminated_player: dict = None,
                                        output_dir: str = None, 
                                        game_id: str = None) -> Optional[dict]:
        """在投票阶段结束后重新审视自己的身份（基于投票行为）
        
        Args:
            round_num: 当前轮次
            current_votes: 当前轮投票结果列表，格式: [{"voter_id": int, "target_id": int, "voter_name": str, "target_name": str}, ...]
            eliminated_player: 被淘汰的玩家信息（如果有），格式: {"player_id": int, "name": str, "role": str}
            output_dir: 输出目录，用于保存 prompt（可选）
            game_id: 游戏ID，用于保存 prompt（可选）
        
        Returns:
            dict: {"role_guess": "civilian"/"undercover"/"unknown", "role_reason": "...", "confidence": "high"/"medium"/"low"}
            如果解析失败，返回None
        """
        # 从记忆中获取历史描述
        history_descriptions = [h for h in self.memory["all_descriptions"] if h["round"] < round_num]
        # 使用包含投票和淘汰信息的历史格式化方法
        history_text = self._format_history_with_votes_and_eliminations(history_descriptions, round_num)
        
        # Format current round voting results
        current_votes_text = "Voting results this round:\n"
        for vote in current_votes:
            voter_name = vote.get("voter_name", f"Player {vote['voter_id']}")
            target_name = vote.get("target_name", f"Player {vote['target_id']}")
            current_votes_text += f"  {voter_name} voted for {target_name}\n"
        
        # Format eliminated player information
        eliminated_player_info = ""
        if eliminated_player:
            player_id = eliminated_player['player_id']
            player_name = eliminated_player.get('name', f'Player {player_id}')
            eliminated_player_info = f"Player {player_id} ({player_name}) was eliminated."
            if eliminated_player.get("role"):
                role_en = "civilian" if eliminated_player["role"] == "civilian" else "undercover"
                eliminated_player_info += f" The eliminated player is a {role_en}."
        
        # 获取身份猜测（格式化后的文本）
        # 在投票后身份反思时，应该基于当前轮次已有的分析（描述阶段和投票阶段的）进行更新
        # 如果当前轮次还没有分析，则显示最近一轮的分析
        current_self_guess_text = self._format_current_self_analysis_from_memory(round_num)
        
        # 获取对其他存活玩家的分析
        # 从 memory 中推断所有玩家，然后排除已淘汰的玩家，确保包含所有存活玩家
        all_players = self._get_all_players_from_memory()
        
        # 排除已淘汰的玩家
        eliminated_player_id = eliminated_player.get("player_id") if eliminated_player else None
        alive_player_ids = [pid for pid in all_players if pid != eliminated_player_id]
        
        # 如果从 memory 中无法推断出所有玩家，则使用投票中的玩家作为备选
        if not alive_player_ids:
            alive_player_ids = list(set([v["voter_id"] for v in current_votes] + [v["target_id"] for v in current_votes]))
            if eliminated_player:
                alive_player_ids = [pid for pid in alive_player_ids if pid != eliminated_player["player_id"]]
            alive_player_ids = [pid for pid in alive_player_ids if pid != self.player_id]
        
        # 传入存活玩家列表，确保所有存活玩家都被包含（即使没有分析，也显示为"未知"）
        current_player_guesses_text = self._format_current_player_analyses_from_memory(round_num, alive_player_ids if alive_player_ids else None)
        
        # 生成投票后的身份审视 prompt
        reflection_prompt = get_identity_reflection_after_voting_prompt(
            self.word, history_text, round_num, self.player_id,
            current_votes_text, eliminated_player_info,
            current_self_guess_text, current_player_guesses_text
        )
        
        # 保存 prompt 到文件（已取消输出重定向）
        # if output_dir and game_id:
        #     try:
        #         prompt_dir = os.path.join(output_dir, "identity_reflection_prompts")
        #         os.makedirs(prompt_dir, exist_ok=True)
        #         
        #         # 文件名格式：round_{round_num}_player_{player_id}_after_voting.txt
        #         filename = f"round_{round_num}_player_{self.player_id}_after_voting.txt"
        #         filepath = os.path.join(prompt_dir, filename)
        #         
        #         # 写入 prompt 内容，包含元数据
        #         with open(filepath, "w", encoding="utf-8") as f:
        #             f.write(f"# Identity Reflection After Voting Prompt\n")
        #             f.write(f"# Game ID: {game_id}\n")
        #             f.write(f"# Round: {round_num}\n")
        #             f.write(f"# Reflection Player ID: {self.player_id}\n")
        #             f.write(f"# Reflection Player Name: {self.name}\n")
        #             f.write(f"# Reflection Player Word: {self.word}\n")
        #             if eliminated_player:
        #                 elim_player_id = eliminated_player['player_id']
        #                 elim_player_name = eliminated_player.get('name', f'玩家{elim_player_id}')
        #                 elim_player_role = eliminated_player.get('role', 'unknown')
        #                 f.write(f"# Eliminated Player: {elim_player_name} ({elim_player_role})\n")
        #             f.write(f"# ==========================================\n\n")
        #             f.write(reflection_prompt)
        #         
        #         print(f"    💾 已保存 identity reflection after voting prompt 到: {filepath}")
        #     except Exception as e:
        #         print(f"    ⚠️  保存 identity reflection after voting prompt 失败: {e}")
        
        messages = [
            HumanMessage(content=reflection_prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
        except Exception as e:
            # 如果LLM调用超时或失败，返回None（不影响游戏流程）
            print(f"    ⚠️  玩家{self.player_id} 投票后身份反思失败: {e}")
            return None
        
        # 解析JSON响应
        try:
            # 尝试直接解析
            result = json.loads(response_text)
        except json.JSONDecodeError:
            # 如果失败，尝试修复JSON
            try:
                repaired_json = json_repair.repair_json(response_text)
                result = json.loads(repaired_json)
            except Exception:
                # 如果都失败，返回None
                return None
        
        # 验证结果格式（新格式包含 player_analyses 和 self_analysis）
        try:
            if "self_analysis" in result:
                self_analysis_data = result.get("self_analysis", {})
                player_analyses_data_raw = result.get("player_analyses", {})
                player_analyses_data = {}

                for key, val in player_analyses_data_raw.items():
                    try:
                        clean_id = self._normalize_player_id(key)
                        player_analyses_data[str(clean_id)] = val
                    except Exception:
                        pass
                
                # 保存自己的分析到记忆中
                self_analysis = {
                    "role_guess": self_analysis_data.get("role_guess", "unknown"),
                    "role_reason": self_analysis_data.get("role_reason", ""),
                    "confidence": self_analysis_data.get("confidence", "medium"),
                    "phase": "voting_reflection"
                }
                
                # 更新记忆中的self_analyses（如果当前轮还没有，则添加；如果有，则更新）
                # 先移除当前轮的所有旧条目（防止重复）
                self.memory["self_analyses"] = [
                    a for a in self.memory["self_analyses"] 
                    if not (a.get("round") == round_num and a.get("analysis", {}).get("phase") == "voting_reflection")
                ]
                # 添加新分析
                self.memory["self_analyses"].append({
                    "round": round_num,
                    "analysis": self_analysis
                })
                
                # 保存对其他玩家的分析到记忆中
                if player_analyses_data:
                    # 更新记忆中的player_analyses（按玩家ID更新，区分阶段）
                    # 先找到当前轮、当前阶段的所有现有分析
                    phase = "voting_reflection"
                    existing_analyses_dict = {}
                    for analysis in self.memory["player_analyses"]:
                        if analysis.get("round") == round_num and analysis.get("phase") == phase:
                            # 合并所有现有分析
                            existing_analyses_dict.update(analysis.get("analyses", {}))
                    
                    # 移除当前轮、当前阶段的所有旧条目（防止重复）
                    self.memory["player_analyses"] = [
                        a for a in self.memory["player_analyses"] 
                        if not (a.get("round") == round_num and a.get("phase") == phase)
                    ]
                    
                    # 合并旧数据和新数据（按玩家ID更新）
                    if existing_analyses_dict:
                        existing_analyses_dict.update(player_analyses_data)
                        final_analyses = existing_analyses_dict
                    else:
                        final_analyses = player_analyses_data
                    
                    # 确保被淘汰的玩家被标记为 "eliminated"
                    # 包括当前轮次被淘汰的玩家
                    eliminated_players = self._get_eliminated_players_from_memory(round_num + 1)  # +1 因为要包含当前轮次
                    if eliminated_player:
                        eliminated_id = eliminated_player.get("player_id")
                        if eliminated_id:
                            eliminated_players.append(eliminated_id)
                    
                    for eliminated_id in eliminated_players:
                        eliminated_id_str = str(eliminated_id)
                        if eliminated_id_str in final_analyses:
                            final_analyses[eliminated_id_str]["role_guess"] = "eliminated"
                    
                    # 添加分析（包含phase字段，区分阶段）
                    self.memory["player_analyses"].append({
                        "round": round_num,
                        "phase": phase,
                        "analyses": final_analyses
                    })
                
                return result
            else:
                return None
        except Exception as e:
            # 如果解析失败，返回None（不影响游戏流程）
            print(f"    ⚠️  玩家{self.player_id} 投票后身份反思结果解析失败: {e}")
            return None
    
    def vote(self, alive_players: List[int], 
             descriptions: List[dict], round_num: int,
             is_tie_break: bool = False, tie_players: List[int] = None,
             output_dir: str = None, game_id: str = None) -> dict:
        """投票阶段 - 输出一个详细的分析理由和投票目标
        
        Args:
            alive_players: 存活玩家列表
            descriptions: 当前轮描述列表
            round_num: 当前轮次
            is_tie_break: 是否是平票重投阶段（默认False）
            tie_players: 如果是平票重投，平票玩家列表（可选）
            output_dir: 输出目录，用于保存 prompt（可选）
            game_id: 游戏ID，用于保存 prompt（可选）
        
        Returns:
            dict: {"reason": str, "vote_number": int}
            reason 包含对所有其他玩家的详细分析过程
            vote_number 表示要投票给哪个玩家（玩家ID）
        """
        # 从记忆中获取历史
        history_descriptions = [h for h in self.memory["all_descriptions"] if h["round"] < round_num]
        
        # 格式化历史描述（包含投票和淘汰信息）
        history_text = self._format_history_with_votes_and_eliminations(history_descriptions, round_num)
        
        # 格式化投票历史（自己的投票记录）
        voting_history_text = self._format_voting_history_from_memory()
        
        # 格式化所有投票历史（所有人的投票记录）
        all_votes_history_text = self._format_all_votes_history_from_memory()
        
        # 格式化上一轮的分析（从player_analyses和self_analyses中提取）
        previous_guesses_text = self._format_previous_analyses_from_memory()
        
        # 格式化当前轮次的分析（描述阶段的推理结果）
        current_self_guess_text = self._format_current_self_analysis_from_memory(round_num)
        current_player_guesses_text = self._format_current_player_analyses_from_memory(round_num, alive_players)
        
        # 格式化当前轮描述
        current_desc_text = "\n".join([
            f"Player {d['player_id']}: {d['description']}"
            for d in descriptions
        ])
        
        user_prompt = get_voting_user_prompt(
            self.word, history_text, current_desc_text, 
            alive_players, round_num, self.player_id, voting_history_text,
            "", all_votes_history_text, previous_guesses_text,
            "", "", is_tie_break, tie_players,
            current_self_guess_text, current_player_guesses_text
        )
        
        # 保存 prompt 到文件（已取消输出重定向）
        # if output_dir and game_id:
        #     try:
        #         prompt_dir = os.path.join(output_dir, "voting_prompts")
        #         os.makedirs(prompt_dir, exist_ok=True)
        #         
        #         # 文件名格式：round_{round_num}_player_{player_id}_vote.txt
        #         # 如果是平票重投，添加 _tiebreak 后缀
        #         if is_tie_break:
        #             filename = f"round_{round_num}_player_{self.player_id}_vote_tiebreak.txt"
        #         else:
        #             filename = f"round_{round_num}_player_{self.player_id}_vote.txt"
        #         filepath = os.path.join(prompt_dir, filename)
        #         
        #         # 写入 prompt 内容，包含元数据
        #         with open(filepath, "w", encoding="utf-8") as f:
        #             f.write(f"# Voting Prompt\n")
        #             f.write(f"# Game ID: {game_id}\n")
        #             f.write(f"# Round: {round_num}\n")
        #             f.write(f"# Player ID: {self.player_id}\n")
        #             f.write(f"# Player Name: {self.name}\n")
        #             f.write(f"# Player Word: {self.word}\n")
        #             f.write(f"# Is Tie Break: {is_tie_break}\n")
        #             if is_tie_break and tie_players:
        #                 f.write(f"# Tie Players: {tie_players}\n")
        #             f.write(f"# Alive Players: {alive_players}\n")
        #             f.write(f"# ==========================================\n\n")
        #             f.write(user_prompt)
        #         
        #         print(f"    💾 已保存 voting prompt 到: {filepath}")
        #     except Exception as e:
        #         print(f"    ⚠️  保存 voting prompt 失败: {e}")
        
        messages = [
            HumanMessage(content=user_prompt)
        ]
        
        try:
            response = self.llm.invoke(messages)
            response_text = response.content.strip()
        except Exception as e:
            # 如果LLM调用超时或失败，返回默认投票（投票给第一个存活玩家）
            print(f"    ⚠️  玩家{self.player_id} 投票生成失败: {e}")
            valid_players = [pid for pid in alive_players if pid != self.player_id]
            if valid_players:
                default_vote_number = valid_players[0]
            else:
                default_vote_number = alive_players[0] if alive_players else 1
            
            # 从记忆中获取描述阶段的推理结果
            player_analyses = {}
            self_analysis = {}
            
            if self.memory.get("self_analyses"):
                for analysis in self.memory["self_analyses"]:
                    if analysis.get("round") == round_num:
                        if analysis.get("analysis"):
                            self_analysis = analysis["analysis"]
                        break
            
            if self.memory.get("player_analyses"):
                # 优先查找描述阶段的分析，如果没有则查找投票阶段的分析
                # 兼容旧的没有phase字段的条目
                for analysis in self.memory["player_analyses"]:
                    if analysis.get("round") == round_num:
                        phase = analysis.get("phase")
                        # 优先使用描述阶段的分析
                        if phase == "description_reflection" or phase is None:
                            if analysis.get("analyses"):
                                player_analyses.update(analysis.get("analyses", {}))
            
            return {
                "reason": "LLM调用失败，使用默认投票",
                "vote_number": default_vote_number,
                "thinking": "",
                "player_analyses": player_analyses,
                "self_analysis": self_analysis
            }
        
        # 解析响应，提取reason和vote_number
        # 如果是平票重投，只能投票给平票玩家
        valid_targets = tie_players if (is_tie_break and tie_players) else alive_players
        voting_result = self._parse_voting_response(response_text, valid_targets, round_num)
        
        return voting_result
    
    def _parse_voting_response(self, response: str, alive_players: List[int], round_num: int) -> dict:
        """解析投票响应，提取投票决策
        
            Returns:
            dict: {
                "reason": str,  # 投票理由（基于描述阶段的推理结果）
                "vote_number": int,  # 投票目标（玩家ID）
                "player_analyses": dict,  # 从记忆中获取的描述阶段的推理结果（对每个其他玩家的分析）
                "self_analysis": dict  # 从记忆中获取的描述阶段的推理结果（对自己的分析）
            }
        """
        import json_repair
        
        # 从记忆中获取描述阶段的推理结果
        player_analyses = {}
        self_analysis = {}
        
        # 获取当前轮次的推理结果（从记忆中）
        # 找到当前轮次的 self_analyses 和 player_analyses
        if self.memory.get("self_analyses"):
            for analysis in self.memory["self_analyses"]:
                if analysis.get("round") == round_num:
                    if analysis.get("analysis"):
                        self_analysis = analysis["analysis"]
                    break
        
        if self.memory.get("player_analyses"):
            # 优先查找描述阶段的分析，如果没有则查找投票阶段的分析
            # 兼容旧的没有phase字段的条目
            description_phase_analyses = {}
            voting_phase_analyses = {}
            no_phase_analyses = {}
            
            for analysis in self.memory["player_analyses"]:
                if analysis.get("round") == round_num:
                    phase = analysis.get("phase")
                    if phase == "description_reflection":
                        if analysis.get("analyses"):
                            description_phase_analyses.update(analysis.get("analyses", {}))
                    elif phase == "voting_reflection":
                        if analysis.get("analyses"):
                            voting_phase_analyses.update(analysis.get("analyses", {}))
                    elif phase is None:  # 兼容旧的没有phase字段的条目
                        if analysis.get("analyses"):
                            no_phase_analyses.update(analysis.get("analyses", {}))
            
            # 优先使用描述阶段的分析，其次投票阶段，最后是没有phase的旧数据
            if description_phase_analyses:
                player_analyses.update(description_phase_analyses)
            elif voting_phase_analyses:
                player_analyses.update(voting_phase_analyses)
            elif no_phase_analyses:
                player_analyses.update(no_phase_analyses)
        
        # 直接尝试解析整个响应为JSON
        try:
            data = json_repair.loads(response)
            
            # Check required fields
            if "vote_target" not in data:
                raise ValueError("Response missing required field: vote_target")
            
            # Parse new format (includes thinking, vote_target and vote_reason)
            thinking = str(data.get("thinking", ""))  # Voting thinking process
            vote_target = int(data.get("vote_target", 0))
            vote_reason = str(data.get("vote_reason", "No reason"))
            
            # Build complete reason (based on description phase reasoning results and voting decision)
            reason_parts = []
            
            # If there are description phase reasoning results, add to reason
            if player_analyses:
                reason_parts.append("**Description Phase Reasoning Results (Analysis of Each Other Player)**")
                for player_id_str in sorted(player_analyses.keys(), key=int):
                    player_id = int(player_id_str)
                    if player_id in alive_players and player_id != self.player_id:
                        analysis = player_analyses[player_id_str]
                        word_guess = analysis.get("word_guess", "unknown")
                        role_guess = analysis.get("role_guess", "unknown")
                        role_en = "civilian" if role_guess == "civilian" else ("undercover" if role_guess == "undercover" else "unknown")
                        reason_parts.append(f"Player {player_id}: guessed word is '{word_guess}', role is {role_en}. Reason: {analysis.get('word_reason', '')}; Role judgment reason: {analysis.get('role_reason', '')}")
            
            if self_analysis:
                reason_parts.append(f"\n**Description Phase Reasoning Results (Analysis of Myself)**")
                role_guess = self_analysis.get("role_guess", "unknown")
                role_en = "civilian" if role_guess == "civilian" else ("undercover" if role_guess == "undercover" else "unknown")
                role_reason = self_analysis.get("role_reason", "No reason")
                if role_guess == "unknown":
                    reason_parts.append(f"I cannot determine my own identity. Reason: {role_reason}")
                else:
                    reason_parts.append(f"I tend to think I am a {role_en}. Reason: {role_reason}")
            
            # Voting decision
            reason_parts.append(f"\n**Voting Decision**")
            reason_parts.append(f"Vote for Player {vote_target}. Reason: {vote_reason}")
            
            reason = "\n".join(reason_parts)
            
            # Validate vote_target is a valid player ID
            if vote_target in alive_players and vote_target != self.player_id:
                result = {
                    "reason": reason,
                    "vote_number": vote_target,
                    "thinking": thinking,  # Voting thinking process
                    "player_analyses": player_analyses,  # Description phase reasoning results from memory
                    "self_analysis": self_analysis  # Description phase reasoning results from memory
                }
                return result
            else:
                raise ValueError(f"Invalid vote target: {vote_target}")
                    
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            # 如果解析失败，使用默认值（不打印错误信息）
            pass
        
        valid_players = [pid for pid in alive_players if pid != self.player_id]
        if valid_players:
            default_vote_number = valid_players[0]
        else:
            default_vote_number = alive_players[0] if alive_players else 1
        
        return {
            "reason": "无法解析响应，响应格式不正确或缺少必需字段",
            "vote_number": default_vote_number,
            "thinking": "",  # 解析失败时，thinking 为空
            "player_analyses": player_analyses,  # 即使解析失败，也返回记忆中的推理结果
            "self_analysis": self_analysis
        }
    
    def _format_history_from_memory(self, history: List[dict]) -> str:
        """Format historical records from memory (including all rounds)"""
        if not history:
            return "This is the first round, there are no historical descriptions yet. You need to carefully give the first description."
        
        # Organize by round
        rounds_dict = {}
        for h in history:
            round_num = h["round"]
            if round_num not in rounds_dict:
                rounds_dict[round_num] = []
            rounds_dict[round_num].append(h)
        
        text = "**⚠️ Important: Historical descriptions from previous rounds (you cannot repeat these descriptions)**:\n"
        text += "Historical conversation records (all rounds, carefully analyze each player's description patterns, but absolutely must not repeat):\n"
        for round_num in sorted(rounds_dict.keys()):
            text += f"\nRound {round_num}:\n"
            for h in rounds_dict[round_num]:
                name = h.get("name", f"Player {h['player_id']}")
                text += f"  {name}: {h['description']}\n"
        
        text += "\n**⚠️ Warning: You must avoid repeating any content, keywords, or expressions from the above historical descriptions!**\n"

        return text
    
    def _format_history_with_votes_and_eliminations(self, history_descriptions: List[dict], 
                                                   current_round: int) -> str:
        """从记忆中格式化历史记录，包含描述、投票和淘汰信息
        
        Args:
            history_descriptions: 历史描述列表
            current_round: 当前轮次
        
        Returns:
            格式化后的历史文本，包含描述、投票和淘汰信息
        """
        if not history_descriptions and not self.memory.get("all_votes_history"):
            return "This is the first round, there are no historical descriptions and events yet."
        
        text_parts = []
        
        # Get historical voting records (excluding current round)
        historical_votes = [
            entry for entry in self.memory.get("all_votes_history", [])
            if entry.get("round", 0) < current_round
        ]
        
        # Organize descriptions by round
        if history_descriptions:
            rounds_dict = {}
            for h in history_descriptions:
                round_num = h["round"]
                if round_num not in rounds_dict:
                    rounds_dict[round_num] = []
                rounds_dict[round_num].append(h)
            
            # Add descriptions, votes, and elimination information for each historical round
            for round_num in sorted(rounds_dict.keys()):
                text_parts.append(f"\n**Round {round_num}:**")
                
                # Add descriptions
                text_parts.append("[Description Phase]")
                for h in rounds_dict[round_num]:
                    name = h.get("name", f"Player {h['player_id']}")
                    text_parts.append(f"  {name}: {h['description']}")
                
                # Add voting information (if any)
                round_votes = next((entry for entry in historical_votes if entry.get("round") == round_num), None)
                if round_votes:
                    text_parts.append("\n[Voting Phase]")
                    votes = round_votes.get("votes", [])
                    vote_counts = {}
                    for vote in votes:
                        target_id = vote.get("target_id")
                        voter_name = vote.get("voter_name", f"Player {vote.get('voter_id')}")
                        target_name = vote.get("target_name", f"Player {target_id}")
                        text_parts.append(f"  {voter_name} voted for {target_name}")
                        vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
                    
                    # Infer eliminated player (player with most votes)
                    if vote_counts:
                        max_votes = max(vote_counts.values())
                        eliminated_candidates = [pid for pid, count in vote_counts.items() if count == max_votes]
                        if len(eliminated_candidates) == 1:
                            eliminated_id = eliminated_candidates[0]
                            eliminated_name = next(
                                (v.get("target_name", f"Player {eliminated_id}") 
                                 for v in votes if v.get("target_id") == eliminated_id),
                                f"Player {eliminated_id}"
                            )
                            text_parts.append(f"\n[Elimination Result]")
                            text_parts.append(f"  Player {eliminated_id} ({eliminated_name}) was eliminated (votes: {max_votes})")
                else:
                    text_parts.append("\n[Voting Phase]")
                    text_parts.append("  (Voting information for this round is unavailable)")
        
        # If no historical descriptions but there is voting history
        elif historical_votes:
            text_parts.append("Historical voting records:")
            for entry in historical_votes:
                round_num = entry.get("round", 0)
                text_parts.append(f"\nRound {round_num} voting:")
                votes = entry.get("votes", [])
                vote_counts = {}
                for vote in votes:
                    voter_name = vote.get("voter_name", f"Player {vote.get('voter_id')}")
                    target_name = vote.get("target_name", f"Player {vote.get('target_id')}")
                    text_parts.append(f"  {voter_name} voted for {target_name}")
                    target_id = vote.get("target_id")
                    vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
                
                # Infer eliminated player
                if vote_counts:
                    max_votes = max(vote_counts.values())
                    eliminated_candidates = [pid for pid, count in vote_counts.items() if count == max_votes]
                    if len(eliminated_candidates) == 1:
                        eliminated_id = eliminated_candidates[0]
                        eliminated_name = next(
                            (v.get("target_name", f"Player {eliminated_id}") 
                             for v in votes if v.get("target_id") == eliminated_id),
                            f"Player {eliminated_id}"
                        )
                        text_parts.append(f"  Elimination result: Player {eliminated_id} ({eliminated_name}) was eliminated (votes: {max_votes})")
        
        return "\n".join(text_parts) if text_parts else "This is the first round, there are no historical descriptions and events yet."
    
    def _format_voting_history_from_memory(self, voting_history: List[dict] = None) -> str:
        """从记忆中格式化投票历史记录
        
        Args:
            voting_history: 投票历史列表，如果为None则使用self.memory["voting_history"]
        
        Returns:
            格式化后的投票历史文本
        """
        if voting_history is None:
            voting_history = self.memory["voting_history"]
        
        if not voting_history:
            return "This is the first round of voting, you have no voting history yet."
        
        text = "Your voting history (refer to previous voting decisions):\n"
        for vote in voting_history:
            text += f"  Round {vote['round']}: voted for {vote['target_name']} "
            text += f"(vote_number: {vote['vote_number']}, reason: {vote['reason']})\n"
        
        return text
    
    def _format_previous_analyses_from_memory(self) -> str:
        """从记忆中格式化上一轮的分析（从player_analyses和self_analyses中提取）
        
        Returns:
            格式化后的上一轮分析文本
        """
        player_analyses_history = self.memory.get("player_analyses", [])
        self_analyses_history = self.memory.get("self_analyses", [])
        
        if not player_analyses_history and not self_analyses_history:
            return "This is the first round of voting, you have no analysis history yet."
        
        text_parts = []
        
        # Get the most recent round's analysis
        if self_analyses_history:
            latest_self = self_analyses_history[-1]
            latest_round = latest_self["round"]
            self_analysis = latest_self.get("analysis", {})
            
            if self_analysis:
                text_parts.append(f"Your analysis of yourself from Round {latest_round} (please update based on new information):")
                role_guess = self_analysis.get("role_guess", "unknown")
                role_en = "civilian" if role_guess == "civilian" else ("undercover" if role_guess == "undercover" else "unknown")
                text_parts.append(f"  Identity guess: {role_en}")
                text_parts.append(f"  Reason: {self_analysis.get('role_reason', 'No reason')}")
                text_parts.append("")
        
        if player_analyses_history:
            latest_player = player_analyses_history[-1]
            latest_round = latest_player["round"]
            player_analyses = latest_player.get("analyses", {})
            
            if player_analyses:
                text_parts.append(f"Your analysis of other players from Round {latest_round} (please update based on new information):")
                for player_id_str in sorted(player_analyses.keys(), key=int):
                    analysis = player_analyses[player_id_str]
                    role_guess = analysis.get("role_guess", "unknown")
                    role_en = "civilian" if role_guess == "civilian" else ("undercover" if role_guess == "undercover" else "unknown")
                    word_guess = analysis.get("word_guess", "unknown")
                    text_parts.append(f"  Player {player_id_str}: word '{word_guess}', role {role_en} (reason: {analysis.get('role_reason', 'No reason')})")
                text_parts.append("")
        
        return "\n".join(text_parts)
    
    def _format_current_self_analysis_from_memory(self, round_num: int) -> str:
        """从记忆中格式化当前轮次对自己的分析（描述阶段的推理结果）
        如果当前轮次没有分析，则显示最近一轮的分析
        
        Args:
            round_num: 当前轮次
        
        Returns:
            格式化后的当前轮次自我分析文本（如果当前轮次没有，则返回最近一轮的分析）
        """
        self_analyses_history = self.memory.get("self_analyses", [])
        
        # First, look for current round's analysis
        for analysis_entry in self_analyses_history:
            if analysis_entry.get("round") == round_num:
                self_analysis = analysis_entry.get("analysis", {})
                if self_analysis:
                    role_guess = self_analysis.get("role_guess", "unknown")
                    role_en = "civilian" if role_guess == "civilian" else ("undercover" if role_guess == "undercover" else "unknown")
                    role_reason = self_analysis.get("role_reason", "No reason")
                    confidence = self_analysis.get("confidence", "medium")
                    confidence_en = {"high": "high", "medium": "medium", "low": "low"}.get(confidence, "medium")
                    
                    return f"Identity guess: {role_en}\nReason: {role_reason}\nConfidence: {confidence_en}"
        
        # If current round has no analysis, find the most recent round's analysis (previous round)
        if self_analyses_history:
            # Sort by round, get the most recent round's analysis
            sorted_analyses = sorted(self_analyses_history, key=lambda x: x.get("round", 0), reverse=True)
            for analysis_entry in sorted_analyses:
                if analysis_entry.get("round") < round_num:  # Only look for previous rounds
                    self_analysis = analysis_entry.get("analysis", {})
                    if self_analysis:
                        analysis_round = analysis_entry.get("round", 0)
                        role_guess = self_analysis.get("role_guess", "unknown")
                        role_en = "civilian" if role_guess == "civilian" else ("undercover" if role_guess == "undercover" else "unknown")
                        role_reason = self_analysis.get("role_reason", "No reason")
                        confidence = self_analysis.get("confidence", "medium")
                        confidence_en = {"high": "high", "medium": "medium", "low": "low"}.get(confidence, "medium")
                        
                        return f"(Analysis from Round {analysis_round}) Identity guess: {role_en}\nReason: {role_reason}\nConfidence: {confidence_en}"
        
        return "No guess about your own identity yet."
    
    def _get_all_players_from_memory(self) -> List[int]:
        """从记忆中推断所有玩家ID（排除自己）
        
        Returns:
            所有玩家ID列表（排除自己），按ID排序
        """
        all_player_ids = set()
        
        # 从所有描述中获取玩家ID
        for desc in self.memory.get("all_descriptions", []):
            player_id = desc.get("player_id")
            if player_id and player_id != self.player_id:
                all_player_ids.add(player_id)
        
        # 从所有投票记录中获取玩家ID
        for vote_entry in self.memory.get("all_votes_history", []):
            for vote in vote_entry.get("votes", []):
                voter_id = vote.get("voter_id")
                target_id = vote.get("target_id")
                if voter_id and voter_id != self.player_id:
                    all_player_ids.add(voter_id)
                if target_id and target_id != self.player_id:
                    all_player_ids.add(target_id)
        
        # 从分析记录中获取玩家ID
        for analysis_entry in self.memory.get("player_analyses", []):
            analyses = analysis_entry.get("analyses", {})
            for key in analyses.keys():
                try:
                    player_id = self._normalize_player_id(key)
                    if player_id != self.player_id:
                        all_player_ids.add(player_id)
                except Exception:
                    continue
        
        return sorted(list(all_player_ids))
    
    def _get_eliminated_players_from_memory(self, current_round: int) -> List[int]:
        """从记忆中推断被淘汰的玩家ID（基于投票历史）
        
        Args:
            current_round: 当前轮次（排除当前轮次的淘汰）
        
        Returns:
            被淘汰的玩家ID列表，按ID排序
        """
        eliminated_players = []
        
        # 从投票历史中推断被淘汰的玩家（得票最多的玩家）
        for vote_entry in self.memory.get("all_votes_history", []):
            round_num = vote_entry.get("round", 0)
            if round_num >= current_round:
                continue  # 跳过当前轮次及之后的轮次
            
            votes = vote_entry.get("votes", [])
            if not votes:
                continue
            
            # 统计得票数
            vote_counts = {}
            for vote in votes:
                target_id = vote.get("target_id")
                if target_id:
                    vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
            
            # 找出得票最多的玩家（被淘汰）
            if vote_counts:
                max_votes = max(vote_counts.values())
                eliminated_candidates = [pid for pid, count in vote_counts.items() if count == max_votes]
                # 如果只有一个得票最多的玩家，则被淘汰
                if len(eliminated_candidates) == 1:
                    eliminated_players.append(eliminated_candidates[0])
        
        return sorted(list(set(eliminated_players)))
    
    def _format_current_player_analyses_from_memory(self, round_num: int, alive_players: Optional[List[int]] = None) -> str:
        """从记忆中格式化当前轮次对其他玩家的分析（描述阶段的推理结果）
        如果当前轮次没有分析，则显示最近一轮的分析
        确保包含所有目标玩家（如果提供了alive_players），否则包含所有玩家
        
        Args:
            round_num: 当前轮次
            alive_players: 存活玩家列表（可选，如果为None则包含所有玩家）
        
        Returns:
            格式化后的当前轮次对其他玩家的分析文本（如果当前轮次没有，则返回最近一轮的分析）
        """
        player_analyses_history = self.memory.get("player_analyses", [])
        
        # 确定要显示的所有玩家（排除自己）
        if alive_players is None:
            # 如果没有指定存活玩家，从memory中推断所有玩家
            target_players = self._get_all_players_from_memory()
        else:
            # 使用提供的存活玩家列表（排除自己）
            target_players = [pid for pid in alive_players if pid != self.player_id]
        
        if not target_players:
            return "No guesses about other players' identities yet."
        
        # 首先查找当前轮次的分析（优先查找描述阶段的分析）
        current_analyses = {}
        description_phase_analyses = {}
        voting_phase_analyses = {}
        no_phase_analyses = {}
        
        for analysis_entry in player_analyses_history:
            if analysis_entry.get("round") == round_num:
                phase = analysis_entry.get("phase")
                analyses = analysis_entry.get("analyses", {})
                if phase == "description_reflection":
                    description_phase_analyses.update(analyses)
                elif phase == "voting_reflection":
                    voting_phase_analyses.update(analyses)
                elif phase is None:  # 兼容旧的没有phase字段的条目
                    no_phase_analyses.update(analyses)
        
        # 优先使用描述阶段的分析，其次投票阶段，最后是没有phase的旧数据
        if description_phase_analyses:
            current_analyses = description_phase_analyses
        elif voting_phase_analyses:
            current_analyses = voting_phase_analyses
        elif no_phase_analyses:
            current_analyses = no_phase_analyses
        
        # 如果当前轮次没有分析，查找最近一轮的分析
        analysis_round = None
        if not current_analyses and player_analyses_history:
            # 按轮次排序，获取最近一轮的分析
            sorted_analyses = sorted(player_analyses_history, key=lambda x: x.get("round", 0), reverse=True)
            for analysis_entry in sorted_analyses:
                if analysis_entry.get("round") < round_num:  # 只查找之前的轮次
                    current_analyses = analysis_entry.get("analyses", {})
                    analysis_round = analysis_entry.get("round", 0)
                    break
        
        # 获取被淘汰的玩家列表（用于检查玩家是否被淘汰）
        eliminated_players = self._get_eliminated_players_from_memory(round_num)
        
        # Format output, ensuring all target players are included
        text_parts = []
        if analysis_round is not None:
            text_parts.append(f"(Analysis from Round {analysis_round})")
        
        # Generate analysis text for each target player
        for player_id in sorted(target_players):
            player_id_str = str(player_id)
            
            # Check if player is eliminated
            if player_id in eliminated_players:
                # Player has been eliminated, set to eliminated
                role_guess = "eliminated"
                role_en = "eliminated"
                word_guess = "unknown"
                word_reason = ""
                role_reason = "This player has been eliminated"
            elif player_id_str in current_analyses:
                # Has analysis result
                analysis = current_analyses[player_id_str]
                role_guess = analysis.get("role_guess", "unknown")
                # If analysis result is already eliminated, keep it
                if role_guess == "eliminated":
                    role_en = "eliminated"
                else:
                    role_en = "civilian" if role_guess == "civilian" else ("undercover" if role_guess == "undercover" else "unknown")
                word_guess = analysis.get("word_guess", "unknown")
                word_reason = analysis.get("word_reason", "")
                role_reason = analysis.get("role_reason", "")
            else:
                # No analysis result, show as unknown
                role_guess = "unknown"
                role_en = "unknown"
                word_guess = "unknown"
                word_reason = ""
                role_reason = "No analysis yet"
            
            text_parts.append(f"Player {player_id_str}:")
            text_parts.append(f"  Word guess: {word_guess}")
            if word_reason:
                text_parts.append(f"  Word guess reason: {word_reason}")
            text_parts.append(f"  Role guess: {role_en}")
            if role_reason:
                text_parts.append(f"  Role guess reason: {role_reason}")
            text_parts.append("")
        
        return "\n".join(text_parts) if text_parts else "No guesses about other players' identities yet."
    
    def _format_all_votes_history_from_memory(self, all_votes_history: List[dict] = None) -> str:
        """从记忆中格式化所有人的投票历史记录
        
        Args:
            all_votes_history: 所有投票历史列表，如果为None则使用self.memory["all_votes_history"]
        
        Returns:
            格式化后的投票历史文本
        """
        if all_votes_history is None:
            all_votes_history = self.memory["all_votes_history"]
        
        if not all_votes_history:
            return "This is the first round of voting, there is no voting history yet."
        
        text = "All players' voting history (analyze voting patterns, identify possible alliances):\n"
        for entry in all_votes_history:
            text += f"\n  Round {entry['round']} voting:\n"
            for vote in entry["votes"]:
                text += (
                    f"    {vote.get('voter_name', 'Player ' + str(vote['voter_id']))} "
                    f"voted for {vote.get('target_name', 'Player ' + str(vote['target_id']))}\n"
                )

        return text
    

