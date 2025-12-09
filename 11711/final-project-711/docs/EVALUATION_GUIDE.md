# 评估系统使用指南

## 📖 概述

本项目已整合了 `anlp-fall2025-hw3` 目录下的测试数据和评测指标计算功能。现在你可以：

1. 使用不同难度的测试数据（easy/medium/hard）
2. 批量运行游戏进行评估
3. 计算多种评估指标（胜率、检测率、语言连贯性等）

## 📁 文件结构

```
项目根目录/
├── data/
│   ├── __init__.py
│   └── word_pairs.py          # 词汇对数据加载模块
├── evaluation/
│   ├── __init__.py
│   └── metrics.py             # 评估指标计算模块
├── evaluate.py                # 批量评估脚本
└── anlp-fall2025-hw3/         # 原始测试数据
    └── data/
        ├── easy_keyword_pair.json
        ├── midium_keyword_pair.json
        ├── hard_keyword_pair.json
        └── keyword_pair.json
```

## 🚀 快速开始

### 1. 使用评估脚本

最简单的使用方式是运行 `evaluate.py` 脚本：

```bash
# 运行10局游戏，使用所有难度的词汇对
python evaluate.py --num-games 10 --difficulty all

# 只使用简单难度的词汇对
python evaluate.py --num-games 20 --difficulty easy

# 自定义玩家和卧底数量
python evaluate.py --num-games 10 --num-players 8 --num-undercover 2

# 安静模式（不打印详细信息）
python evaluate.py --num-games 10 --quiet

# 保存结果到指定文件
python evaluate.py --num-games 10 --output my_results.json
```

### 2. 在代码中使用

#### 加载测试数据

```python
from data import load_word_pairs

# 加载所有难度的词汇对
all_pairs = load_word_pairs(difficulty="all")

# 只加载简单难度的
easy_pairs = load_word_pairs(difficulty="easy")

# 只加载中等难度的
medium_pairs = load_word_pairs(difficulty="medium")

# 只加载困难难度的
hard_pairs = load_word_pairs(difficulty="hard")

# 使用默认的中文词汇对
default_pairs = load_word_pairs(difficulty="default")
```

#### 运行单局游戏并评估

```python
from graph.workflow import create_undercover_workflow
from data import load_word_pairs
from evaluation import evaluate_game_result

# 加载词汇对
word_pairs = load_word_pairs(difficulty="easy")

# 创建游戏状态
initial_state = {
    "num_players": 6,
    "num_undercover": 1,
    "word_pairs": word_pairs,  # 传递词汇对
    # ... 其他状态
}

# 运行游戏
workflow = create_undercover_workflow()
app = workflow.compile()
final_state = None
for state in app.stream(initial_state):
    final_state = state

# 评估结果
if final_state:
    final_state_dict = {}
    for node_name, node_state in final_state.items():
        if node_state:
            final_state_dict.update(node_state)
    
    metrics = evaluate_game_result(final_state_dict)
    print(f"平民获胜: {metrics['civilian_won']}")
    print(f"检测率: {metrics['detection_rate']:.2%}")
    print(f"语言连贯性: {metrics['linguistic_coherence']:.4f}")
```

#### 批量评估

```python
from evaluate import run_evaluation

# 运行批量评估
results = run_evaluation(
    num_games=10,
    num_players=6,
    num_undercover=1,
    difficulty="all",
    verbose=True
)

# 查看结果
summary = results["summary"]
print(f"平民胜率: {summary['civilian_win_rate']:.2%}")
print(f"卧底胜率: {summary['undercover_win_rate']:.2%}")
print(f"平均检测率: {summary['avg_detection_rate']:.2%}")
```

## 📊 评估指标说明

### 1. 胜率 (Win Rate)
- **平民胜率**: 平民获胜的游戏比例
- **卧底胜率**: 卧底获胜的游戏比例

### 2. 检测率 (Detection Rate)
- 卧底被正确识别并淘汰的比例
- 范围: 0.0 - 1.0

### 3. 语言连贯性 (Linguistic Coherence)
- 玩家描述与参考文本（平民词）的相似度
- 基于词汇重叠计算（可扩展为 BERTScore）
- 范围: 0.0 - 1.0

### 4. 说服力分数 (Persuasion Score)
- 玩家话语的说服力评分
- 当前为占位符实现，可扩展为 GPT-4 评分

