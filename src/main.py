"""
AI Voice Inputer - 主程序
Ubuntu AI 语音输入法核心控制器
"""

import os
# 禁用 CUDA 相关警告 (使用 CPU 模式时)
os.environ['CUDA_VISIBLE_DEVICES'] = ''
os.environ['CT2_VERBOSE'] = '-1'

import sys
import signal
import logging
import threading
import time
from pathlib import Path
from typing import Optional

from .x11_display import ensure_x_display

# 必须在导入 pynput (热键监听) 之前确定 DISPLAY,
# 否则连接不到 X server 时会在 import 阶段直接抛 ImportError
X_DISPLAY_AVAILABLE = ensure_x_display()

from .config_manager import ConfigManager, get_config, Config
from .asr_service import ASRServiceFactory, ASRService
from .audio_recorder import AudioRecorder, AudioConfig, AudioRecorderManager
from .hotkey_listener import HotkeyListener, HotkeyManager
from .text_injector import TextInjectorFactory, TextInjector
from .llm_enhancer import LLMEnhancer, LLMEnhancerFactory, LLMConfig
from .notifier import Notifier, NotifierFactory


def setup_logging(config: Config):
    """设置日志"""
    log_level = getattr(logging, config.logging.level.upper(), logging.INFO)
    
    # 配置根日志器
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 如果配置了日志文件，添加文件处理器
    if config.logging.file:
        log_path = Path(config.logging.file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logging.getLogger().addHandler(file_handler)


class VoiceInputer:
    """语音输入控制器"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化语音输入控制器
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        self.config_manager = ConfigManager(config_path)
        self.config = self.config_manager.config
        
        # 设置日志
        setup_logging(self.config)
        self.logger = logging.getLogger(__name__)
        
        # 初始化组件
        self.asr_service: Optional[ASRService] = None
        self.audio_recorder: Optional[AudioRecorder] = None
        self.hotkey_listener: Optional[HotkeyListener] = None
        self.text_injector: Optional[TextInjector] = None
        self.llm_enhancer: Optional[LLMEnhancer] = None
        self.notifier: Optional[Notifier] = None
        
        # 状态
        self._is_running = False
        self._is_recording = False
        self._processing_lock = threading.Lock()
    
    def initialize(self):
        """初始化所有组件"""
        self.logger.info("正在初始化 AI Voice Inputer...")
        
        # 初始化通知器
        self.notifier = NotifierFactory.get_instance(
            enabled=self.config.notification.enabled,
            method=self.config.notification.method
        )
        
        # 初始化 ASR 服务
        self.logger.info("正在加载语音识别模型...")
        self.asr_service = ASRServiceFactory.get_instance(
            model_name=self.config.asr.model,
            device=self.config.asr.device,
            compute_type=self.config.asr.compute_type,
            language=self.config.asr.language,
            vad_enabled=self.config.asr.vad.enabled,
            vad_threshold=self.config.asr.vad.silence_threshold,
            min_speech_duration=self.config.asr.vad.min_speech_duration
        )
        
        # 初始化音频录制器
        audio_config = AudioConfig(
            sample_rate=self.config.audio.sample_rate,
            channels=self.config.audio.channels,
            chunk_duration_ms=self.config.audio.chunk_duration_ms
        )
        self.audio_recorder = AudioRecorderManager.get_instance(audio_config)
        
        # 初始化文字注入器
        self.text_injector = TextInjectorFactory.create(
            method=self.config.input.method,
            delay_ms=self.config.input.delay_ms
        )
        
        # 初始化 LLM 增强器 (如果启用)
        if self.config.llm.enabled:
            llm_config = LLMConfig(
                enabled=self.config.llm.enabled,
                api_url=self.config.llm.api_url,
                model=self.config.llm.model,
                api_key=self.config.llm.api_key,
                timeout=self.config.llm.timeout,
                prompt=self.config.llm.prompt
            )
            self.llm_enhancer = LLMEnhancerFactory.create(llm_config)
            self.logger.info("LLM 增强已启用")
        
        # 初始化热键监听器
        self.hotkey_listener = HotkeyManager.create(
            hotkeys=self.config.hotkey.keys,
            on_activate=self._on_hotkey_activate,
            on_deactivate=self._on_hotkey_deactivate
        )
        
        self.logger.info("初始化完成")
    
    def _on_hotkey_activate(self):
        """热键激活回调"""
        with self._processing_lock:
            if self._is_recording:
                return
            
            self._is_recording = True
            self.logger.info("开始录音")
            
            if self.notifier:
                self.notifier.notify_recording_start()
            
            self.audio_recorder.start_recording()
    
    def _on_hotkey_deactivate(self):
        """热键释放回调"""
        with self._processing_lock:
            if not self._is_recording:
                return
            
            self._is_recording = False
            self.logger.info("停止录音，开始处理")
            
            if self.notifier:
                self.notifier.notify_recording_stop()
        
        # 在新线程中处理，避免阻塞
        threading.Thread(target=self._process_audio).start()
    
    def _process_audio(self):
        """处理录制的音频"""
        try:
            # 获取录制的音频
            audio = self.audio_recorder.stop_recording()
            
            if len(audio) == 0:
                self.logger.warning("没有录制到音频")
                return
            
            # 转录
            self.logger.info("正在识别...")
            result = self.asr_service.transcribe(
                audio,
                sample_rate=self.config.audio.sample_rate
            )
            
            text = result.text
            self.logger.info(f"识别结果: {text}")
            
            if not text.strip():
                self.logger.warning("识别结果为空")
                return
            
            # LLM 增强 (如果启用)
            if self.llm_enhancer and self.config.llm.enabled:
                self.logger.info("正在进行 LLM 增强...")
                text = self.llm_enhancer.enhance(text)
                self.logger.info(f"增强结果: {text}")
            
            # 输入文字
            self.logger.info("正在输入文字...")
            success = self.text_injector.inject(text)
            
            if success:
                if self.notifier:
                    self.notifier.notify_transcription_done(text)
                self.logger.info("输入完成")
            else:
                if self.notifier:
                    self.notifier.notify_error("文字输入失败")
                self.logger.error("文字输入失败")
                
        except Exception as e:
            self.logger.error(f"处理音频时出错: {e}", exc_info=True)
            if self.notifier:
                self.notifier.notify_error(str(e))
    
    def start(self):
        """启动服务"""
        if self._is_running:
            return
        
        self.logger.info("启动 AI Voice Inputer...")
        
        # 启动音频流
        self.audio_recorder.start_stream()
        
        # 启动热键监听
        self.hotkey_listener.start()
        
        self._is_running = True
        
        hotkeys = ' + '.join(self.config.hotkey.keys).upper()
        self.logger.info(f"服务已启动，按住 {hotkeys} 开始语音输入")
        
        if self.notifier:
            self.notifier.notify(
                "AI Voice Inputer",
                f"✅ 服务已启动\n按住 {hotkeys} 开始语音输入",
                timeout=3000
            )
    
    def stop(self):
        """停止服务"""
        if not self._is_running:
            return
        
        self.logger.info("停止 AI Voice Inputer...")
        
        self._is_running = False
        
        # 停止热键监听
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        
        # 停止音频流
        if self.audio_recorder:
            self.audio_recorder.stop_stream()
        
        self.logger.info("服务已停止")
    
    def run(self):
        """运行服务（阻塞）"""
        # X11 环境检查: DISPLAY 不可用时热键和文字输入都无法工作
        if not X_DISPLAY_AVAILABLE:
            print(
                "错误: 无法连接 X11 显示器 (DISPLAY 不可用)\n"
                "  请确认在图形界面会话中运行, 例如:\n"
                "    ./run.sh\n"
                "  如使用 systemd 自启, 需要保证服务能拿到正确的 "
                "DISPLAY/XAUTHORITY 环境变量。",
                file=sys.stderr
            )
            raise SystemExit(1)
        
        self.initialize()
        self.start()
        
        # 设置信号处理
        def signal_handler(sig, frame):
            self.logger.info("收到退出信号")
            self.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 保持运行
        try:
            self.hotkey_listener.join()
        except KeyboardInterrupt:
            self.stop()


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='AI Voice Inputer - Ubuntu AI 语音输入法'
    )
    parser.add_argument(
        '-c', '--config',
        help='配置文件路径',
        default=None
    )
    parser.add_argument(
        '--debug',
        help='启用调试模式',
        action='store_true'
    )
    
    args = parser.parse_args()
    
    # 调试模式
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    
    # 创建并运行
    inputer = VoiceInputer(config_path=args.config)
    inputer.run()


if __name__ == '__main__':
    main()
