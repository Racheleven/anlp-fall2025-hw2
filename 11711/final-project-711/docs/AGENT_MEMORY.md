# 智能体记忆系统

## 概述

每个智能体（`PlayerAgent`）都有自己的**持久化记忆系统**，能够记住：
1. 所有轮次中所有智能体说过的话（描述历史）
2. 自己每一轮的投票记录（投票历史）
3. 自己每一轮的完整推理过程（推理历史）
4. 所有人的投票记录（投票模式历史）

这使得智能体能够基于完整的对话历史、投票历史、推理历史和投票模式做出更智能的决策。


## 记忆系统架构

### 1. Agent 记忆结构

每个 `PlayerAgent` 实例都有一个 `memory` 字典：

```python
self.memory = {
    "all_descriptions": [
        {
            "round": 1,
            "player_id": 1,
            "description": "这是一种常见的水果",
            "name": "玩家1"
        },
        {
            "round": 1,
            "player_id": 2,
            "description": "圆形的，可以直接吃",
            "name": "玩家2"
        },
        # ... 所有轮次的所有描述
    ],
    "voting_history": [
        {
            "round": 1,
            "target_id": 2,
            "target_name": "玩家2",
            "vote_number": 2,
            "reason": "详细分析每个玩家的过程。首先分析玩家1：...；然后分析玩家2：...；最后分析玩家3：...。综合考虑，我认为玩家2最可疑，因为..."
        },
        # ... 所有轮次的投票记录
    ],
    "reasoning_history": [
        {
            "round": 1,
            "reasoning": {
                "reason": "详细分析每个玩家的过程。首先分析玩家1：...；然后分析玩家2：...；最后分析玩家3：...。综合考虑，我认为玩家2最可疑，因为...",
                "vote_number": 2
            }
        },
        # ... 所有轮次的推理历史
    ],
    "all_votes_history": [
        {
            "round": 1,
            "votes": [
                {"voter_id": 1, "target_id": 2, "voter_name": "玩家1", "target_name": "玩家2"},
                {"voter_id": 2, "target_id": 3, "voter_name": "玩家2", "target_name": "玩家3"},
                # ... 所有人的投票记录
            ]
        },
        # ... 所有轮次的投票历史
    ]
}
```

### 2. Agent 实例持久化

- **之前**：每个阶段都重新创建 Agent 实例，Agent 没有记忆
- **现在**：Agent 实例在 `GameState.agents_map` 中持久化保存，在整个游戏过程中保持存在

```python
# 在 initialize_game 中创建
agents_map = {
    1: PlayerAgent(...),  # 玩家1的Agent实例
    2: PlayerAgent(...),  # 玩家2的Agent实例
    ...
}

# 保存到 state 中
state["agents_map"] = agents_map
```

## 记忆更新流程

### 描述阶段 (Description Phase)

1. **生成描述**：每个 Agent 从自己的记忆中读取：
   - 历史轮次的描述（`round < round_num`）
   - 当前轮次已说过的描述（`round == round_num`，排除自己）
   - 这样可以避免重复其他人的描述

2. **实时更新记忆**：每个玩家说话后，立即更新所有 Agent 的记忆，让后续说话的玩家可以看到前面玩家的描述，形成动态推理。

**代码位置**：`nodes.py` - `description_phase()` 函数

### 投票阶段 (Voting Phase)

Agent 在投票时会使用完整的记忆：
- 所有历史描述
- 自己的投票历史
- 自己的推理历史
- 所有人的投票历史

投票后，更新 Agent 的投票记忆和推理历史。

**代码位置**：`nodes.py` - `voting_phase()` 函数

## 记忆访问方法

### 1. `add_to_memory(round_num, descriptions=None, vote_record=None, reasoning=None, all_votes=None)`
将描述、投票记录、推理过程和所有投票添加到记忆中。

**添加描述**（描述阶段使用）：
```python
agent.add_to_memory(round_num=2, descriptions=[
    {"player_id": 1, "description": "...", "name": "玩家1"},
])
```

**添加投票记录和推理过程**（投票阶段使用）：
```python
agent.add_to_memory(
    round_num=2, 
    vote_record={
        "target_id": 3,
        "target_name": "玩家3",
        "vote_number": 3,
        "reason": "详细分析每个玩家的过程..."
    },
    reasoning={
        "reason": "详细分析每个玩家的过程。首先分析玩家1：...；然后分析玩家2：...；最后分析玩家3：...。综合考虑，我认为玩家3最可疑，因为...",
        "vote_number": 3
    }
)
```

**添加所有人的投票记录**（投票阶段后使用）：
```python
agent.add_to_memory(
    round_num=2,
    all_votes=[
        {"voter_id": 1, "target_id": 2, "voter_name": "玩家1", "target_name": "玩家2"},
        {"voter_id": 2, "target_id": 3, "voter_name": "玩家2", "target_name": "玩家3"},
        # ...
    ]
)
```

### 2. `_format_history_from_memory(history)`
将记忆中的历史格式化为可读文本（按轮次组织）。这是内部方法，用于在生成描述和分析时格式化历史记录。

```python
# 从记忆中获取历史
all_history = [h for h in agent.memory["all_descriptions"] if h["round"] < round_num]

# 格式化历史
formatted = agent._format_history_from_memory(all_history)
# 输出:
# 第1轮：
#   玩家1: 描述1
#   玩家2: 描述2
# 第2轮：
#   玩家1: 描述3
#   ...
```

### 3. `_format_voting_history_from_memory(voting_history=None)`
将记忆中的投票历史格式化为可读文本。这是内部方法，用于在投票时格式化投票历史。

