import logging
import time
import tempfile
import wave
import pyaudio
import struct
from typing import Optional
import asyncio
import os

from llm_models.voice_model import (
    transcribe_audio,
    speak_text,
    create_audio_response,
    load_whisper_model,
    get_tts_engine
)

logger = logging.getLogger(__name__)

class VoiceManager:
    """Comprehensive voice processing and recording utility"""
    
    def __init__(self):
        try:
            load_whisper_model()
            get_tts_engine()
            self.audio = pyaudio.PyAudio()
            self.is_recording = False
            self.recording_started = False
            self.silence_start = None
            self.frames = []
            self.stream = None
            self.chunk = 1024
            self.format = pyaudio.paInt16
            self.channels = 1
            self.rate = 16000
            self.silence_threshold = 500
            self.silence_duration = 2.0
            logger.info("Voice components initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing voice components: {e}")
            self.audio = None
            raise
    
    async def transcribe_audio_file(self, audio_file_path: str) -> Optional[str]:
        """Transcribe audio file to text"""
        try:
            if not os.path.exists(audio_file_path):
                logger.error(f"Audio file not found: {audio_file_path}")
                return None
                
            file_size = os.path.getsize(audio_file_path)
            logger.info(f"Transcribing audio file: {audio_file_path} (size: {file_size} bytes)")
            
            if file_size < 1000:  # Less than 1KB
                logger.warning("Audio file too small for transcription")
                return None
                
            result = await transcribe_audio(audio_file_path)
            logger.info(f"Transcription result: '{result}'")
            return result
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None
    
    async def create_audio_response(self, text: str) -> Optional[str]:
        """Create audio response from text"""
        try:
            return await create_audio_response(text)
        except Exception as e:
            logger.error(f"Error creating audio response: {e}")
            return None
    
    async def speak_text_async(self, text: str) -> bool:
        """Speak text asynchronously"""
        try:
            return await speak_text(text)
        except Exception as e:
            logger.error(f"Error speaking text: {e}")
            return False
    
    def get_audio_level(self, data: bytes) -> int:
        """Get audio level from byte data"""
        try:
            if len(data) < 2:
                return 0
            shorts = struct.unpack('<' + ('h' * (len(data) // 2)), data)
            return max(abs(i) for i in shorts) if shorts else 0
        except Exception as e:
            logger.error(f"Error getting audio level: {e}")
            return 0
    
    def start_recording_stream(self):
        """Start the audio recording stream"""
        try:
            if not self.audio:
                raise Exception("Audio system not initialized")
                
            self.frames = []
            self.is_recording = True
            self.recording_started = False
            self.silence_start = None
            
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk,
                stream_callback=None  # We'll read manually
            )
            
            logger.info("🎤 Recording stream started - listening for voice...")
            return True
            
        except Exception as e:
            logger.error(f"Error starting recording stream: {e}")
            self.stop_recording()
            return False
    
    async def process_audio_chunk(self, chunk_data: bytes):
        """Process incoming audio chunk"""
        try:
            if not self.is_recording:
                return
                
            self.frames.append(chunk_data)
            audio_level = self.get_audio_level(chunk_data)
            
            if audio_level > self.silence_threshold:
                if not self.recording_started:
                    self.recording_started = True
                    logger.info("🗣️ Voice detected, recording...")
                self.silence_start = None
            else:
                if self.recording_started:
                    if self.silence_start is None:
                        self.silence_start = time.time()
                    elif time.time() - self.silence_start > self.silence_duration:
                        logger.info("🔇 Silence detected, processing recording...")
                        await self.finalize_recording()
                        
        except Exception as e:
            logger.error(f"Error processing audio chunk: {e}")
    
    async def record_audio(self, max_duration: int = 30) -> Optional[str]:
        """Record audio with voice activity detection"""
        try:
            if not self.start_recording_stream():
                return None
                
            logger.info("🎤 Listening... Speak now!")
            start_time = time.time()
            
            while self.is_recording and (time.time() - start_time) < max_duration:
                try:
                    if self.stream and self.stream.is_active():
                        data = self.stream.read(self.chunk, exception_on_overflow=False)
                        await self.process_audio_chunk(data)
                    
                    await asyncio.sleep(0.01)  # Small delay to prevent blocking
                    
                except Exception as e:
                    logger.error(f"Error reading audio data: {e}")
                    break
            
            # If we reach here due to timeout, finalize recording
            if self.is_recording:
                logger.info("⏰ Recording timeout reached")
                return await self.finalize_recording()
            
            return None
            
        except Exception as e:
            logger.error(f"Error in record_audio: {e}")
            self.stop_recording()
            return None
    
    async def finalize_recording(self) -> Optional[str]:
        """Finalize recording and save to file"""
        try:
            self.stop_recording()
            
            if not self.frames:
                logger.warning("No audio frames recorded")
                return None
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            temp_path = temp_file.name
            temp_file.close()
            
            # Write audio data to file
            with wave.open(temp_path, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(self.frames))
            
            # Check file size
            file_size = os.path.getsize(temp_path)
            logger.info(f"Audio saved to: {temp_path} (size: {file_size} bytes)")
            
            if file_size < 1000:
                logger.warning("Recorded audio file is too small")
                try:
                    os.unlink(temp_path)
                except:
                    pass
                return None
            
            return temp_path
            
        except Exception as e:
            logger.error(f"Error finalizing recording: {e}")
            return None
    
    def stop_recording(self):
        """Stop recording and clean up stream"""
        try:
            self.is_recording = False
            self.recording_started = False
            self.silence_start = None
            
            if self.stream:
                try:
                    if self.stream.is_active():
                        self.stream.stop_stream()
                    self.stream.close()
                except Exception as e:
                    logger.error(f"Error stopping stream: {e}")
                finally:
                    self.stream = None
                    
            logger.info("🔇 Recording stopped")
            
        except Exception as e:
            logger.error(f"Error in stop_recording: {e}")
    
    def cleanup(self):
        """Clean up all resources"""
        try:
            self.stop_recording()
            if self.audio:
                self.audio.terminate()
                self.audio = None
        except Exception as e:
            logger.error(f"Error in cleanup: {e}")
    
    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.cleanup()
        except:
            pass