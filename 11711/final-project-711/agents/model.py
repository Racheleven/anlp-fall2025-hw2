# agents/model.py
"""Model class for LLM initialization"""
from langchain_openai import ChatOpenAI
from typing import Optional


class GameModel:
    """游戏模型类 - 封装LLM的初始化和管理"""
    
    def __init__(
        self,
        api_key: str = "sk-amcjzxomyzuispivnvvtgszrnxijmxpkmewbvlviffgborlg",
        base_url: str = "https://api.siliconflow.cn/v1",
        model: str = "Qwen/Qwen2.5-32B-Instruct",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        timeout: Optional[float] = 60.0
    ):
        """初始化游戏模型
        
        Args:
            api_key: API密钥
            base_url: API基础URL
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 请求超时时间（秒），默认60秒
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model_name = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        # 创建LLM实例
        self.llm = ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout
        )
    
    def get_llm(self) -> ChatOpenAI:
        """获取LLM实例"""
        return self.llm
    
    def __repr__(self) -> str:
        return f"GameModel(model={self.model_name}, base_url={self.base_url})"

