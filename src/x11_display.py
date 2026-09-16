"""
X11 环境检查模块
确保 DISPLAY 可用, 避免热键监听和文字输入因连接不到 X server 而失败
"""

import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def x11_socket_path(display: str) -> Optional[Path]:
    """
    根据 DISPLAY 值推算对应的 X11 socket 路径
    
    Args:
        display: DISPLAY 环境变量的值, 如 ':0'
    
    Returns:
        Optional[Path]: socket 路径, 无法解析时返回 None
    """
    if ':' not in display:
        return None
    
    num = display.split(':', 1)[1].split('.', 1)[0]
    if not num.isdigit():
        return None
    
    return Path(f'/tmp/.X11-unix/X{num}')


def ensure_x_display() -> bool:
    """
    确保 X11 DISPLAY 可用
    
    systemd 自启或从图形界面之外启动时, DISPLAY 可能未设置或指向不存在的
    显示器, 会导致 pynput/xdotool/notify-send 全部无法工作。
    此处在必要时自动探测当前会话可用的显示器。
    
    Returns:
        bool: DISPLAY 是否可用
    """
    display = os.environ.get('DISPLAY', '')
    socket_path = x11_socket_path(display) if display else None
    
    if socket_path is not None and socket_path.exists():
        return True
    
    if display:
        logger.warning(
            f"DISPLAY={display} 不可用 (未找到 {socket_path}), 尝试自动探测..."
        )
    
    # /tmp/.X11-unix/X<n> 对应 DISPLAY=:<n>
    x11_dir = Path('/tmp/.X11-unix')
    sockets = sorted(x11_dir.glob('X*')) if x11_dir.is_dir() else []
    
    for sock in sockets:
        if not sock.name[1:].isdigit():
            continue
        
        os.environ['DISPLAY'] = f':{sock.name[1:]}'
        
        # XAUTHORITY 未设置时回退到默认路径, 否则仍然无法连接 X server
        if not os.environ.get('XAUTHORITY'):
            default_auth = Path.home() / '.Xauthority'
            if default_auth.exists():
                os.environ['XAUTHORITY'] = str(default_auth)
        
        logger.warning(f"已自动切换到 DISPLAY={os.environ['DISPLAY']}")
        return True
    
    return False
