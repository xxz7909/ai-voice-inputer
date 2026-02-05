"""
音频录制模块
使用 sounddevice 进行实时音频采集
"""

import numpy as np
import sounddevice as sd
import queue
import threading
from typing import Optional, Callable
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class AudioConfig:
    """音频配置"""
    sample_rate: int = 16000
    channels: int = 1
    chunk_duration_ms: int = 100
    dtype: str = 'float32'


class AudioRecorder:
    """音频录制器"""
    
    def __init__(self, config: Optional[AudioConfig] = None):
        """
        初始化音频录制器
        
        Args:
            config: 音频配置
        """
        self.config = config or AudioConfig()
        self.audio_queue: queue.Queue = queue.Queue()
        self.is_recording: bool = False
        self.stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        
        # 计算每个块的帧数
        self.chunk_frames = int(
            self.config.sample_rate * self.config.chunk_duration_ms / 1000
        )
    
    def _audio_callback(self, indata, frames, time, status):
        """音频输入回调函数"""
        if status:
            logger.warning(f"音频状态: {status}")
        
        if self.is_recording:
            # 复制数据到队列
            self.audio_queue.put(indata.copy())
    
    def start_stream(self):
        """启动音频流"""
        if self.stream is not None:
            return
        
        try:
            self.stream = sd.InputStream(
                samplerate=self.config.sample_rate,
                channels=self.config.channels,
                dtype=self.config.dtype,
                blocksize=self.chunk_frames,
                callback=self._audio_callback
            )
            self.stream.start()
            logger.info("音频流已启动")
        except Exception as e:
            logger.error(f"启动音频流失败: {e}")
            raise
    
    def stop_stream(self):
        """停止音频流"""
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
            self.stream = None
            logger.info("音频流已停止")
    
    def start_recording(self):
        """开始录音"""
        with self._lock:
            # 清空队列
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
            
            self.is_recording = True
            logger.info("开始录音")
    
    def stop_recording(self) -> np.ndarray:
        """
        停止录音并返回录制的音频
        
        Returns:
            np.ndarray: 录制的音频数据
        """
        with self._lock:
            self.is_recording = False
            
            # 收集所有录制的音频块
            audio_chunks = []
            while not self.audio_queue.empty():
                try:
                    chunk = self.audio_queue.get_nowait()
                    audio_chunks.append(chunk)
                except queue.Empty:
                    break
            
            if not audio_chunks:
                logger.warning("没有录制到音频数据")
                return np.array([], dtype=np.float32)
            
            # 合并音频块
            audio = np.concatenate(audio_chunks, axis=0).flatten()
            duration = len(audio) / self.config.sample_rate
            logger.info(f"停止录音, 时长: {duration:.2f}秒")
            
            return audio
    
    def get_audio_devices(self) -> dict:
        """获取可用的音频设备"""
        devices = sd.query_devices()
        return {
            'devices': devices,
            'default_input': sd.default.device[0],
            'default_output': sd.default.device[1],
        }
    
    def set_input_device(self, device_id: int):
        """设置输入设备"""
        sd.default.device[0] = device_id
        logger.info(f"设置输入设备: {device_id}")
        
        # 如果流正在运行，重启流
        if self.stream is not None:
            self.stop_stream()
            self.start_stream()


class AudioRecorderManager:
    """音频录制器管理器 (单例)"""
    
    _instance: Optional[AudioRecorder] = None
    
    @classmethod
    def get_instance(cls, config: Optional[AudioConfig] = None) -> AudioRecorder:
        """获取录制器单例"""
        if cls._instance is None:
            cls._instance = AudioRecorder(config)
        return cls._instance
    
    @classmethod
    def reset(cls):
        """重置单例"""
        if cls._instance is not None:
            cls._instance.stop_stream()
            cls._instance = None
