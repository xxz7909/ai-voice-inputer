"""
ASR (语音识别) 服务模块
使用 faster-whisper 进行高效的语音转文字
"""

import numpy as np
from typing import Optional, Tuple, List, Generator
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """转录结果"""
    text: str
    language: str
    segments: List[dict]
    duration: float


class ASRService:
    """语音识别服务"""
    
    def __init__(
        self,
        model_name: str = "medium",
        device: str = "auto",
        compute_type: str = "int8",
        language: str = "zh"
    ):
        """
        初始化 ASR 服务
        
        Args:
            model_name: 模型名称 (tiny, base, small, medium, large-v3)
            device: 设备 (auto, cpu, cuda)
            compute_type: 计算类型 (int8, float16, float32)
            language: 语言代码
        """
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.model = None
        
        self._load_model()
    
    def _load_model(self):
        """加载 Whisper 模型"""
        try:
            from faster_whisper import WhisperModel
            
            logger.info(f"正在加载 Whisper 模型: {self.model_name}")
            logger.info(f"设备: {self.device}, 计算类型: {self.compute_type}")
            
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type
            )
            
            logger.info("Whisper 模型加载完成")
            
        except Exception as e:
            logger.error(f"加载 Whisper 模型失败: {e}")
            raise
    
    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int = 16000
    ) -> TranscriptionResult:
        """
        转录音频
        
        Args:
            audio: 音频数据 (numpy 数组)
            sample_rate: 采样率
        
        Returns:
            TranscriptionResult: 转录结果
        """
        if self.model is None:
            raise RuntimeError("模型未加载")
        
        # 确保音频是正确的格式
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        
        # 如果是立体声，转换为单声道
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        
        # 归一化到 [-1, 1] 范围
        max_val = np.abs(audio).max()
        if max_val > 0:
            if max_val > 1.0:
                # 可能是 int16 格式的数据
                audio = audio / 32768.0
            # 确保音量足够（避免太小被 VAD 过滤）
            audio = audio / max(np.abs(audio).max(), 1e-6)
        
        # 打印音频信息用于调试
        logger.debug(f"音频长度: {len(audio)}, 最大值: {np.abs(audio).max():.4f}")
        
        duration = len(audio) / sample_rate
        
        try:
            segments, info = self.model.transcribe(
                audio,
                language=self.language,
                beam_size=5,
                best_of=5,
                temperature=0.0,
                condition_on_previous_text=True,
                vad_filter=False,  # 先禁用 VAD，避免误过滤
            )
            
            # 收集所有片段
            text_parts = []
            segment_list = []
            
            for segment in segments:
                text_parts.append(segment.text)
                segment_list.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text,
                })
            
            full_text = ''.join(text_parts).strip()
            
            return TranscriptionResult(
                text=full_text,
                language=info.language if hasattr(info, 'language') else self.language,
                segments=segment_list,
                duration=duration
            )
            
        except Exception as e:
            logger.error(f"转录失败: {e}")
            raise
    
    def transcribe_stream(
        self,
        audio_chunks: Generator[np.ndarray, None, None],
        sample_rate: int = 16000,
        chunk_duration: float = 0.5
    ) -> Generator[str, None, None]:
        """
        流式转录音频
        
        Args:
            audio_chunks: 音频数据块生成器
            sample_rate: 采样率
            chunk_duration: 每个块的时长 (秒)
        
        Yields:
            str: 转录的文本片段
        """
        buffer = np.array([], dtype=np.float32)
        min_chunk_size = int(sample_rate * chunk_duration)
        
        for chunk in audio_chunks:
            # 添加到缓冲区
            if chunk.dtype != np.float32:
                chunk = chunk.astype(np.float32)
            if len(chunk.shape) > 1:
                chunk = chunk.mean(axis=1)
            
            buffer = np.concatenate([buffer, chunk.flatten()])
            
            # 当缓冲区足够大时进行转录
            if len(buffer) >= min_chunk_size:
                result = self.transcribe(buffer, sample_rate)
                if result.text:
                    yield result.text
                buffer = np.array([], dtype=np.float32)
        
        # 处理剩余的音频
        if len(buffer) > 0:
            result = self.transcribe(buffer, sample_rate)
            if result.text:
                yield result.text


class ASRServiceFactory:
    """ASR 服务工厂"""
    
    _instance: Optional[ASRService] = None
    
    @classmethod
    def get_instance(
        cls,
        model_name: str = "medium",
        device: str = "auto",
        compute_type: str = "int8",
        language: str = "zh",
        force_reload: bool = False
    ) -> ASRService:
        """
        获取 ASR 服务单例
        
        Args:
            model_name: 模型名称
            device: 设备
            compute_type: 计算类型
            language: 语言
            force_reload: 是否强制重新加载
        
        Returns:
            ASRService: ASR 服务实例
        """
        if cls._instance is None or force_reload:
            cls._instance = ASRService(
                model_name=model_name,
                device=device,
                compute_type=compute_type,
                language=language
            )
        return cls._instance
