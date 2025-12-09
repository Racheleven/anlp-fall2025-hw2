# 谁是卧底 Multi-Agent System - LangGraph 设计框架

## 1. 系统架构概览

```
┌─────────────────────────────────────────────────────────┐
│                   Game Orchestrator                      │
│                  (LangGraph Workflow)                    │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   ┌─────────┐      ┌─────────┐      ┌─────────┐
   │ Agent 1 │      │ Agent 2 │ ...  │ Agent N │
   │ (平民)   │      │ (卧底)   │      │ (平民)   │
   └─────────┘      └─────────┘      └─────────┘
```

## 2. 核心组件设计

### 2.1 State Schema (游戏状态)

实际实现的状态定义（`state.py`）：

```python
class PlayerState(TypedDict):
    player_id: int
    name: str
    role: Literal["civilian", "undercover"]
    word: str
    alive: bool
    description_history: List[str]
    votes_received: int

class GameState(TypedDict, total=False):
    round: int
    phase: Literal["init", "description", "voting", "check", "end"]
    players: List[PlayerState]
    num_players: int
    num_undercover: int
    current_descriptions: List[dict]
    current_votes: List[dict]
    eliminated_players: List[int]
    elimination_history: List[dict]
    winner: Literal["civilian", "undercover", None]
    game_over: bool
    conversation_history: Annotated[List[dict], add]
    agents_map: Dict[int, Any]  # Agent实例持久化
```

### 2.2 Graph Nodes (节点定义)

#### Node 1: Initialize Game
- 功能：初始化游戏，分配角色和词汇
- 输入：玩家数量、词汇对
- 输出：初始化的 GameState

#### Node 2: Description Phase
- 功能：每个智能体依次描述自己的词汇
- 子流程：
  - 使用持久化的 Agent 实例（从 `state["agents_map"]` 获取）
  - 按顺序让每个 Agent 生成描述
  - Agent 从自己的记忆中读取历史（包括之前已说话的玩家的描述）
  - **实时更新记忆**：每个玩家说话后立即更新所有 Agent 的记忆
  - **避免重复**：Agent 会从记忆中读取当前轮次已说过的描述（排除自己）
  - 使用 `PlayerAgent`（LLM生成）

#### Node 3: Voting Phase
- 功能：推理并投票淘汰最可疑的玩家
- 子流程：
  - 每个 Agent 直接基于历史记忆和当前描述进行推理
  - 输出一个详细的分析理由（`reason`）和投票目标（`vote_number`）
  - `reason` 包含：对自己身份的倾向性判断 + 对所有其他玩家的详细分析
  - 每个存活 Agent 投票给最可疑的玩家（同时投票，看不到其他人的投票）
  - 统计投票结果，淘汰得票最多的玩家（平票则随机选择）

#### Node 5: Check Win Condition
- 功能：检查游戏是否结束
- 条件：
  - 卧底被淘汰 → 平民胜利
  - 卧底数量 ≥ 平民数量 → 卧底胜利
  - 否则继续下一轮

#### Node 6: Result Summary
- 功能：总结游戏结果和过程

### 2.3 Graph Structure (流程图)

```
START
  ↓
Initialize Game
  ↓
┌→ Description Phase (实时更新记忆)
│   ↓
│ Voting Phase (包含分析和投票)
│   ↓
│ Check Win Condition
│   ↓
│   ├─→ Continue? ──Yes──┘
│   │
│   No
│   ↓
End Game
  ↓
END
```

## 3. Agent 设计

### 3.1 Agent 类型

系统支持两种 Agent 类型：

#### PlayerAgent (AI Agent)
- 使用 LLM 自动生成描述和进行投票分析
- 记忆系统：存储所有历史描述、投票历史、推理历史、投票模式历史
- 核心方法：`generate_description()`, `vote()`, `add_to_memory()`

**关键特性**：
- Agent 实例持久化保存在 `state["agents_map"]` 中
- 记忆系统存储所有轮次中所有玩家的描述和投票历史

**详细说明**：参见 `AGENT_MEMORY.md`

### 3.2 Prompt Templates

