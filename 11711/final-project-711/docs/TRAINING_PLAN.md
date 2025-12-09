# 模型训练方案：Behavior Cloning (SFT) + RL-GRPO

## 1. 训练目标

通过两阶段训练提升模型在"谁是卧底"游戏中的表现：
1. **Behavior Cloning (SFT)**：让模型模仿能力更强的模型（teacher model）
2. **RL-GRPO训练**：通过强化学习进一步优化策略

## 2. Behavior Cloning (SFT) 实施步骤

### 2.1 构造 Teacher Model（能力更强的模型）

**目标**：使用能力更强的模型作为"老师"，让学生模型模仿。

**方案**：使用更强的LLM作为Teacher
- **选择**：使用GPT-4、Claude-3.5、Qwen-Max等更强的模型
- **优势**：这些模型推理能力更强，能生成高质量的描述和投票决策
- **实施**：
  1. 使用这些模型运行游戏，收集它们的输出
  2. 记录它们的描述和投票决策作为"标准答案"

### 2.2 数据收集：让Teacher模型生成训练数据

#### 步骤1：使用Teacher模型运行游戏
```python
# 伪代码示例
teacher_model = load_teacher_model()  # GPT-4、Claude-3.5等更强的LLM

for game in range(num_games):
    game_state = initialize_game()
    
    while not game_over:
        # 描述阶段
        for player in alive_players:
            # 使用teacher模型生成描述
            description = teacher_model.generate_description(
                word=player.word,
                history=game_state.history,
                round_num=game_state.round
            )
            game_state.add_description(player.id, description)
        
        # 投票阶段
        for player in alive_players:
            # 使用teacher模型生成投票决策
            vote = teacher_model.vote(
                word=player.word,
                history=game_state.history,
                alive_players=alive_players,
                round_num=game_state.round
            )
            game_state.add_vote(player.id, vote)
        
        game_state.check_win_condition()
```

#### 步骤2：收集高质量样本
- **筛选标准**：
  - 只保留最终游戏胜利的样本（优先）
  - 描述不重复历史的样本
  - 投票决策合理的样本（平民投票给卧底，卧底合理伪装）
- **数据量**：
  - 描述阶段：20,000-50,000条样本
  - 投票阶段：20,000-50,000条样本

#### 步骤3：数据格式
```json
{
  "input": "系统提示 + 用户提示（包含游戏状态、历史信息）",
  "output": "teacher模型的输出（描述或投票决策）",
  "metadata": {
    "player_role": "civilian/undercover",
    "player_word": "苹果",
    "round": 1,
    "game_outcome": "win/lose"
  }
}
```

### 2.3 训练学生模型（Behavior Cloning）

#### 步骤1：准备训练数据
```python
# 数据格式转换
train_data = []
for sample in teacher_generated_data:
    train_data.append({
        "instruction": sample["input"],  # 游戏状态和提示
        "output": sample["output"],      # teacher的输出
        "input": ""  # 如果需要instruction格式
    })
```

#### 步骤2：模型配置
- **基础模型**：Qwen3-VL-8B-Instruct（或你选择的模型）
- **微调方法**：LoRA（推荐）或全参数微调
- **LoRA参数**：
  - rank: 8
  - alpha: 16
  - dropout: 0.1

#### 步骤3：训练超参数
- **学习率**：1e-5 到 3e-5（LoRA）
- **批次大小**：16-32
- **训练轮数**：3-5 epochs
- **优化器**：AdamW
- **损失函数**：标准交叉熵损失

#### 步骤4：训练流程
```python
# 伪代码
model = load_base_model()
model = apply_lora(model)  # 如果使用LoRA

for epoch in range(num_epochs):
    for batch in dataloader:
        # 标准监督学习
        outputs = model(input_ids=batch["input_ids"])
        loss = cross_entropy_loss(outputs.logits, batch["labels"])
        loss.backward()
        optimizer.step()
    
    # 验证
    eval_metrics = evaluate(model, val_set)
    if eval_metrics["win_rate"] > best_win_rate:
        save_checkpoint(model)
```

## 3. RL-GRPO训练方案

### 3.1 训练目标
在Behavior Cloning的基础上，通过强化学习进一步优化策略，提升胜率。

### 3.2 奖励函数设计

#### 即时奖励
- **描述阶段**：
  - 不重复历史：+0.1
  - 重复历史：-0.2
  - 策略合理：+0.05

