"""
JARVIS TTS 语音合成模块
使用 Edge-TTS 提供高质量语音输出

Author: gngdingghuan
"""

import asyncio
import tempfile
import os
from pathlib import Path
from typing import Optional

from config import get_config
from utils.logger import log

# Edge-TTS
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

# Pygame 用于播放音频
try:
    import pygame
    pygame.mixer.init()
    PYGAME_AVAILABLE = True
except:
    PYGAME_AVAILABLE = False


class TTS:
    """
    语音合成模块
    使用 Edge-TTS 生成语音，Pygame 播放
    """
    
    # 常用中文语音
    VOICES = {
        "yunxi": "zh-CN-YunxiNeural",      # 男声，标准
        "xiaoxiao": "zh-CN-XiaoxiaoNeural", # 女声，温柔
        "yunyang": "zh-CN-YunyangNeural",   # 男声，新闻
        "xiaoyi": "zh-CN-XiaoyiNeural",     # 女声，活泼
    }
    
    def __init__(self, voice: Optional[str] = None):
        """
        初始化 TTS
        
        Args:
            voice: 语音名称或语音 ID
        """
        self.config = get_config().voice
        
        # 设置语音
        if voice:
            self.voice = self.VOICES.get(voice, voice)
        else:
            self.voice = self.config.tts_voice
        
        self.rate = self.config.tts_rate
        self.volume = self.config.tts_volume
        
        # 临时文件目录
        self._temp_dir = Path(tempfile.gettempdir()) / "jarvis_tts"
        self._temp_dir.mkdir(exist_ok=True)
        
        # 播放状态
        self._is_speaking = False
        
        if not EDGE_TTS_AVAILABLE:
            log.warning("edge-tts 未安装，TTS 功能不可用")
        if not PYGAME_AVAILABLE:
            log.warning("pygame 未安装，音频播放功能不可用")
        
        log.info(f"TTS 初始化完成，语音: {self.voice}")
    
    async def speak(self, text: str, wait: bool = True) -> bool:
        """
        语音播放文本
        
        Args:
            text: 要播放的文本
            wait: 是否等待播放完成
            
        Returns:
            是否成功
        """
        if not EDGE_TTS_AVAILABLE or not PYGAME_AVAILABLE:
            log.warning(f"TTS 不可用，文本: {text}")
            return False
        
        if not text or not text.strip():
            return True
        
        try:
            self._is_speaking = True
            
            # 生成语音文件
            audio_file = self._temp_dir / f"tts_{hash(text)}.mp3"
            
            communicate = edge_tts.Communicate(
                text=text,
                voice=self.voice,
                rate=self.rate,
                volume=self.volume
            )
            
            await communicate.save(str(audio_file))
            
            # 播放
            if wait:
                await self._play_audio(audio_file)
            else:
                asyncio.create_task(self._play_audio(audio_file))
            
            return True
            
        except Exception as e:
            log.error(f"TTS 失败: {e}")
            return False
        finally:
            self._is_speaking = False
    
    async def _play_audio(self, audio_file: Path):
        """播放音频文件"""
        try:
            pygame.mixer.music.load(str(audio_file))
            pygame.mixer.music.play()
            
            # 等待播放完成
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
            
            # 清理临时文件
            try:
                audio_file.unlink()
            except:
                pass
                
        except Exception as e:
            log.error(f"音频播放失败: {e}")
    
    async def speak_stream(self, text_generator) -> bool:
        """
        流式语音播放
        边生成文本边播放（用于 LLM 流式输出）
        
        Args:
            text_generator: 文本生成器
            
        Returns:
            是否成功
        """
        if not EDGE_TTS_AVAILABLE or not PYGAME_AVAILABLE:
            return False
        
        buffer = ""
        sentence_endings = ("。", "！", "？", ".", "!", "?", "\n")
        
        try:
            async for chunk in text_generator:
                buffer += chunk
                
                # 检查是否有完整句子
                for ending in sentence_endings:
                    if ending in buffer:
                        idx = buffer.rfind(ending)
                        sentence = buffer[:idx + 1]
                        buffer = buffer[idx + 1:]
                        
                        # 播放句子
                        await self.speak(sentence.strip())
                        break
            
            # 播放剩余内容
            if buffer.strip():
                await self.speak(buffer.strip())
            
            return True
            
        except Exception as e:
            log.error(f"流式 TTS 失败: {e}")
            return False
    
    def stop(self):
        """停止播放"""
        try:
            if PYGAME_AVAILABLE:
                pygame.mixer.music.stop()
            self._is_speaking = False
        except:
            pass
    
    def is_speaking(self) -> bool:
        """是否正在播放"""
        return self._is_speaking
    
    def set_voice(self, voice: str):
        """设置语音"""
        self.voice = self.VOICES.get(voice, voice)
        log.info(f"TTS 语音已切换为: {self.voice}")
    
    def set_rate(self, rate: str):
        """设置语速，如 '+10%' 或 '-20%'"""
        self.rate = rate
    
    def set_volume(self, volume: str):
        """设置音量，如 '+10%' 或 '-20%'"""
        self.volume = volume
    
    @staticmethod
    async def list_voices(language: str = "zh") -> list:
        """列出可用语音"""
        if not EDGE_TTS_AVAILABLE:
            return []
        
        try:
            voices = await edge_tts.list_voices()
            return [v for v in voices if language in v["Locale"]]
        except:
            return []
