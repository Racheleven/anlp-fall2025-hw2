# 配置文件使用说明

## 配置文件格式

项目支持通过 JSON 配置文件来管理模型配置（包括 api_key、base_url、model 等参数）。

### 配置文件位置

- 默认配置文件：项目根目录下的 `config.json`
- 自定义配置文件：通过 `--config` 参数指定路径

### 配置文件结构

创建一个 `config.json` 文件（或复制 `config.json.example`），格式如下：

```json
{
  "fixed_model_undercover": false,
  "default_model": {
    "api_key": "your-api-key-here",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "Qwen/Qwen2.5-32B-Instruct",
    "temperature": 0.7,
    "max_tokens": null,
    "timeout": 60.0
  },
  "undercover_model": {
    "api_key": "your-api-key-here",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "temperature": 0.7,
    "max_tokens": null,
    "timeout": 60.0
  },
  "civilian_model": {
    "api_key": "your-api-key-here",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "Qwen/Qwen2.5-32B-Instruct",
    "temperature": 0.7,
    "max_tokens": null,
    "timeout": 60.0
  }
}
```

### 配置说明

- `fixed_model_undercover`: 布尔值，是否根据身份固定分配模型
  - `true`: 卧底和平民使用不同的模型
  - `false`: 所有玩家使用相同模型（使用 `default_model` 配置）

- `default_model`: 当 `fixed_model_undercover=false` 时，所有玩家使用的模型配置
- `undercover_model`: 当 `fixed_model_undercover=true` 时，卧底玩家使用的模型配置
- `civilian_model`: 当 `fixed_model_undercover=true` 时，平民玩家使用的模型配置

### 模型配置参数

每个模型配置可以包含以下参数（所有参数都是可选的，未提供的参数将使用 `GameModel` 的默认值）：

- `api_key`: API 密钥
- `base_url`: API 基础 URL
- `model`: 模型名称
- `temperature`: 温度参数（0.0-2.0）
- `max_tokens`: 最大 token 数（null 表示不限制）
- `timeout`: 请求超时时间（秒）

## 使用方法

### 方法1：使用默认配置文件

1. 在项目根目录创建 `config.json` 文件
2. 运行脚本（会自动加载 `config.json`）：

```bash
python run_batch_games.py --exp exp1 --num-games 10
```

### 方法2：指定配置文件路径

```bash
python run_batch_games.py --exp exp1 --num-games 10 --config my_config.json
```

### 方法3：使用命令行参数（向后兼容）

如果不使用配置文件，仍然可以通过命令行参数指定模型：

```bash
python run_batch_games.py \
  --exp exp1 \
  --num-games 10 \
  --fixed-model-undercover \
  --undercover-model "Qwen/Qwen2.5-7B-Instruct" \
  --civilian-model "Qwen/Qwen2.5-32B-Instruct"
```

**注意**：如果同时提供了配置文件和命令行参数，配置文件会覆盖命令行参数。

## 示例配置

### 示例1：所有玩家使用相同模型

```json
{
  "fixed_model_undercover": false,
  "default_model": {
    "api_key": "sk-xxx",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "Qwen/Qwen2.5-32B-Instruct",
    "temperature": 0.7
  }
}
```

### 示例2：卧底和平民使用不同模型

```json
{
  "fixed_model_undercover": true,
  "undercover_model": {
    "api_key": "sk-xxx",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "Qwen/Qwen2.5-7B-Instruct",
    "temperature": 0.7
  },
  "civilian_model": {
    "api_key": "sk-xxx",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "Qwen/Qwen2.5-32B-Instruct",
    "temperature": 0.7
  }
}
```

### 示例3：使用不同的 API 提供商

```json
{
  "fixed_model_undercover": false,
  "default_model": {
    "api_key": "sk-xxx",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4",
    "temperature": 0.8,
    "timeout": 120.0
  }
}
```

