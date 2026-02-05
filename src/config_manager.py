"""
配置管理模块
负责加载和管理 YAML 配置文件
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ASRVADConfig:
    """VAD 配置"""
    enabled: bool = True
    silence_threshold: float = 0.5
    min_speech_duration: float = 0.3


@dataclass
class ASRConfig:
    """ASR (语音识别) 配置"""
    model: str = "medium"
    device: str = "auto"
    compute_type: str = "int8"
    language: str = "zh"
    vad: ASRVADConfig = field(default_factory=ASRVADConfig)


@dataclass
class AudioConfig:
    """音频配置"""
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_ms: int = 100


@dataclass
class HotkeyConfig:
    """热键配置"""
    keys: List[str] = field(default_factory=lambda: ["ctrl", "cmd"])
    show_status: bool = True


@dataclass
class InputConfig:
    """输入配置"""
    method: str = "xdotool"
    delay_ms: int = 5


@dataclass
class LLMConfig:
    """LLM 增强配置"""
    enabled: bool = False
    api_url: str = "http://localhost:8000/v1/chat/completions"
    model: str = "qwen2.5-7b"
    api_key: str = ""
    timeout: int = 5
    prompt: str = ""


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    file: str = "~/.local/share/ai-voice-inputer/logs/voice-inputer.log"


@dataclass
class NotificationConfig:
    """通知配置"""
    enabled: bool = True
    method: str = "notify-send"


@dataclass
class Config:
    """主配置类"""
    asr: ASRConfig = field(default_factory=ASRConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    input: InputConfig = field(default_factory=InputConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)


class ConfigManager:
    """配置管理器"""
    
    DEFAULT_CONFIG_PATHS = [
        Path.home() / ".config" / "ai-voice-inputer" / "config.yaml",
        Path(__file__).parent.parent / "config" / "config.yaml",
    ]
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = self._find_config_path(config_path)
        self.config = self._load_config()
    
    def _find_config_path(self, custom_path: Optional[str]) -> Path:
        """查找配置文件路径"""
        if custom_path:
            path = Path(custom_path).expanduser()
            if path.exists():
                return path
            raise FileNotFoundError(f"配置文件不存在: {custom_path}")
        
        for path in self.DEFAULT_CONFIG_PATHS:
            if path.exists():
                return path
        
        # 如果没有找到，创建默认配置
        default_path = self.DEFAULT_CONFIG_PATHS[0]
        self._create_default_config(default_path)
        return default_path
    
    def _create_default_config(self, path: Path):
        """创建默认配置文件"""
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # 复制项目内的默认配置
        source_config = Path(__file__).parent.parent / "config" / "config.yaml"
        if source_config.exists():
            import shutil
            shutil.copy(source_config, path)
        else:
            # 创建最小配置
            default_config = {
                'asr': {'model': 'medium', 'device': 'auto', 'language': 'zh'},
                'hotkey': {'keys': ['ctrl', 'cmd']},
                'input': {'method': 'xdotool'},
            }
            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, allow_unicode=True)
    
    def _load_config(self) -> Config:
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        return self._parse_config(data)
    
    def _parse_config(self, data: dict) -> Config:
        """解析配置数据到配置对象"""
        config = Config()
        
        # ASR 配置
        if 'asr' in data:
            asr_data = data['asr']
            vad_data = asr_data.pop('vad', {})
            config.asr = ASRConfig(
                model=asr_data.get('model', 'medium'),
                device=asr_data.get('device', 'auto'),
                compute_type=asr_data.get('compute_type', 'int8'),
                language=asr_data.get('language', 'zh'),
                vad=ASRVADConfig(**vad_data) if vad_data else ASRVADConfig()
            )
        
        # 音频配置
        if 'audio' in data:
            config.audio = AudioConfig(**data['audio'])
        
        # 热键配置
        if 'hotkey' in data:
            config.hotkey = HotkeyConfig(**data['hotkey'])
        
        # 输入配置
        if 'input' in data:
            config.input = InputConfig(**data['input'])
        
        # LLM 配置
        if 'llm' in data:
            config.llm = LLMConfig(**data['llm'])
        
        # 日志配置
        if 'logging' in data:
            config.logging = LoggingConfig(**data['logging'])
        
        # 通知配置
        if 'notification' in data:
            config.notification = NotificationConfig(**data['notification'])
        
        return config
    
    def save_config(self, config: Optional[Config] = None):
        """保存配置到文件"""
        if config:
            self.config = config
        
        data = {
            'asr': {
                'model': self.config.asr.model,
                'device': self.config.asr.device,
                'compute_type': self.config.asr.compute_type,
                'language': self.config.asr.language,
                'vad': {
                    'enabled': self.config.asr.vad.enabled,
                    'silence_threshold': self.config.asr.vad.silence_threshold,
                    'min_speech_duration': self.config.asr.vad.min_speech_duration,
                }
            },
            'audio': {
                'sample_rate': self.config.audio.sample_rate,
                'channels': self.config.audio.channels,
                'chunk_duration_ms': self.config.audio.chunk_duration_ms,
            },
            'hotkey': {
                'keys': self.config.hotkey.keys,
                'show_status': self.config.hotkey.show_status,
            },
            'input': {
                'method': self.config.input.method,
                'delay_ms': self.config.input.delay_ms,
            },
            'llm': {
                'enabled': self.config.llm.enabled,
                'api_url': self.config.llm.api_url,
                'model': self.config.llm.model,
                'api_key': self.config.llm.api_key,
                'timeout': self.config.llm.timeout,
                'prompt': self.config.llm.prompt,
            },
            'logging': {
                'level': self.config.logging.level,
                'file': self.config.logging.file,
            },
            'notification': {
                'enabled': self.config.notification.enabled,
                'method': self.config.notification.method,
            }
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


# 全局配置实例
_config_manager: Optional[ConfigManager] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """获取全局配置"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_path)
    return _config_manager.config


def reload_config(config_path: Optional[str] = None) -> Config:
    """重新加载配置"""
    global _config_manager
    _config_manager = ConfigManager(config_path)
    return _config_manager.config
