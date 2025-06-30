import os
import logging
from typing import Optional, Tuple
import asyncio
import concurrent.futures
import tempfile
import wave
import numpy as np

import whisper
import pyttsx3

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load Whisper model once to reuse
_whisper_model = None
_tts_engine = None

def load_whisper_model(model_name: str = "base") -> whisper.Whisper:
    """Lazily load the Whisper model"""
    global _whisper_model
    if _whisper_model is None:
        logger.info(f"Loading Whisper model: {model_name}")
        _whisper_model = whisper.load_model(model_name)
    return _whisper_model

def get_tts_engine() -> pyttsx3.Engine:
    """Lazily load and configure TTS engine"""
    global _tts_engine
    if _tts_engine is None:
        logger.info("Initializing TTS engine")
        _tts_engine = pyttsx3.init()
        # Configure TTS properties
        _tts_engine.setProperty('rate', 160)
        _tts_engine.setProperty('volume', 0.9)
        # Set better quality voice if available
        voices = _tts_engine.getProperty('voices')
        if voices:
            # Try to set a higher quality voice
            for voice in voices:
                if "premium" in voice.name.lower() or "high" in voice.name.lower():
                    _tts_engine.setProperty('voice', voice.id)
                    break
    return _tts_engine

async def transcribe_audio(file_path: str, model_name: str = "base") -> Optional[str]:
    """Transcribe audio using local Whisper model asynchronously"""
    try:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
            
        model = load_whisper_model(model_name)
        
        # Run transcription in thread pool to avoid blocking
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(model.transcribe, file_path)
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: future.result()
            )
            
        transcription = result.get("text", "").strip()
        if not transcription:
            logger.warning("Transcription resulted in empty text")
            return None
            
        logger.info(f"Transcription successful: {transcription}")
        return transcription
        
    except Exception as e:
        logger.error(f"Transcription failed: {str(e)}")
        return None

async def speak_text(text: str) -> bool:
    """Speak the given text using text-to-speech asynchronously"""
    try:
        if not text:
            raise ValueError("Cannot speak empty text")
            
        engine = get_tts_engine()
        
        def speak():
            engine.say(text)
            engine.runAndWait()
            
        # Run TTS in thread pool to avoid blocking
        with concurrent.futures.ThreadPoolExecutor() as executor:
            await asyncio.get_event_loop().run_in_executor(executor, speak)
            
        logger.info("Text spoken successfully")
        return True
        
    except Exception as e:
        logger.error(f"TTS failed: {str(e)}")
        return False

async def create_audio_response(text: str) -> Optional[str]:
    """Create an audio file from text and return the file path"""
    try:
        if not text:
            raise ValueError("Cannot create audio from empty text")
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)
            
        # Create audio file path
        timestamp = int(asyncio.get_event_loop().time() * 1000)
        audio_file = os.path.join(output_dir, f"response_{timestamp}.wav")
        
        def generate_audio():
            try:
                # Create a fresh engine instance for file generation
                # This avoids conflicts with the global engine
                file_engine = pyttsx3.init()
                
                # Configure the file engine with same settings
                file_engine.setProperty('rate', 160)
                file_engine.setProperty('volume', 0.9)
                
                # Set voice if available
                voices = file_engine.getProperty('voices')
                if voices:
                    for voice in voices:
                        if "premium" in voice.name.lower() or "high" in voice.name.lower():
                            file_engine.setProperty('voice', voice.id)
                            break
                
                file_engine.save_to_file(text, audio_file)
                file_engine.runAndWait()
                
                # Clean up the engine
                try:
                    file_engine.stop()
                except:
                    pass  # Some engines don't support stop()
                
                if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
                    logger.info(f"Successfully created audio file: {audio_file}")
                    return audio_file
                else:
                    raise RuntimeError(f"Failed to create audio file at {audio_file} or file is empty")
                    
            except Exception as e:
                logger.error(f"Error generating audio: {str(e)}")
                raise
        
        # Generate audio synchronously to avoid threading issues with pyttsx3
        # pyttsx3 can have issues when used across different threads
        result_file = generate_audio()
        
        return result_file
        
    except Exception as e:
        logger.error(f"Error creating audio response: {str(e)}")
        return None

# Alternative async version that creates the file synchronously
async def create_audio_response_alt(text: str) -> Optional[str]:
    """Alternative implementation that runs file generation synchronously"""
    try:
        if not text:
            raise ValueError("Cannot create audio from empty text")
        
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)
            
        # Create audio file path
        timestamp = int(asyncio.get_event_loop().time() * 1000)
        audio_file = os.path.join(output_dir, f"response_{timestamp}.wav")
        
        # Generate audio synchronously (like your working test)
        engine = pyttsx3.init()
        engine.setProperty('rate', 160)
        engine.setProperty('volume', 0.9)
        
        engine.save_to_file(text, audio_file)
        engine.runAndWait()
        
        if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
            logger.info(f"Successfully created audio file: {audio_file}")
            return audio_file
        else:
            raise RuntimeError(f"Failed to create audio file at {audio_file} or file is empty")
        
    except Exception as e:
        logger.error(f"Error creating audio response: {str(e)}")
        return None

# Optional test runner
if __name__ == "__main__":
    import sys
    
    async def test():
        if len(sys.argv) < 2:
            print("Usage: python voice_model.py path_to_audio.wav")
            exit(1)
            
        audio_path = sys.argv[1]
        
        print("🔊 Transcribing audio...")
        transcript = await transcribe_audio(audio_path)
        
        if transcript:
            print("✅ Transcription:", transcript)
            print("🗣️ Speaking the response...")
            await speak_text(f"You said: {transcript}")
            
            print("💾 Creating audio file...")
            audio_file = await create_audio_response(f"You said: {transcript}")
            if audio_file:
                print(f"✅ Audio file created: {audio_file}")
            else:
                print("❌ Trying alternative method...")
                audio_file = await create_audio_response_alt(f"You said: {transcript}")
                if audio_file:
                    print(f"✅ Audio file created with alternative method: {audio_file}")
        else:
            print("❌ Transcription failed.")
    
    asyncio.run(test())