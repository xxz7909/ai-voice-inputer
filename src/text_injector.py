"""
文字注入模块
将识别的文字输入到当前光标位置
"""

import subprocess
import shutil
from typing import Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class TextInjector(ABC):
    """文字注入器基类"""
    
    @abstractmethod
    def inject(self, text: str) -> bool:
        """
        注入文字
        
        Args:
            text: 要输入的文字
        
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查注入器是否可用"""
        pass


class XdotoolInjector(TextInjector):
    """使用 xdotool 注入文字 (X11)"""
    
    def __init__(self, delay_ms: int = 5):
        """
        初始化 xdotool 注入器
        
        Args:
            delay_ms: 按键延迟 (毫秒)
        """
        self.delay_ms = delay_ms
        self._xdotool_path = shutil.which('xdotool')
    
    def is_available(self) -> bool:
        """检查 xdotool 是否可用"""
        return self._xdotool_path is not None
    
    def inject(self, text: str) -> bool:
        """使用 xdotool 输入文字"""
        if not text:
            return True
        
        if not self.is_available():
            logger.error("xdotool 未安装")
            return False
        
        try:
            # 使用 xdotool type 命令
            result = subprocess.run(
                [
                    self._xdotool_path,
                    'type',
                    '--delay', str(self.delay_ms),
                    '--clearmodifiers',  # 清除修饰键状态
                    text
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"xdotool 执行失败: {result.stderr}")
                return False
            
            logger.debug(f"成功输入文字: {text[:50]}...")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("xdotool 执行超时")
            return False
        except Exception as e:
            logger.error(f"xdotool 执行异常: {e}")
            return False


class YdotoolInjector(TextInjector):
    """使用 ydotool 注入文字 (Wayland)"""
    
    def __init__(self, delay_ms: int = 5):
        """
        初始化 ydotool 注入器
        
        Args:
            delay_ms: 按键延迟 (毫秒)
        """
        self.delay_ms = delay_ms
        self._ydotool_path = shutil.which('ydotool')
    
    def is_available(self) -> bool:
        """检查 ydotool 是否可用"""
        return self._ydotool_path is not None
    
    def inject(self, text: str) -> bool:
        """使用 ydotool 输入文字"""
        if not text:
            return True
        
        if not self.is_available():
            logger.error("ydotool 未安装")
            return False
        
        try:
            result = subprocess.run(
                [
                    self._ydotool_path,
                    'type',
                    '--delay', str(self.delay_ms),
                    text
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"ydotool 执行失败: {result.stderr}")
                return False
            
            logger.debug(f"成功输入文字: {text[:50]}...")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("ydotool 执行超时")
            return False
        except Exception as e:
            logger.error(f"ydotool 执行异常: {e}")
            return False


class WtypeInjector(TextInjector):
    """使用 wtype 注入文字 (Wayland)"""
    
    def __init__(self, delay_ms: int = 5):
        """
        初始化 wtype 注入器
        
        Args:
            delay_ms: 按键延迟 (毫秒)
        """
        self.delay_ms = delay_ms
        self._wtype_path = shutil.which('wtype')
    
    def is_available(self) -> bool:
        """检查 wtype 是否可用"""
        return self._wtype_path is not None
    
    def inject(self, text: str) -> bool:
        """使用 wtype 输入文字"""
        if not text:
            return True
        
        if not self.is_available():
            logger.error("wtype 未安装")
            return False
        
        try:
            result = subprocess.run(
                [
                    self._wtype_path,
                    '-d', str(self.delay_ms),
                    text
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                logger.error(f"wtype 执行失败: {result.stderr}")
                return False
            
            logger.debug(f"成功输入文字: {text[:50]}...")
            return True
            
        except subprocess.TimeoutExpired:
            logger.error("wtype 执行超时")
            return False
        except Exception as e:
            logger.error(f"wtype 执行异常: {e}")
            return False


class ClipboardInjector(TextInjector):
    """使用剪贴板注入文字 (备用方案)"""
    
    def __init__(self):
        self._xclip_path = shutil.which('xclip')
        self._xdotool_path = shutil.which('xdotool')
    
    def is_available(self) -> bool:
        """检查 xclip 和 xdotool 是否可用"""
        return self._xclip_path is not None and self._xdotool_path is not None
    
    def inject(self, text: str) -> bool:
        """通过剪贴板输入文字"""
        if not text:
            return True
        
        if not self.is_available():
            logger.error("xclip 或 xdotool 未安装")
            return False
        
        try:
            # 复制到剪贴板
            process = subprocess.Popen(
                [self._xclip_path, '-selection', 'clipboard'],
                stdin=subprocess.PIPE,
                text=True
            )
            process.communicate(input=text, timeout=5)
            
            if process.returncode != 0:
                logger.error("复制到剪贴板失败")
                return False
            
            # 模拟 Ctrl+V 粘贴
            result = subprocess.run(
                [self._xdotool_path, 'key', '--clearmodifiers', 'ctrl+v'],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode != 0:
                logger.error("粘贴失败")
                return False
            
            logger.debug(f"成功通过剪贴板输入文字: {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"剪贴板注入异常: {e}")
            return False


class TextInjectorFactory:
    """文字注入器工厂"""
    
    INJECTORS = {
        'xdotool': XdotoolInjector,
        'ydotool': YdotoolInjector,
        'wtype': WtypeInjector,
        'clipboard': ClipboardInjector,
    }
    
    @classmethod
    def create(cls, method: str = 'xdotool', delay_ms: int = 5) -> TextInjector:
        """
        创建文字注入器
        
        Args:
            method: 注入方法
            delay_ms: 按键延迟
        
        Returns:
            TextInjector: 注入器实例
        """
        if method not in cls.INJECTORS:
            logger.warning(f"未知的注入方法: {method}, 使用 xdotool")
            method = 'xdotool'
        
        injector_class = cls.INJECTORS[method]
        
        if method == 'clipboard':
            injector = injector_class()
        else:
            injector = injector_class(delay_ms=delay_ms)
        
        if not injector.is_available():
            logger.warning(f"{method} 不可用，尝试其他方法")
            # 尝试其他方法
            for alt_method, alt_class in cls.INJECTORS.items():
                if alt_method != method:
                    if alt_method == 'clipboard':
                        alt_injector = alt_class()
                    else:
                        alt_injector = alt_class(delay_ms=delay_ms)
                    
                    if alt_injector.is_available():
                        logger.info(f"使用 {alt_method} 作为替代")
                        return alt_injector
            
            raise RuntimeError("没有可用的文字注入方法，请安装 xdotool 或 ydotool")
        
        return injector
    
    @classmethod
    def get_available_methods(cls) -> list[str]:
        """获取可用的注入方法列表"""
        available = []
        for method, injector_class in cls.INJECTORS.items():
            if method == 'clipboard':
                injector = injector_class()
            else:
                injector = injector_class(delay_ms=5)
            
            if injector.is_available():
                available.append(method)
        
        return available
