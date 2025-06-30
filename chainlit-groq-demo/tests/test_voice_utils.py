import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import os
import pytest
from utils.voice_utils import VoiceManager
import pyttsx3

@pytest.mark.asyncio
async def test_transcribe_audio(tmp_path):
    # Create a short test audio file using pyttsx3
    test_text = "Hello, this is a test."
    audio_path = tmp_path / "test.wav"
    engine = pyttsx3.init()
    engine.save_to_file(test_text, str(audio_path))
    engine.runAndWait()
    vm = VoiceManager()
    result = await vm.transcribe_audio_file(str(audio_path))
    print("Transcription result:", result)
    assert isinstance(result, str)
    assert "hello" in result.lower()
    assert len(result.strip()) > 0

def play_audio_file(audio_file):
    import platform
    if platform.system() == "Linux":
        os.system(f"aplay {audio_file}")
    elif platform.system() == "Darwin":
        os.system(f"afplay {audio_file}")
    elif platform.system() == "Windows":
        os.system(f'start {audio_file}')

@pytest.mark.asyncio
async def test_create_audio_response():
    test_text = "Testing speech synthesis."
    vm = VoiceManager()
    audio_file = await vm.create_audio_response(test_text)
    assert audio_file is not None
    assert os.path.exists(audio_file)
    assert os.path.getsize(audio_file) > 1000
    play_audio_file(audio_file)
