"""
JARVIS 语音识别模块 (Ears)
使用 Whisper 进行语音转文字

Author: gngdingghuan
"""

import asyncio
from typing import Optional, Callable
from pathlib import Path
import tempfile
import wave
import io

from config import get_config
from utils.logger import log
from utils.compat import to_thread

# NumPy - 语音识别需要
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

# 音频录制
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False

# Whisper 语音识别
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False


class Ears:
    """
    语音识别模块
    - 录音（sounddevice）
    - VAD 语音活动检测
    - Whisper 语音转文字
    """
    
    SAMPLE_RATE = 16000  # Whisper 需要 16kHz
    CHANNELS = 1
    
    def __init__(self, model_name: Optional[str] = None):
        """
        初始化语音识别
        
        Args:
            model_name: Whisper 模型名称 (tiny, base, small, medium, large)
        """
        self.config = get_config().voice
        self.model_name = model_name or self.config.whisper_model
        
        self._model = None
        self._is_listening = False
        self._audio_buffer = []
        
        # VAD 配置
        self.vad_threshold = self.config.vad_threshold
        self.silence_duration = self.config.silence_duration
        
        if not SOUNDDEVICE_AVAILABLE:
            log.warning("sounddevice 未安装，录音功能不可用")
        
        if not WHISPER_AVAILABLE:
            log.warning("whisper 未安装，语音识别功能不可用")
        else:
            self._load_model()
    
    def _load_model(self):
        """加载 Whisper 模型"""
        try:
            log.info(f"正在加载 Whisper 模型: {self.model_name}...")
            self._model = whisper.load_model(self.model_name)
            log.info("Whisper 模型加载完成")
        except Exception as e:
            log.error(f"Whisper 模型加载失败: {e}")
            self._model = None
    
    def is_available(self) -> bool:
        """检查语音识别是否可用"""
        return NUMPY_AVAILABLE and SOUNDDEVICE_AVAILABLE and WHISPER_AVAILABLE and self._model is not None
    
    async def listen(self, timeout: float = 10.0) -> Optional[str]:
        """
        录音并识别
        
        Args:
            timeout: 最大录音时间（秒）
            
        Returns:
            识别的文本，失败返回 None
        """
        if not self.is_available():
            log.warning("语音识别不可用")
            return None
        
        log.info("开始录音...")
        
        try:
            # 录音
            audio_data = await self._record_with_vad(timeout)
            
            if audio_data is None or len(audio_data) < self.SAMPLE_RATE * 0.5:
                log.info("录音太短，忽略")
                return None
            
            # 识别
            text = await self._transcribe(audio_data)
            
            return text.strip() if text else None
            
        except Exception as e:
            log.error(f"语音识别失败: {e}")
            return None
    
    async def _record_with_vad(self, timeout: float) -> Optional['np.ndarray']:
        """
        带 VAD 的录音
        检测到静音后自动停止
        """
        if not NUMPY_AVAILABLE:
            log.warning("NumPy 未安装，录音功能不可用")
            return None
        audio_chunks = []
        silence_count = 0
        max_silence = int(self.silence_duration * self.SAMPLE_RATE / 1024)  # 静音帧数
        
        # 每次录制 1024 帧
        chunk_duration = 1024 / self.SAMPLE_RATE
        max_chunks = int(timeout / chunk_duration)
        
        def audio_callback(indata, frames, time, status):
            if status:
                log.warning(f"录音状态: {status}")
            audio_chunks.append(indata.copy())
        
        try:
            stream = sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                callback=audio_callback,
                blocksize=1024,
            )
            
            with stream:
                for i in range(max_chunks):
                    await asyncio.sleep(chunk_duration)
                    
                    # 简单的 VAD：检查音量
                    if len(audio_chunks) > 0:
                        current_chunk = audio_chunks[-1]
                        volume = np.abs(current_chunk).mean() if NUMPY_AVAILABLE else 0
                        
                        if volume < 0.01:  # 静音阈值
                            silence_count += 1
                        else:
                            silence_count = 0
                        
                        # 检测到足够长的静音，停止录音
                        if silence_count >= max_silence and len(audio_chunks) > max_silence:
                            log.debug(f"检测到静音，停止录音")
                            break
            
            if len(audio_chunks) == 0:
                return None
            
            # 合并音频
            audio_data = np.concatenate(audio_chunks) if NUMPY_AVAILABLE else None
            return audio_data.flatten() if audio_data is not None else None
            
        except Exception as e:
            log.error(f"录音失败: {e}")
            return None
    
    async def _transcribe(self, audio_data: 'np.ndarray') -> Optional[str]:
        """
        使用 Whisper 识别音频
        """
        if self._model is None or not NUMPY_AVAILABLE:
            return None
        
        try:
            # Whisper 需要 float32，范围 [-1, 1]
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
            
            # 确保范围正确
            if np.abs(audio_data).max() > 1.0:
                audio_data = audio_data / np.abs(audio_data).max()
            
            # 运行识别
            result = await to_thread(
                self._model.transcribe,
                audio_data,
                language="zh",
                fp16=False,
            )
            
            text = result.get("text", "")
            log.info(f"语音识别结果: {text}")
            
            return text
            
        except Exception as e:
            log.error(f"Whisper 识别失败: {e}")
            return None
    
    async def listen_continuous(self, callback: Callable[[str], None], stop_event: asyncio.Event):
        """
        持续监听模式
        
        Args:
            callback: 识别到文本时的回调函数
            stop_event: 停止事件
        """
        log.info("开始持续监听...")
        
        while not stop_event.is_set():
            try:
                text = await self.listen(timeout=5.0)
                if text:
                    callback(text)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"持续监听错误: {e}")
                await asyncio.sleep(1)
        
        log.info("停止持续监听")
    
    def get_audio_devices(self) -> list:
        """获取可用的音频输入设备"""
        if not SOUNDDEVICE_AVAILABLE:
            return []
        
        try:
            devices = sd.query_devices()
            return [
                {"id": i, "name": d["name"], "channels": d["max_input_channels"]}
                for i, d in enumerate(devices)
                if d["max_input_channels"] > 0
            ]
        except:
            return []