### 5. 心理理论分数 (Theory of Mind)
- **1-Word**: 预测其他玩家的词
- **1-Identity**: 预测其他玩家的身份
- **2-Word**: 预测其他玩家认为我的词是什么
- **2-Identity**: 预测其他玩家认为我的身份是什么

## 🔧 高级用法

### 自定义词汇对

```python
from graph.nodes import set_word_pairs

# 自定义词汇对
custom_pairs = [
    {"civilian": "Apple", "undercover": "Pear"},
    {"civilian": "Dog", "undercover": "Cat"},
]

# 设置全局词汇对
set_word_pairs(custom_pairs)

# 然后运行游戏，会使用这些词汇对
```

### 使用不同难度的数据

```python
from data import get_word_pairs_by_difficulty

# 获取按难度分类的词汇对
pairs_by_difficulty = get_word_pairs_by_difficulty()

easy_pairs = pairs_by_difficulty["easy"]
medium_pairs = pairs_by_difficulty["medium"]
hard_pairs = pairs_by_difficulty["hard"]

print(f"简单: {len(easy_pairs)} 对")
print(f"中等: {len(medium_pairs)} 对")
print(f"困难: {len(hard_pairs)} 对")
```

### 计算单个指标

```python
from evaluation import (
    compute_win_rate,
    compute_detection_rate,
    compute_linguistic_coherence,
    compute_tom_scores
)

# 计算胜率
game_results = [
    {"winner": "civilian", "players": [...]},
    {"winner": "undercover", "players": [...]},
]
civilian_win_rate = compute_win_rate(game_results, role="civilian")

# 计算检测率
game_logs = [
    {"players": [...], "eliminated_players": [3], ...},
]
detection_rate = compute_detection_rate(game_logs, player_id=3)

# 计算语言连贯性
descriptions = ["A red fruit", "A sweet fruit", "Round and red"]
reference = "Apple"
coherence = compute_linguistic_coherence(descriptions, reference)
```

## 📝 数据格式

### 词汇对格式

测试数据中的词汇对格式为：
```json
[
    ["Civilian Word", "Undercover Word"],
    ["Apple", "Pear"],
    ...
]
```

加载后转换为项目格式：
```python
[
    {"civilian": "Apple", "undercover": "Pear"},
    ...
]
```

### 游戏结果格式

游戏结果包含以下字段：
```python
{
    "winner": "civilian" | "undercover",
    "round": 3,
    "players": [...],
    "elimination_history": [...],
    "current_descriptions": [...],
    "current_votes": [...],
    ...
}
```

## ⚙️ 配置选项

### evaluate.py 参数

- `--num-games`: 游戏局数（默认: 10）
- `--num-players`: 玩家数量（默认: 6）
- `--num-undercover`: 卧底数量（默认: 1）
- `--difficulty`: 难度级别（easy/medium/hard/all/default，默认: all）
- `--output`: 输出文件路径（默认: evaluation_results.json）
- `--quiet`: 安静模式，不打印详细信息

## 🎯 使用场景

### 场景1: 模型性能评估
```bash
# 评估模型在不同难度下的表现
python evaluate.py --num-games 50 --difficulty easy
python evaluate.py --num-games 50 --difficulty medium
python evaluate.py --num-games 50 --difficulty hard
```

### 场景2: 参数调优
```python
# 运行多组实验，比较不同参数设置
for temperature in [0.5, 0.7, 0.9]:
    # 设置模型参数
    # 运行评估
    results = run_evaluation(num_games=20, ...)
    # 比较结果
```

### 场景3: 多模型对比
```python
# 为不同玩家分配不同模型
# 运行评估，比较各模型表现
```

## 📌 注意事项

1. **数据路径**: 默认从 `anlp-fall2025-hw3/data/` 目录加载数据
2. **API 限制**: 批量运行时注意 API 调用限制
3. **成本控制**: 大量游戏会产生 API 调用费用
4. **结果保存**: 默认只保存摘要，完整结果可能很大

## 🔮 未来扩展

- [ ] 集成 BERTScore 进行更准确的语言连贯性计算
- [ ] 使用 GPT-4 进行说服力评分
- [ ] 支持心理理论（ToM）数据的收集和评估
- [ ] 可视化评估结果
- [ ] 支持并行运行多局游戏

