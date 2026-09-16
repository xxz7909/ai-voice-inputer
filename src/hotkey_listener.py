"""
全局热键监听模块
监听 Win+Ctrl 组合键来触发语音输入
"""

import os
import threading
import logging
from typing import Callable, Set, Optional

# pynput 在 import 阶段就会连接 X server, 失败时给出更明确的提示
try:
    from pynput import keyboard
except ImportError as e:
    raise ImportError(
        "无法加载键盘监听模块 (pynput), 通常是 DISPLAY/XAUTHORITY 无效导致:\n"
        f"  DISPLAY={os.environ.get('DISPLAY', '(未设置)')}\n"
        f"  XAUTHORITY={os.environ.get('XAUTHORITY', '(未设置)')}\n"
        f"  原始错误: {e}"
    ) from e

logger = logging.getLogger(__name__)


class HotkeyListener:
    """全局热键监听器"""
    
    # 键名到 pynput Key 的映射
    KEY_MAP = {
        'ctrl': keyboard.Key.ctrl,
        'ctrl_l': keyboard.Key.ctrl_l,
        'ctrl_r': keyboard.Key.ctrl_r,
        'alt': keyboard.Key.alt,
        'alt_l': keyboard.Key.alt_l,
        'alt_r': keyboard.Key.alt_r,
        'shift': keyboard.Key.shift,
        'shift_l': keyboard.Key.shift_l,
        'shift_r': keyboard.Key.shift_r,
        'cmd': keyboard.Key.cmd,
        'cmd_l': keyboard.Key.cmd_l,
        'cmd_r': keyboard.Key.cmd_r,
        'super': keyboard.Key.cmd,  # Super 键就是 Win/Cmd 键
        'win': keyboard.Key.cmd,
        'meta': keyboard.Key.cmd,
    }
    
    def __init__(
        self,
        hotkeys: list[str],
        on_activate: Optional[Callable[[], None]] = None,
        on_deactivate: Optional[Callable[[], None]] = None,
    ):
        """
        初始化热键监听器
        
        Args:
            hotkeys: 热键列表，如 ['ctrl', 'cmd']
            on_activate: 热键激活时的回调
            on_deactivate: 热键释放时的回调
        """
        self.hotkeys = self._parse_hotkeys(hotkeys)
        self.on_activate = on_activate
        self.on_deactivate = on_deactivate
        
        self.pressed_keys: Set[keyboard.Key] = set()
        self.is_active: bool = False
        self.listener: Optional[keyboard.Listener] = None
        self._lock = threading.Lock()
    
    def _parse_hotkeys(self, hotkeys: list[str]) -> Set[keyboard.Key]:
        """解析热键字符串到 pynput Key"""
        parsed = set()
        for key in hotkeys:
            key_lower = key.lower()
            if key_lower in self.KEY_MAP:
                parsed.add(self.KEY_MAP[key_lower])
            else:
                logger.warning(f"未知的热键: {key}")
        return parsed
    
    def _normalize_key(self, key) -> Optional[keyboard.Key]:
        """将按键标准化"""
        # 处理 ctrl 类型的键
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            if keyboard.Key.ctrl in self.hotkeys:
                return keyboard.Key.ctrl
        
        # 处理 alt 类型的键
        if key in (keyboard.Key.alt_l, keyboard.Key.alt_r):
            if keyboard.Key.alt in self.hotkeys:
                return keyboard.Key.alt
        
        # 处理 shift 类型的键
        if key in (keyboard.Key.shift_l, keyboard.Key.shift_r):
            if keyboard.Key.shift in self.hotkeys:
                return keyboard.Key.shift
        
        # 处理 cmd/win/super 类型的键
        if key in (keyboard.Key.cmd_l, keyboard.Key.cmd_r):
            if keyboard.Key.cmd in self.hotkeys:
                return keyboard.Key.cmd
        
        return key
    
    def _on_press(self, key):
        """按键按下事件"""
        normalized = self._normalize_key(key)
        
        with self._lock:
            if normalized in self.hotkeys:
                self.pressed_keys.add(normalized)
                
                # 检查是否所有热键都已按下
                if self.hotkeys <= self.pressed_keys and not self.is_active:
                    self.is_active = True
                    logger.debug("热键激活")
                    if self.on_activate:
                        threading.Thread(target=self.on_activate).start()
    
    def _on_release(self, key):
        """按键释放事件"""
        normalized = self._normalize_key(key)
        
        with self._lock:
            if normalized in self.pressed_keys:
                self.pressed_keys.discard(normalized)
                
                # 如果任意一个热键被释放且当前处于激活状态
                if self.is_active:
                    self.is_active = False
                    logger.debug("热键释放")
                    if self.on_deactivate:
                        threading.Thread(target=self.on_deactivate).start()
    
    def start(self):
        """启动热键监听"""
        if self.listener is not None:
            return
        
        self.listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
            suppress=False  # 不阻止按键传递到其他应用
        )
        self.listener.start()
        logger.info(f"热键监听已启动: {[k.name for k in self.hotkeys]}")
    
    def stop(self):
        """停止热键监听"""
        if self.listener is not None:
            self.listener.stop()
            self.listener = None
            logger.info("热键监听已停止")
    
    def join(self):
        """等待监听器结束"""
        if self.listener is not None:
            self.listener.join()


class HotkeyManager:
    """热键管理器"""
    
    _instance: Optional[HotkeyListener] = None
    
    @classmethod
    def create(
        cls,
        hotkeys: list[str],
        on_activate: Optional[Callable[[], None]] = None,
        on_deactivate: Optional[Callable[[], None]] = None,
    ) -> HotkeyListener:
        """创建热键监听器"""
        if cls._instance is not None:
            cls._instance.stop()
        
        cls._instance = HotkeyListener(
            hotkeys=hotkeys,
            on_activate=on_activate,
            on_deactivate=on_deactivate,
        )
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> Optional[HotkeyListener]:
        """获取当前实例"""
        return cls._instance
    
    @classmethod
    def stop(cls):
        """停止监听"""
        if cls._instance is not None:
            cls._instance.stop()
            cls._instance = None