```python
# 从记忆中获取投票历史
voting_history_text = agent._format_voting_history_from_memory()
# 输出:
# 你的投票历史（参考之前的投票决策）：
#   第1轮: 投票给 玩家2 (vote_number: 2, reason: 详细分析每个玩家的过程...)
#   第2轮: 投票给 玩家3 (vote_number: 3, reason: 详细分析每个玩家的过程...)
```

### 4. `_format_reasoning_history_from_memory(reasoning_history=None)`
将记忆中的推理历史格式化为可读文本。这是内部方法，用于在投票时格式化推理历史。

```python
# 从记忆中获取推理历史
reasoning_history_text = agent._format_reasoning_history_from_memory()
# 输出:
# 你之前的推理历史（参考之前的判断，分析判断的准确性）：
#   第1轮你的推理：
#     分析：详细分析每个玩家的过程。首先分析玩家1：...；然后分析玩家2：...；最后分析玩家3：...。综合考虑，我认为玩家2最可疑，因为...
#     投票给：玩家2
```

### 5. `_format_all_votes_history_from_memory(all_votes_history=None)`
将记忆中的所有投票历史格式化为可读文本。这是内部方法，用于在投票时格式化所有人的投票记录。

```python
# 从记忆中获取所有投票历史
all_votes_history_text = agent._format_all_votes_history_from_memory()
# 输出:
# 所有人的投票历史（分析投票模式，识别可能的联盟）：
#   第1轮投票：
#     玩家1 投票给 玩家2
#     玩家2 投票给 玩家3
#     ...
```

### 6. 直接访问记忆
如果需要访问记忆，可以直接访问 `agent.memory`：

```python
# 获取所有历史描述
all_history = agent.memory["all_descriptions"]

# 获取特定轮次的历史
round_1_history = [h for h in agent.memory["all_descriptions"] if h["round"] == 1]

# 获取所有投票历史
all_votes = agent.memory["voting_history"]

# 获取特定轮次的投票
round_1_vote = [v for v in agent.memory["voting_history"] if v["round"] == 1]

# 获取推理历史
all_reasoning = agent.memory["reasoning_history"]

# 获取所有人的投票历史
all_votes_history = agent.memory["all_votes_history"]
```

## 记忆的优势

### ✅ 完整上下文
- Agent 能够看到**所有轮次**中所有玩家的描述
- 不再局限于最近几轮，可以分析长期模式

### ✅ 智能分析
- 能够识别玩家描述的一致性/不一致性
- 可以追踪某个玩家在不同轮次中的描述变化
- 更好地识别卧底（描述模式异常）
- 能够参考自己的投票历史，保持投票决策的一致性

### ✅ 投票记忆
- Agent 能够记住自己每一轮投给了谁
- 在后续投票时可以参考之前的投票决策
- 可以分析自己投票的准确性和一致性

### ✅ 推理记忆
- Agent 能够记住自己每一轮的完整推理过程（对所有玩家的分析）
- 可以回顾之前的判断，分析判断的准确性
- 能够识别自己判断的变化，调整推理策略

### ✅ 投票模式记忆
- Agent 能够记住所有人的投票记录
- 可以分析投票模式，识别可能的联盟
- 如果某些玩家总是投票给相同的人，可能是卧底联盟的信号

### ✅ 持久化
- Agent 实例在整个游戏过程中保持存在
- 记忆不会丢失，即使经过多轮游戏

## 示例：记忆如何帮助分析

假设游戏进行到第3轮：

**Agent 1 的记忆**：
```
第1轮：
  玩家1: 这是一种常见的水果
  玩家2: 圆形的，可以直接吃
  玩家3: 营养丰富，口感清脆

第2轮：
  玩家1: 通常是红色的
  玩家2: 可以直接吃，很甜
  玩家3: 口感清脆，水分多

第3轮：
  玩家1: 常见的水果
  玩家2: 圆形的
  玩家3: 营养丰富
```

Agent 1 可以分析：
- 玩家2和玩家3的描述一直很一致（都像在说"苹果"）
- 自己的描述也与他们一致
- 可能自己是平民，玩家2和玩家3也是平民

或者：
- 如果玩家3的描述突然变得模糊
- Agent 1 可以对比历史，发现玩家3的描述模式发生了变化
- 这可能是卧底的信号

## 代码位置

- **记忆系统定义**: `agents.py` - `PlayerAgent.memory`
- **描述记忆更新**: `nodes.py` - `description_phase()` 中的 `agent.add_to_memory()`
- **投票记忆更新**: `nodes.py` - `voting_phase()` 中的 `agent.add_to_memory()`
- **记忆使用**: `agents.py` - `generate_description()` 和 `vote()`

## 总结

通过记忆系统，每个智能体都能够：
1. ✅ 记住所有轮次中所有玩家的描述
2. ✅ 记住自己每一轮的投票记录
3. ✅ 记住自己每一轮的完整推理过程（对所有玩家的分析）
4. ✅ 记住所有人的投票记录，分析投票模式
5. ✅ 基于完整历史（描述+投票+推理+投票模式）做出更智能的决策
6. ✅ 识别长期模式和异常行为
7. ✅ 保持投票决策的一致性，同时根据新信息调整判断
8. ✅ 分析投票模式，识别可能的联盟
9. ✅ 回顾之前的判断，分析判断的准确性
10. ✅ 更好地推测自己的身份和其他玩家的身份

这使得游戏更加真实和有趣，智能体的行为更像真实玩家！