Prompt 模板位于 `prompts/` 目录下：
- `description_prompts.py` - 描述阶段的 Prompt（包含避免重复规则、伪装策略）
- `voting_prompts.py` - 投票阶段的 Prompt（包含身份倾向性判断要求、投票策略）

**详细内容**：参见 `prompts/` 目录下的文件

## 4. 技术栈

### 4.1 核心库
- **LangGraph**: 工作流编排
- **LangChain**: Agent 框架和 LLM 集成
- **SiliconFlow API (Qwen模型)**: LLM 后端（可配置）
- **TypedDict**: 类型安全的状态定义

### 4.2 可选增强
- **ChromaDB / FAISS**: 语义相似度计算
- **Sentence Transformers**: Embedding 生成
- **Streamlit / Gradio**: UI 界面

## 5. 实现步骤

### Phase 1: 基础框架 (Week 1)
1. 定义 State Schema
2. 实现 Initialize 和 Check Win Condition 节点
3. 搭建基本的 LangGraph 流程

### Phase 2: Agent 实现 (Week 2)
1. 实现单个 Agent 的描述生成
2. 实现分析和投票逻辑
3. 测试单轮游戏流程

### Phase 3: 优化和增强 (Week 3)
1. 添加 Memory 和上下文管理
2. 优化 Prompt Engineering
3. 添加语义相似度分析

### Phase 4: UI 和部署 (Week 4)
1. 开发可视化界面
2. 添加日志和调试功能
3. 性能优化和测试

## 6. 关键挑战和解决方案

### 6.1 挑战：卧底推理能力
**解决方案**：
- 使用 Chain-of-Thought 让卧底分析其他描述
- 给卧底提供更多上下文和策略提示

### 6.2 挑战：避免 Hallucination
**解决方案**：
- 严格的 State 管理
- 使用 Structured Output
- 添加验证层

### 6.3 挑战：游戏平衡性
**解决方案**：
- 调整玩家数量和卧底比例
- 优化 Prompt 策略指导
- 支持人机对战模式

## 7. 扩展方向

1. **多轮对话**：允许玩家之间质询
2. **角色多样化**：添加"白板"角色
3. **难度等级**：调整词汇相似度
5. **统计分析**：胜率、策略效果分析

## 8. 实际代码结构

```
final_project/
├── main.py                      # 主程序入口
├── workflow.py                  # LangGraph 工作流构建
├── state.py                     # 游戏状态定义（TypedDict）
├── nodes.py                     # 工作流节点实现
├── agents.py                    # PlayerAgent 智能体实现
├── prompts/                     # Prompt 模板
│   ├── __init__.py
│   ├── description_prompts.py  # 描述阶段 prompts
│   └── voting_prompts.py       # 投票阶段 prompts
├── undercover_requirements.txt     # 依赖清单
├── readme.md                    # 项目说明
├── AGENT_MEMORY.md             # Agent 记忆系统文档
├── MESSAGE_PASSING.md          # 消息传递机制文档
└── langgraph_design.md         # LangGraph 设计文档（本文件）
```

## 9. 实际实现的关键特性

### ✅ 已实现
- LangGraph 工作流编排
- 统一的 PlayerAgent 设计（玩家不知道自己的身份）
- 实时记忆更新机制
- 直接投票推理（基于完整记忆一次性推理）
- Agent 实例持久化
- 完整的游戏循环

### 🔄 关键实现特性
- **Agent 接口**：`PlayerAgent` 提供统一的接口
- **实时记忆更新**：描述阶段每个玩家说话后立即更新所有 Agent 的记忆
- **避免重复机制**：Agent 会从记忆中读取当前轮次和历史轮次已说过的描述，确保不重复
- **身份倾向性判断**：投票阶段 Agent 会先判断自己的身份倾向性，再制定投票策略
- **同时投票机制**：每个 Agent 在同一轮投票时看不到其他人的投票
- **简化的工作流**：描述 → 投票（直接推理）→ 检查 → 循环/结束

---

这个设计文档描述了项目的架构和实现。实际代码已经完成，可以参考 `readme.md` 了解如何使用。