"""
LLM 增强模块
使用大语言模型对语音识别结果进行纠错和优化
"""

import requests
import json
from typing import Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """LLM 配置"""
    enabled: bool = False
    api_url: str = "http://localhost:8000/v1/chat/completions"
    model: str = "qwen2.5-7b"
    api_key: str = ""
    timeout: int = 5
    prompt: str = ""


class LLMEnhancer:
    """LLM 文本增强器"""
    
    DEFAULT_PROMPT = """请修正以下语音转写结果，使其符合书面表达规范：
1. 添加正确的标点符号
2. 修正同音错别字
3. 修正技术术语的拼写
4. 保持原意不变，不要添加额外内容

语音转写结果：{text}

修正后的文本（只输出修正后的文本，不要输出其他内容）："""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        初始化 LLM 增强器
        
        Args:
            config: LLM 配置
        """
        self.config = config or LLMConfig()
        self.prompt_template = self.config.prompt or self.DEFAULT_PROMPT
    
    def enhance(self, text: str) -> str:
        """
        增强文本
        
        Args:
            text: 原始文本
        
        Returns:
            str: 增强后的文本
        """
        if not self.config.enabled:
            return text
        
        if not text.strip():
            return text
        
        try:
            enhanced = self._call_llm(text)
            if enhanced and enhanced.strip():
                logger.debug(f"LLM 增强: {text[:30]}... -> {enhanced[:30]}...")
                return enhanced
            return text
        except Exception as e:
            logger.warning(f"LLM 增强失败，返回原文: {e}")
            return text
    
    def _call_llm(self, text: str) -> str:
        """调用 LLM API"""
        prompt = self.prompt_template.format(text=text)
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        if self.config.api_key:
            headers['Authorization'] = f'Bearer {self.config.api_key}'
        
        # 检测 API 类型
        if '/v1/chat/completions' in self.config.api_url:
            # OpenAI 兼容 API (vLLM, OpenAI, etc.)
            return self._call_openai_compatible(prompt, headers)
        else:
            # 通用 HTTP API
            return self._call_generic(prompt, headers)
    
    def _call_openai_compatible(self, prompt: str, headers: dict) -> str:
        """调用 OpenAI 兼容 API"""
        payload = {
            'model': self.config.model,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': 1024,
            'temperature': 0.1,  # 低温度保证输出稳定
        }
        
        response = requests.post(
            self.config.api_url,
            headers=headers,
            json=payload,
            timeout=self.config.timeout
        )
        
        response.raise_for_status()
        result = response.json()
        
        return result['choices'][0]['message']['content'].strip()
    
    def _call_generic(self, prompt: str, headers: dict) -> str:
        """调用通用 HTTP API"""
        payload = {
            'prompt': prompt,
            'max_tokens': 1024,
            'temperature': 0.1,
        }
        
        response = requests.post(
            self.config.api_url,
            headers=headers,
            json=payload,
            timeout=self.config.timeout
        )
        
        response.raise_for_status()
        result = response.json()
        
        # 尝试不同的响应格式
        if 'text' in result:
            return result['text'].strip()
        elif 'response' in result:
            return result['response'].strip()
        elif 'output' in result:
            return result['output'].strip()
        else:
            return str(result).strip()
    
    def test_connection(self) -> bool:
        """测试 LLM 连接"""
        try:
            result = self._call_llm("测试")
            logger.info(f"LLM 连接测试成功: {result[:50]}")
            return True
        except Exception as e:
            logger.error(f"LLM 连接测试失败: {e}")
            return False


class LLMEnhancerFactory:
    """LLM 增强器工厂"""
    
    _instance: Optional[LLMEnhancer] = None
    
    @classmethod
    def get_instance(cls, config: Optional[LLMConfig] = None) -> LLMEnhancer:
        """获取 LLM 增强器单例"""
        if cls._instance is None:
            cls._instance = LLMEnhancer(config)
        return cls._instance
    
    @classmethod
    def create(cls, config: Optional[LLMConfig] = None) -> LLMEnhancer:
        """创建新的 LLM 增强器"""
        cls._instance = LLMEnhancer(config)
        return cls._instance
    
    @classmethod
    def reset(cls):
        """重置单例"""
        cls._instance = None
