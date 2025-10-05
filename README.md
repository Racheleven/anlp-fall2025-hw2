# Pittsburgh Events RAG System
# 匹兹堡活动数据检索增强生成系统

这是一个基于匹兹堡活动数据的RAG（检索增强生成）系统，能够智能地回答关于匹兹堡各种活动和美食节的问题。

## 系统特性

- **多格式数据支持**: 支持Markdown (.md) 和 CSV (.csv) 文件
- **本地模型支持**: 可以使用本地模型保护隐私
- **OpenAI集成**: 可选择使用OpenAI API获得更好的生成效果
- **交互式界面**: 提供友好的命令行交互界面
- **向量搜索**: 基于语义相似性的智能检索

## 数据源

系统处理两个主要数据文件夹：

1. **Event_Pittsburgh_CMU_data** - 包含：
   - CMU校园活动日历
   - 匹兹堡市中心活动
   - 匹兹堡城市活动日历

2. **Food_related_events_data** - 包含：
   - 香蕉分裂节 (Banana Split Festival)
   - 小意大利日 (Little Italy Days)
   - 匹兹堡餐厅周 (Pittsburgh Restaurant Week)
   - 匹兹堡塔可节 (Pittsburgh Taco Fest)
   - 匹克尔斯堡节 (Picklesburgh)

## 快速开始

### 方法1: 使用快速启动脚本（推荐）

```bash
# 1. 安装依赖
python install.py

# 2. 快速开始
python quick_start.py
```

### 方法2: 手动安装

```bash
# 安装依赖
pip install -r requirements.txt

# 运行交互式界面
python interactive_rag.py
```

### 方法3: 运行测试

```bash
# 运行测试验证系统功能
python test_rag.py --test

# 运行演示查询
python test_rag.py --demo
```

## 使用方法

### 1. 基本使用

```python
from rag import PittsburghEventsRAG

# 初始化RAG系统
rag = PittsburghEventsRAG(
    data_path=".",
    use_local_models=True  # 使用本地模型
)

# 加载数据
rag.load_data()

# 构建向量存储
rag.build_vectorstore()

# 查询
result = rag.query("What food festivals are available in Pittsburgh?")
print(result['answer'])
```

### 2. 交互式界面

运行交互式界面：

```bash
python interactive_rag.py
```

这将启动一个交互式命令行界面，您可以：
- 输入问题获得答案
- 查看数据摘要
- 获取帮助信息

### 3. 使用OpenAI API

如果您有OpenAI API密钥，可以获得更好的生成效果：

```python
rag = PittsburghEventsRAG(
    data_path=".",
    use_local_models=False,
    openai_api_key="your-api-key-here"
)

rag.setup_retrieval_chain()  # 设置生成链
```

## 系统架构

```
数据文件 (MD/CSV)
    ↓
文档加载器
    ↓
文本分割器
    ↓
向量化 (Embeddings)
    ↓
向量数据库 (FAISS)
    ↓
检索系统
    ↓
生成系统 (可选)
    ↓
答案输出
```

## 主要组件

### PittsburghEventsRAG 类

主要RAG系统类，包含以下方法：

- `load_data()`: 加载所有数据文件
- `build_vectorstore()`: 构建向量存储
- `query(question)`: 查询系统
- `get_event_summary()`: 获取数据摘要
- `save_vectorstore(path)`: 保存向量存储
- `load_vectorstore(path)`: 加载向量存储

### InteractiveRAGInterface 类

交互式界面类，提供：

- 系统初始化
- 交互式查询会话
- 帮助和摘要功能

## 示例查询

系统可以回答各种关于匹兹堡活动的问题：

- "What food festivals are available in Pittsburgh?"
- "Tell me about the Banana Split Festival activities"
- "When is Pittsburgh Restaurant Week?"
- "What entertainment is available at Little Italy Days?"
- "What CMU campus events are scheduled?"

## 配置选项

### 本地模型模式（推荐）
- 保护隐私
- 无需API密钥
- 离线工作

### OpenAI模式
- 更好的生成质量
- 需要API密钥
- 需要网络连接

## 文件结构

```
.
├── rag.py                 # 主RAG系统核心代码
├── interactive_rag.py     # 交互式命令行界面
├── test_rag.py           # 测试脚本
├── install.py            # 安装脚本
├── quick_start.py        # 快速启动脚本
├── requirements.txt      # Python依赖文件
├── README.md            # 说明文档
├── Event_Pittsburgh_CMU_data/     # 匹兹堡和CMU活动数据
│   ├── campus_events_page/
│   ├── CMU_events_calendar/
│   ├── Downtown_Pittsburgh_events_calendar/
│   └── Pittsburgh_events_calendar/
└── Food_related_events_data/      # 美食节相关数据
    ├── Banana_Split_Fest/
    ├── Little_Italy_Days/
    ├── Pittsburgh_Restaurant_Week/
    ├── Pittsburgh_Taco_Fest/
    ├── Picklesburgh/
    └── food_festival/
```

## 技术细节

- **文本分割**: 使用RecursiveCharacterTextSplitter，块大小1000字符
- **向量化**: 使用sentence-transformers/all-MiniLM-L6-v2模型
- **向量存储**: FAISS数据库
- **检索**: 语义相似性搜索，返回最相关的5个文档
- **生成**: 可选使用OpenAI GPT模型或基于检索的答案

## 注意事项

1. 首次运行时会下载模型文件，可能需要一些时间
2. 确保有足够的内存来加载和处理所有文档
3. 向量存储可以保存到磁盘以便快速重新加载
4. 系统支持中英文查询

## 故障排除

### 常见问题

1. **模型下载失败**: 检查网络连接，或使用本地模型
2. **内存不足**: 减少chunk_size或使用更小的模型
3. **文件编码问题**: 确保所有文件使用UTF-8编码

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 扩展功能

系统设计为可扩展的，您可以：

- 添加新的数据源
- 集成其他语言模型
- 自定义文本分割策略
- 添加更多元数据字段
- 实现Web界面

## 许可证

本项目仅供学习和研究使用。