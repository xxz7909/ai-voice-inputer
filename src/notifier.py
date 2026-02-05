"""
通知模块
显示桌面通知
"""

import subprocess
import shutil
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Notifier:
    """桌面通知器"""
    
    def __init__(self, enabled: bool = True, method: str = "notify-send"):
        """
        初始化通知器
        
        Args:
            enabled: 是否启用通知
            method: 通知方法
        """
        self.enabled = enabled
        self.method = method
        self._notify_send_path = shutil.which('notify-send')
    
    def notify(
        self,
        title: str,
        message: str,
        icon: str = "audio-input-microphone",
        urgency: str = "normal",
        timeout: int = 2000
    ) -> bool:
        """
        发送通知
        
        Args:
            title: 标题
            message: 消息内容
            icon: 图标名称
            urgency: 紧急程度 (low, normal, critical)
            timeout: 显示时间 (毫秒)
        
        Returns:
            bool: 是否成功
        """
        if not self.enabled:
            return True
        
        if self._notify_send_path is None:
            logger.warning("notify-send 未安装，无法显示通知")
            return False
        
        try:
            subprocess.run(
                [
                    self._notify_send_path,
                    '-i', icon,
                    '-u', urgency,
                    '-t', str(timeout),
                    title,
                    message
                ],
                capture_output=True,
                timeout=5
            )
            return True
        except Exception as e:
            logger.warning(f"发送通知失败: {e}")
            return False
    
    def notify_recording_start(self):
        """通知开始录音"""
        self.notify(
            "语音输入",
            "🎙️ 开始录音...",
            icon="audio-input-microphone",
            timeout=1000
        )
    
    def notify_recording_stop(self):
        """通知停止录音"""
        self.notify(
            "语音输入",
            "⏹️ 录音结束，正在识别...",
            icon="audio-input-microphone",
            timeout=1000
        )
    
    def notify_transcription_done(self, text: str):
        """通知识别完成"""
        preview = text[:50] + "..." if len(text) > 50 else text
        self.notify(
            "语音输入",
            f"✅ {preview}",
            icon="dialog-information",
            timeout=2000
        )
    
    def notify_error(self, error: str):
        """通知错误"""
        self.notify(
            "语音输入错误",
            f"❌ {error}",
            icon="dialog-error",
            urgency="critical",
            timeout=3000
        )


class NotifierFactory:
    """通知器工厂"""
    
    _instance: Optional[Notifier] = None
    
    @classmethod
    def get_instance(cls, enabled: bool = True, method: str = "notify-send") -> Notifier:
        """获取通知器单例"""
        if cls._instance is None:
            cls._instance = Notifier(enabled=enabled, method=method)
        return cls._instance
    
    @classmethod
    def reset(cls):
        """重置单例"""
        cls._instance = None