- **投票阶段**：
  - 平民投票给卧底：+0.3
  - 平民投票给平民：-0.1
  - 卧底合理伪装投票：+0.2

#### 延迟奖励
- 游戏胜利：+1.0（平民）或 +1.5（卧底）
- 游戏失败：-0.5
- 存活到最后一轮：+0.2

### 3.3 GRPO训练流程

#### 步骤1：初始化
- 使用Behavior Cloning训练好的模型作为初始策略

#### 步骤2：数据收集
```python
# 使用当前策略进行自对弈
trajectories = []
for game in range(num_games):
    trajectory = play_game(policy=current_policy)
    trajectories.append(trajectory)
```

#### 步骤3：计算相对奖励
```python
# 将轨迹分组
groups = group_trajectories(trajectories, group_size=32)

# 计算组内相对奖励
for group in groups:
    rewards = [t["episode_reward"] for t in group]
    mean_reward = np.mean(rewards)
    std_reward = np.std(rewards)
    
    for trajectory in group:
        relative_reward = (trajectory["episode_reward"] - mean_reward) / (std_reward + 1e-8)
        trajectory["relative_reward"] = relative_reward
```

#### 步骤4：策略更新
```python
# GRPO损失函数
for batch in dataloader:
    log_probs = policy.get_log_probs(batch["states"], batch["actions"])
    loss = -torch.mean(log_probs * batch["relative_rewards"])
    loss.backward()
    optimizer.step()
```

#### 步骤5：训练循环
```python
for epoch in range(num_epochs):
    # 1. 收集数据
    trajectories = collect_trajectories(policy, num_games=100)
    
    # 2. 计算相对奖励
    trajectories = compute_relative_rewards(trajectories)
    
    # 3. 更新策略
    for batch in create_batches(trajectories):
        update_policy(batch)
    
    # 4. 评估
    eval_metrics = evaluate(policy)
    if eval_metrics["win_rate"] > best_win_rate:
        save_checkpoint(policy)
```

### 3.4 超参数
- **学习率**：1e-6 到 5e-6
- **批次大小**：32-64
- **组大小**：16-32
- **训练轮数**：10-20 epochs
- **更新频率**：每收集100-200局游戏后更新

## 4. 实施步骤总结

### 阶段1：Behavior Cloning（2-3周）

1. **选择Teacher模型**
   - 使用GPT-4、Claude-3.5等更强的LLM作为teacher

2. **收集Teacher数据**
   - 使用teacher模型运行10,000-20,000局游戏
   - 筛选高质量样本（胜利对局、不重复描述、合理投票）

3. **训练学生模型**
   - 使用LoRA微调基础模型
   - 训练3-5个epochs
   - 在验证集上评估性能

### 阶段2：RL-GRPO训练（3-4周）

1. **初始化策略**
   - 使用Behavior Cloning训练好的模型

2. **实现GRPO训练框架**
   - 实现数据收集、相对奖励计算、策略更新

3. **训练**
   - 进行多轮GRPO训练
   - 持续监控胜率、描述质量等指标

4. **评估和优化**
   - 在测试集上评估最终性能
   - 进行超参数调优

## 5. 评估指标

### 任务级指标
- **描述任务**：
  - 重复率（越低越好）
  - 策略合理性评分

- **投票任务**：
  - 投票准确性（平民投票给卧底的比例）
  - 推理质量评分

### 游戏级指标
- **胜率**：平民胜率、卧底胜率、总体胜率
- **存活指标**：平均存活轮数
- **游戏质量**：平均游戏轮数

## 6. 关键注意事项

### Behavior Cloning
1. **Teacher质量很重要**：选择能力强的teacher模型，确保生成高质量数据
2. **数据筛选**：只保留高质量样本（胜利对局、合理决策）
3. **数据平衡**：确保平民和卧底角色的样本比例平衡
4. **避免过拟合**：使用验证集监控，及时早停

### RL-GRPO
1. **稳定性**：使用相对奖励机制提高训练稳定性
2. **探索**：初始阶段使用较高温度参数鼓励探索
3. **评估**：定期评估模型性能，保存最佳检查点
4. **多智能体**：确保不同角色都有足够的训练数据

## 7. 资源需求

- **GPU**：至少2-4块A100或同等算力
- **内存**：至少64GB
- **存储**：至少500GB用于数据和模型
- **API费用**：如果使用GPT-4等API作为teacher，需要预算API调用费用
