"""
ASR (语音识别) 服务模块
使用 faster-whisper 进行高效的语音转文字
"""

import numpy as np
from typing import Optional, Tuple, List, Generator
from dataclasses import dataclass
import logging
from pathlib import Path

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
    
    # 片段级"非语音"判定阈值, 高于该值的片段会被丢弃 (防止静音/噪声产生幻觉文本)
    NO_SPEECH_THRESHOLD = 0.6
    
    # 响度兜底阈值: VAD 没检出人声但音频能量明显偏高时 (如麦克风过载),
    # 仍然送去识别, 避免把真实语音误判成静音
    LOUD_RMS_THRESHOLD = 0.05
    
    def __init__(
        self,
        model_name: str = "medium",
        device: str = "auto",
        compute_type: str = "int8",
        language: str = "zh",
        vad_enabled: bool = True,
        vad_threshold: float = 0.5,
        min_speech_duration: float = 0.3
    ):
        """
        初始化 ASR 服务
        
        Args:
            model_name: 模型名称 (tiny, base, small, medium, large-v3)
            device: 设备 (auto, cpu, cuda)
            compute_type: 计算类型 (int8, float16, float32)
            language: 语言代码
            vad_enabled: 是否启用 VAD (语音活动检测) 过滤静音
            vad_threshold: VAD 语音判定阈值 (0~1, 越大越严格)
            min_speech_duration: 最小语音长度 (秒), 更短的音频直接跳过
        """
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self.language = language
        self.vad_enabled = vad_enabled
        self.vad_threshold = vad_threshold
        self.min_speech_duration = min_speech_duration
        self.model = None
        
        self._load_model()
    
    def _load_model(self):
        """加载 Whisper 模型"""
        try:
            from faster_whisper import WhisperModel
            
            logger.info(f"正在加载 Whisper 模型: {self.model_name}")
            logger.info(f"设备: {self.device}, 计算类型: {self.compute_type}")
            
            model_path = self._resolve_model_path()
            
            self.model = WhisperModel(
                model_path,
                device=self.device,
                compute_type=self.compute_type
            )
            
            logger.info("Whisper 模型加载完成")
            
        except Exception as e:
            logger.error(f"加载 Whisper 模型失败: {e}")
            raise

    def _resolve_model_path(self) -> str:
        """
        解析模型路径: 优先使用本地缓存, 避免启动时联网检查导致卡死
        
        模型已缓存到本地时直接返回本地目录, 完全不访问网络;
        只有本地没有缓存时才联网下载。
        
        Returns:
            str: 模型目录路径或模型名称
        """
        # 用户直接指定了本地模型目录
        if Path(self.model_name).is_dir():
            return self.model_name
        
        try:
            from faster_whisper.utils import download_model
            
            path = download_model(self.model_name, local_files_only=True)
            logger.info(f"使用本地缓存模型: {path}")
            return path
            
        except Exception as e:
            logger.warning(f"本地未找到模型 {self.model_name} 的缓存: {e}")
            logger.warning(
                "将尝试联网下载模型, 国内网络通常无法访问 huggingface.co, "
                "可执行以下命令使用镜像下载:\n"
                f"  HF_ENDPOINT=https://hf-mirror.com "
                f"python -c \"from faster_whisper.utils import download_model; "
                f"print(download_model('{self.model_name}'))\""
            )
            return self.model_name
    
    def _has_speech(self, audio: np.ndarray) -> bool:
        """
        用 Silero VAD 判断音频中是否真的有人声
        
        这里只做判断, 不裁剪音频: VAD 的分段裁剪会切掉弱读音节甚至整段语音,
        导致识别结果丢字, 因此识别时始终送入完整音频。
        
        Args:
            audio: 单声道 float32 音频
        
        Returns:
            bool: 是否检测到人声
        """
        from faster_whisper.vad import VadOptions, get_speech_timestamps
        
        timestamps = get_speech_timestamps(
            audio,
            VadOptions(
                threshold=self.vad_threshold,
                min_speech_duration_ms=int(self.min_speech_duration * 1000),
                speech_pad_ms=200,
            ),
        )
        return len(timestamps) > 0
    
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
        # 按 dtype 判断量程: 整数格式按自身范围换算到 [-1, 1] 浮点
        if np.issubdtype(audio.dtype, np.integer):
            audio = audio.astype(np.float32) / float(np.iinfo(audio.dtype).max + 1)
        elif audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        
        # 如果是立体声，转换为单声道
        if len(audio.shape) > 1:
            audio = audio.mean(axis=1)
        
        # 麦克风增益偏高时浮点波形可能略微超出 [-1, 1], 削顶即可
        # 注意: 不能按峰值放大音量, 否则环境噪声会被放大成"语音"并触发幻觉文本
        audio = np.clip(audio, -1.0, 1.0)
        
        # 打印音频信息用于调试
        logger.debug(f"音频长度: {len(audio)}, 最大值: {np.abs(audio).max():.4f}")
        
        duration = len(audio) / sample_rate
        
        # 音频过短直接跳过, 避免在空白音频上识别出幻觉文本
        if duration < self.min_speech_duration:
            logger.info(f"音频过短 ({duration:.2f}秒), 跳过识别")
            return TranscriptionResult(
                text='',
                language=self.language,
                segments=[],
                duration=duration
            )
        
        # VAD 门禁: 没检测到人声直接返回, 避免 Whisper 在静音/噪声上产生幻觉文本
        if self.vad_enabled:
            speech_detected = True
            try:
                speech_detected = self._has_speech(audio)
            except Exception as e:
                logger.warning(f"VAD 检测失败, 继续识别: {e}")
            
            if not speech_detected:
                rms = float(np.sqrt(np.mean(np.square(audio)))) if len(audio) else 0.0
                
                if rms < self.LOUD_RMS_THRESHOLD:
                    logger.info(f"未检测到人声 (rms={rms:.4f}), 跳过识别")
                    return TranscriptionResult(
                        text='',
                        language=self.language,
                        segments=[],
                        duration=duration
                    )
                
                logger.warning(
                    f"VAD 未检测到人声但响度偏高 (rms={rms:.4f}), 仍尝试识别"
                )
        
        try:
            segments, info = self.model.transcribe(
                audio,
                language=self.language,
                beam_size=5,
                best_of=5,
                temperature=0.0,
                condition_on_previous_text=False,  # 避免上下文累积导致重复输出
                no_speech_threshold=self.NO_SPEECH_THRESHOLD,
                vad_filter=False,  # 不裁剪音频, 交由上面的 VAD 门禁判断
            )
            
            # 收集所有片段
            text_parts = []
            segment_list = []
            
            for segment in segments:
                # 二次校验: 丢弃被判定为"非语音"的片段
                if segment.no_speech_prob > self.NO_SPEECH_THRESHOLD:
                    logger.debug(
                        f"丢弃非语音片段: {segment.text!r} "
                        f"(no_speech_prob={segment.no_speech_prob:.2f})"
                    )
                    continue
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
        vad_enabled: bool = True,
        vad_threshold: float = 0.5,
        min_speech_duration: float = 0.3,
        force_reload: bool = False
    ) -> ASRService:
        """
        获取 ASR 服务单例
        
        Args:
            model_name: 模型名称
            device: 设备
            compute_type: 计算类型
            language: 语言
            vad_enabled: 是否启用 VAD 过滤静音
            vad_threshold: VAD 语音判定阈值
            min_speech_duration: 最小语音长度 (秒)
            force_reload: 是否强制重新加载
        
        Returns:
            ASRService: ASR 服务实例
        """
        if cls._instance is None or force_reload:
            cls._instance = ASRService(
                model_name=model_name,
                device=device,
                compute_type=compute_type,
                language=language,
                vad_enabled=vad_enabled,
                vad_threshold=vad_threshold,
                min_speech_duration=min_speech_duration
            )
        return cls._instance
