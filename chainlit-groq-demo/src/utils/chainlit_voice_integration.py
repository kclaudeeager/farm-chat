import asyncio
import os
import logging
import time
import numpy as np
from enum import Enum
from typing import Optional
from utils.voice_utils import VoiceManager

logger = logging.getLogger(__name__)

class VoiceState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PROCESSING = "processing"
    ERROR = "error"

class ChainlitVoiceIntegration:
    """Enhanced Chainlit voice integration with comprehensive debugging"""
    
    def __init__(self, cl):
        try:
            self.cl = cl
            self.voice_manager = VoiceManager()
            
            # State management
            self.state = VoiceState.IDLE
            self.state_lock = asyncio.Lock()
            
            # Recording state
            self.recording_task = None
            self.audio_chunks = []
            
            # Built-in audio session
            self._audio_session_active = False
            self._accumulated_audio = bytearray()
            self._last_audio_time = None
            self._first_chunk_received = False
            
            # Audio chunk processing 
            self._chunk_queue = asyncio.Queue(maxsize=1000)
            self._chunk_processor_task = None
            self._processing_chunks = False
            
            # Debug counters
            self._debug_chunk_count = 0
            self._debug_start_time = None
            
            # Adjusted parameters for better detection
            self.silence_threshold = 0.005  # Lower threshold
            self.silence_duration = 1.5     # Shorter silence duration
            self.min_speech_duration = 0.2  # Minimum speech duration
            self.max_recording_duration = 30.0
            self.stream_timeout = 10.0      # Timeout for stream
            self.initial_timeout = 8.0      # Timeout for first chunk
            
            # Voice detection state
            self.voice_detected = False
            self.speech_start_time = None
            self.last_chunk_time = None
            
            logger.info("Voice integration initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing voice integration: {e}")
            self.voice_manager = None
            raise
    
    async def _transition_state(self, new_state: VoiceState):
        """Safely transition between states"""
        async with self.state_lock:
            old_state = self.state
            self.state = new_state
            logger.info(f"State transition: {old_state.value} -> {new_state.value}")
    
    async def _is_state(self, expected_state: VoiceState) -> bool:
        """Check current state safely"""
        async with self.state_lock:
            return self.state == expected_state
    
    async def handle_voice_commands(self, message: str) -> dict:
        """Handle voice-related commands"""
        cmd = message.lower().strip()
        
        try:
            if cmd.startswith("/voice"):
                return await self.toggle_voice_mode("on" in cmd)
            elif cmd.startswith("/auto-speak"):
                return await self.toggle_auto_speak("on" in cmd)
            elif cmd == "/record" or cmd == "/start":
                return await self.start_manual_recording()
            elif cmd == "/stop":
                return await self.stop_recording()
            elif cmd == "/test-audio":
                return await self.test_audio_system()
            elif cmd == "/debug-audio":
                return await self.debug_audio_system()
                
        except Exception as e:
            logger.error(f"Error handling voice command '{cmd}': {e}")
            await self._transition_state(VoiceState.ERROR)
            return {
                "handled": True,
                "message": f"Error processing command: {str(e)}",
                "speak": False
            }
            
        return {"handled": False}
    
    async def debug_audio_system(self) -> dict:
        """Debug audio system status"""
        try:
            debug_info = []
            debug_info.append(f"🔍 **Audio System Debug Info**")
            debug_info.append(f"Current State: {self.state.value}")
            debug_info.append(f"Audio Session Active: {self._audio_session_active}")
            debug_info.append(f"First Chunk Received: {self._first_chunk_received}")
            debug_info.append(f"Chunk Count: {self._debug_chunk_count}")
            debug_info.append(f"Accumulated Audio Size: {len(self._accumulated_audio)} bytes")
            debug_info.append(f"Processing Chunks: {self._processing_chunks}")
            debug_info.append(f"Queue Size: {self._chunk_queue.qsize()}")
            
            # Voice manager status
            if self.voice_manager:
                debug_info.append(f"Voice Manager Available: ✅")
                debug_info.append(f"PyAudio Available: {'✅' if self.voice_manager.audio else '❌'}")
            else:
                debug_info.append(f"Voice Manager Available: ❌")
            
            # Session state
            state = self.cl.user_session.get("state", {})
            debug_info.append(f"Voice Enabled: {state.get('voice_enabled', False)}")
            debug_info.append(f"Auto Speak: {state.get('auto_speak', False)}")
            
            debug_message = "\n".join(debug_info)
            await self.cl.Message(content=debug_message).send()
            
            return {
                "handled": True,
                "message": "Debug info displayed",
                "speak": False
            }
            
        except Exception as e:
            logger.error(f"Error in debug: {e}")
            return {
                "handled": True,
                "message": f"Debug error: {str(e)}",
                "speak": False
            }
    
    async def start_manual_recording(self) -> dict:
        """Start manual recording with proper state management"""
        try:
            if not self.voice_manager:
                return {
                    "handled": True,
                    "message": "❌ Voice system not available",
                    "speak": False
                }
            
            # Check if we can start recording
            if not await self._is_state(VoiceState.IDLE):
                current_state = self.state.value
                return {
                    "handled": True,
                    "message": f"❌ Cannot start recording in {current_state} state. Use '/stop' first.",
                    "speak": False
                }
            
            await self._transition_state(VoiceState.RECORDING)
            
            # Show recording message
            await self.cl.Message(content="🎤 Recording started... Speak now! (Use '/stop' to finish)").send()
            
            # Start recording task
            self.recording_task = asyncio.create_task(self._record_and_process())
            
            return {
                "handled": True,
                "message": "🎤 Recording started",
                "speak": False
            }
            
        except Exception as e:
            logger.error(f"Error starting manual recording: {e}")
            await self._transition_state(VoiceState.ERROR)
            return {
                "handled": True,
                "message": f"❌ Error starting recording: {str(e)}",
                "speak": False
            }
    
    async def stop_recording(self) -> dict:
        """Stop any active recording"""
        try:
            current_state = self.state
            
            if current_state == VoiceState.IDLE:
                return {
                    "handled": True,
                    "message": "❌ Not currently recording",
                    "speak": False
                }
            
            logger.info(f"Stopping recording from state: {current_state.value}")
            
            # Stop built-in audio session
            if self._audio_session_active:
                self._audio_session_active = False
                logger.info("Stopped built-in audio session")
                
            # Stop voice manager recording
            if self.voice_manager:
                self.voice_manager.stop_recording()
            
            # Stop chunk processing
            await self._stop_chunk_processor()
            
            # Wait for recording task to complete
            if self.recording_task and not self.recording_task.done():
                try:
                    await asyncio.wait_for(self.recording_task, timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("Recording task timeout - cancelling")
                    self.recording_task.cancel()
                except Exception as e:
                    logger.error(f"Error waiting for recording task: {e}")
                finally:
                    self.recording_task = None
            
            # Process any accumulated audio
            if len(self._accumulated_audio) > 1024:
                await self._transition_state(VoiceState.PROCESSING)
                await self._process_accumulated_audio()
            
            await self._transition_state(VoiceState.IDLE)
            
            return {
                "handled": True,
                "message": "🔇 Recording stopped",
                "speak": False
            }
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            await self._transition_state(VoiceState.ERROR)
            return {
                "handled": True,
                "message": f"❌ Error stopping recording: {str(e)}",
                "speak": False
            }
    
    async def _record_and_process(self):
        """Background task to record and process audio"""
        try:
            logger.info("Starting background recording task")
            
            # Record audio
            audio_file = await self.voice_manager.record_audio(max_duration=30)
            
            # Check if we're still in recording state
            if not await self._is_state(VoiceState.RECORDING):
                logger.info("Recording was stopped externally")
                return
                
            if audio_file:
                await self._transition_state(VoiceState.PROCESSING)
                await self._process_recorded_audio(audio_file)
            else:
                await self.cl.Message(content="❌ No audio detected or recording failed").send()
                
        except Exception as e:
            logger.error(f"Error in background recording task: {e}")
            await self.cl.Message(content=f"❌ Recording error: {str(e)}").send()
            await self._transition_state(VoiceState.ERROR)
        finally:
            # Ensure we return to idle state
            if await self._is_state(VoiceState.RECORDING) or await self._is_state(VoiceState.PROCESSING):
                await self._transition_state(VoiceState.IDLE)
    
    async def toggle_voice_mode(self, enable: bool) -> dict:
        """Toggle voice mode"""
        try:
            state = self.cl.user_session.get("state", {})
            state["voice_enabled"] = enable
            
            if enable:
                state["auto_speak"] = True
                self.cl.user_session.set("state", state)
                return {
                    "handled": True,
                    "message": "🎤 Voice mode enabled! Click the microphone button to start recording.",
                    "speak": False
                }
            else:
                # Stop any active recording
                if not await self._is_state(VoiceState.IDLE):
                    await self.stop_recording()
                    
                self.cl.user_session.set("state", state)
                return {
                    "handled": True,
                    "message": "🔇 Voice mode disabled.",
                    "speak": False
                }
                
        except Exception as e:
            logger.error(f"Error toggling voice mode: {e}")
            return {
                "handled": True,
                "message": f"❌ Error toggling voice mode: {str(e)}",
                "speak": False
            }
    
    async def toggle_auto_speak(self, enable: bool) -> dict:
        """Toggle automatic speech responses"""
        try:
            state = self.cl.user_session.get("state", {})
            if enable and not state.get("voice_enabled", False):
                return {
                    "handled": True,
                    "message": "Please enable voice mode first with '/voice on'",
                    "speak": False
                }
            
            state["auto_speak"] = enable
            self.cl.user_session.set("state", state)
            
            msg = "🔊 Auto-speak enabled! I'll read my responses." if enable else "🔇 Auto-speak disabled."
            return {
                "handled": True,
                "message": msg,
                "speak": enable
            }
            
        except Exception as e:
            logger.error(f"Error toggling auto-speak: {e}")
            return {
                "handled": True,
                "message": f"❌ Error toggling auto-speak: {str(e)}",
                "speak": False
            }
    
    async def test_audio_system(self) -> dict:
        """Test the audio system"""
        try:
            await self.cl.Message(content="🧪 Testing audio system...").send()
            
            if self.voice_manager and hasattr(self.voice_manager, 'audio') and self.voice_manager.audio:
                await self.cl.Message(content="✅ Audio system initialized").send()
                
                # Test very short recording
                await self.cl.Message(content="🎤 Testing 3-second recording...").send()
                test_audio = await self.voice_manager.record_audio(max_duration=3)
                
                if test_audio:
                    await self.cl.Message(content="✅ Test recording successful").send()
                    try:
                        os.unlink(test_audio)
                    except:
                        pass
                else:
                    await self.cl.Message(content="❌ Test recording failed").send()
                    
                return {"handled": True, "message": "Audio test completed"}
            else:
                await self.cl.Message(content="❌ Audio system not initialized").send()
                return {"handled": True, "message": "Audio system not available"}
                
        except Exception as e:
            logger.error(f"Audio test error: {e}")
            return {"handled": True, "message": f"Audio test failed: {e}"}
    
    
    async def handle_audio_chunk(self, chunk_data: bytes):
        """Handle incoming audio chunks with comprehensive debugging"""
        try:
            self._debug_chunk_count += 1
            
            # Log first few chunks
            if self._debug_chunk_count <= 5:
                logger.info(f"📦 Audio chunk #{self._debug_chunk_count}: {len(chunk_data) if chunk_data else 0} bytes")
            elif self._debug_chunk_count % 50 == 0:  # Log every 50th chunk
                logger.info(f"📦 Audio chunk #{self._debug_chunk_count}: {len(chunk_data) if chunk_data else 0} bytes")
            
            if self._audio_session_active and chunk_data and len(chunk_data) > 0:
                # Mark first chunk received
                if not self._first_chunk_received:
                    self._first_chunk_received = True
                    logger.info(f"✅ First audio chunk received: {len(chunk_data)} bytes")
                
                self.last_chunk_time = time.time()
                
                try:
                    await asyncio.wait_for(
                        self._chunk_queue.put(chunk_data),
                        timeout=0.1
                    )
                except asyncio.TimeoutError:
                    logger.warning(f"⚠️ Chunk queue full - dropping chunk #{self._debug_chunk_count}")
            else:
                if not self._audio_session_active:
                    logger.debug(f"📦 Chunk #{self._debug_chunk_count} ignored - session not active")
                elif not chunk_data:
                    logger.debug(f"📦 Chunk #{self._debug_chunk_count} ignored - no data")
                    
        except Exception as e:
            logger.error(f"Error handling audio chunk #{self._debug_chunk_count}: {e}")
    
    async def handle_audio_end(self):
        """Handle end of built-in audio recording"""
        try:
            logger.info("🔇 handle_audio_end called")
            if self._audio_session_active:
                logger.info(f"Built-in audio recording ended by user (received {self._debug_chunk_count} chunks)")
                await self._finalize_builtin_recording()
            else:
                logger.info("Audio end called but session was not active")
                
        except Exception as e:
            logger.error(f"Error handling audio end: {e}")
    
    async def _start_chunk_processor(self):
        """Start the chunk processor task"""
        if not self._chunk_processor_task or self._chunk_processor_task.done():
            self._processing_chunks = True
            self._chunk_processor_task = asyncio.create_task(self._process_chunk_queue())
            logger.info("🔄 Chunk processor started")
    
    async def _stop_chunk_processor(self):
        """Stop the chunk processor task"""
        self._processing_chunks = False
        if self._chunk_processor_task and not self._chunk_processor_task.done():
            try:
                await asyncio.wait_for(self._chunk_processor_task, timeout=2.0)
                logger.info("🔄 Chunk processor stopped")
            except asyncio.TimeoutError:
                self._chunk_processor_task.cancel()
                logger.info("🔄 Chunk processor cancelled")
    
    async def _process_chunk_queue(self):
        """Process audio chunks with enhanced debugging"""
        try:
            consecutive_silence = 0
            speech_detected = False
            start_time = time.time()
            last_activity_time = start_time
            processed_chunks = 0
            
            logger.info("🔄 Starting chunk queue processing")
            
            while self._processing_chunks:
                try:
                    # Use a longer timeout to avoid premature timeouts
                    chunk_data = await asyncio.wait_for(
                        self._chunk_queue.get(),
                        timeout=1.0
                    )
                    
                    processed_chunks += 1
                    
                    if chunk_data and len(chunk_data) > 0:
                        self._accumulated_audio.extend(chunk_data)
                        self._last_audio_time = time.time()
                        last_activity_time = time.time()
                        
                        # Calculate audio level
                        audio_level = self._calculate_audio_level(chunk_data)
                        
                        # Log audio levels for first few chunks
                        if processed_chunks <= 10:
                            logger.info(f"🔊 Chunk {processed_chunks} audio level: {audio_level:.4f}")
                        
                        if audio_level > self.silence_threshold:
                            if not speech_detected:
                                speech_detected = True
                                logger.info(f"🗣️ Speech detected (level: {audio_level:.4f}, threshold: {self.silence_threshold})")
                            consecutive_silence = 0
                        else:
                            consecutive_silence += 1
                            
                            # Stop after silence period if speech was detected
                            if speech_detected and consecutive_silence > 75:  # ~1.5 seconds
                                logger.info(f"🔇 Silence detected after speech - finalizing recording (processed {processed_chunks} chunks)")
                                await self._finalize_builtin_recording()
                                break
                        
                        # Max duration check
                        if time.time() - start_time > self.max_recording_duration:
                            logger.info(f"⏰ Max duration reached - finalizing recording (processed {processed_chunks} chunks)")
                            await self._finalize_builtin_recording()
                            break
                            
                except asyncio.TimeoutError:
                    current_time = time.time()
                    
                    # Check if we should timeout based on last chunk received
                    if (self.last_chunk_time and 
                        current_time - self.last_chunk_time > self.stream_timeout):
                        logger.info(f"⏰ Stream timeout - no chunks for {current_time - self.last_chunk_time:.1f}s (processed {processed_chunks} total)")
                        await self._finalize_builtin_recording()
                        break
                    
                    # Check for initial timeout (no first chunk received)
                    elif (not self._first_chunk_received and 
                          current_time - start_time > self.initial_timeout):
                        logger.warning(f"⏰ Initial timeout - no audio chunks received after {self.initial_timeout}s")
                        logger.warning(f"Debug info: session_active={self._audio_session_active}, chunk_count={self._debug_chunk_count}")
                        await self._finalize_builtin_recording()
                        break
                    
                    continue
                    
        except Exception as e:
            logger.error(f"Error in chunk processor: {e}")
            await self._finalize_builtin_recording()
    
    def _calculate_audio_level(self, chunk_data: bytes) -> float:
        """Calculate audio level from chunk data with better handling"""
        try:
            if len(chunk_data) == 0:
                return 0.0
                
            # Handle different audio formats
            try:
                # Try int16 first (most common)
                audio_data = np.frombuffer(chunk_data, dtype=np.int16)
            except ValueError:
                try:
                    # Try float32
                    audio_data = np.frombuffer(chunk_data, dtype=np.float32)
                except ValueError:
                    # Fallback to uint8
                    audio_data = np.frombuffer(chunk_data, dtype=np.uint8)
                    audio_data = audio_data.astype(np.float32) - 128.0
            
            if len(audio_data) == 0:
                return 0.0
            
            # Calculate RMS
            rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
            
            # Normalize based on data type
            if audio_data.dtype == np.int16:
                rms = rms / 32768.0
            elif audio_data.dtype == np.float32:
                rms = abs(rms)
            else:
                rms = rms / 128.0
            
            return float(rms)
            
        except Exception as e:
            logger.error(f"Error calculating audio level: {e}")
            return 0.0
    
    async def _finalize_builtin_recording(self):
        """Finalize built-in recording with comprehensive debugging"""
        try:
            if not self._audio_session_active:
                logger.info("Finalize called but session was not active")
                return
                
            logger.info(f"🏁 Finalizing built-in recording... (received {self._debug_chunk_count} chunks)")
            self._audio_session_active = False
            await self._stop_chunk_processor()
            
            audio_size = len(self._accumulated_audio)
            logger.info(f"📊 Final stats: {audio_size} bytes, {self._debug_chunk_count} chunks")
            
            if audio_size > 1024:  # Lower threshold
                await self._transition_state(VoiceState.PROCESSING)
                await self.cl.Message(content=f"🔇 Processing recording... ({audio_size} bytes from {self._debug_chunk_count} chunks)").send()
                await self._process_accumulated_audio()
            else:
                await self.cl.Message(content=f"❌ Insufficient audio data ({audio_size} bytes from {self._debug_chunk_count} chunks) - please speak louder or longer").send()
                
            await self._transition_state(VoiceState.IDLE)
            
        except Exception as e:
            logger.error(f"Error finalizing recording: {e}")
            await self._transition_state(VoiceState.ERROR)
    
    async def _process_accumulated_audio(self):
        """Process accumulated audio data with better format handling"""
        try:
            import tempfile
            import wave
            
            if len(self._accumulated_audio) == 0:
                logger.warning("No accumulated audio to process")
                return
            
            logger.info(f"🎵 Processing {len(self._accumulated_audio)} bytes of audio")
            
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_filename = temp_file.name
                
                try:
                    with wave.open(temp_filename, 'wb') as wav_file:
                        wav_file.setnchannels(1)
                        wav_file.setsampwidth(2)  # 16-bit
                        wav_file.setframerate(16000)
                        wav_file.writeframes(bytes(self._accumulated_audio))
                    
                    logger.info(f"📁 Created audio file: {temp_filename}")
                    
                    # Verify file was created
                    if os.path.exists(temp_filename) and os.path.getsize(temp_filename) > 44:  # WAV header is 44 bytes
                        # Process the audio
                        await self._process_recorded_audio(temp_filename)
                    else:
                        logger.error("Failed to create valid audio file")
                        await self.cl.Message(content="❌ Failed to create audio file").send()
                        
                except Exception as e:
                    logger.error(f"Error creating WAV file: {e}")
                    await self.cl.Message(content=f"❌ Error creating audio file: {str(e)}").send()
                
                # Clear accumulated data
                self._accumulated_audio.clear()
                
        except Exception as e:
            logger.error(f"Error processing accumulated audio: {e}")
            await self.cl.Message(content=f"❌ Error processing audio: {str(e)}").send()
    
    async def _process_recorded_audio(self, audio_file_path: str):
        """Process recorded audio file"""
        try:
            logger.info(f"Processing audio file: {audio_file_path}")
            
            # Show processing message
            processing_msg = await self.cl.Message(content="🔄 Transcribing audio...").send()
            
            # Transcribe audio
            text = await self.voice_manager.transcribe_audio_file(audio_file_path)
            
            # Remove processing message
            await processing_msg.remove()
            
            if not text or text.strip() == "":
                await self.cl.Message(content="❌ Could not understand the audio. Please speak more clearly and try again.").send()
                return
                
            logger.info(f"Transcribed text: '{text}'")
            
            # Show what was heard
            await self.cl.Message(content=f"👂 I heard: \"{text}\"").send()
            
            # Process the transcribed text
            await self._process_transcribed_text(text)
            
        except Exception as e:
            logger.error(f"Error processing recorded audio: {e}")
            await self.cl.Message(content=f"❌ Error processing audio: {str(e)[:100]}").send()
        finally:
            # Clean up audio file
            try:
                if os.path.exists(audio_file_path):
                    os.unlink(audio_file_path)
            except Exception as e:
                logger.error(f"Error cleaning up audio file: {e}")
    
    async def _process_transcribed_text(self, text: str):
        """Process transcribed text through the conversation system"""
        try:
            from langchain_core.messages import HumanMessage
            
            state = self.cl.user_session.get("state")
            graph = self.cl.user_session.get("graph")
            
            if not graph or not state:
                await self.cl.Message(content="❌ System not properly initialized").send()
                return
            
            # Add debug logging
            logger.info(f"Processing transcribed text: '{text}'")
            logger.info(f"Current state messages count: {len(state.get('messages', []))}")
            
            # Create voice message
            msg = HumanMessage(content=text)
            msg.voice_input = True
            
            # Initialize messages list if not present
            if 'messages' not in state:
                state['messages'] = []
                
            state["messages"].append(msg)
            
            # Store original message count
            original_message_count = len(state["messages"])
            
            # Show thinking message
            thinking = await self.cl.Message(content="🤔 Processing your request...", author="Assistant").send()
            
            try:
                # Add debug logging before graph processing
                logger.info("Invoking graph processing...")
                
                # Process through graph with timeout
                new_state = await asyncio.wait_for(graph.ainvoke(state), timeout=60.0)
                
                # Add debug logging after graph processing
                logger.info(f"Graph processing complete. New state messages count: {len(new_state.get('messages', []))}")
                
                # Update session state
                self.cl.user_session.set("state", new_state)
                
                # Remove thinking message
                await thinking.remove()
                
                # Look for new AI messages after user message
                new_messages = new_state["messages"][original_message_count:]
                ai_messages = [msg for msg in new_messages if not isinstance(msg, HumanMessage)]
                
                if ai_messages:
                    # Get the last AI message
                    ai_message = ai_messages[-1]
                    response_content = ai_message.content.strip()
                    
                    logger.info(f"Generated response: '{response_content}'")
                    
                    # Send text response
                    await self.cl.Message(content=response_content, author="Assistant").send()
                    
                    # Handle voice response if auto-speak is enabled
                    if state.get("auto_speak", False):
                        await self._speak_response(response_content)
                else:
                    logger.warning("No AI messages found in response")
                    await self.cl.Message(content="❌ I processed your request but couldn't generate a proper response. Please try again.").send()
                    
            except asyncio.TimeoutError:
                await thinking.remove()
                await self.cl.Message(content="⏰ Request processing timed out. Please try again.").send()
            except Exception as e:
                logger.error(f"Error processing through graph: {e}", exc_info=True)
                await thinking.remove()
                await self.cl.Message(content=f"❌ Error processing request: {str(e)[:100]}").send()
                
        except Exception as e:
            logger.error(f"Error in transcribed text processing: {e}", exc_info=True)
            await self.cl.Message(content=f"❌ Error processing transcribed text: {str(e)[:100]}").send()
            
            
    async def _speak_response(self, text: str):
        """Generate and play audio response"""
        try:
            logger.info(f"Generating speech for: {text[:50]}...")
            
            # Generate audio response
            audio_file = await asyncio.wait_for(
                self.voice_manager.create_audio_response(text),
                timeout=30.0
            )
            
            if audio_file and os.path.exists(audio_file):
                # Create and send messages separately
                audio_msg = self.cl.Message(content="🔊 Audio response generated")
                await audio_msg.send()
                
                audio_element = self.cl.Audio(
                    path=audio_file,
                    name=f"response_{int(time.time())}"
                )
                
                # Send audio element
                await audio_element.send(for_id=audio_msg.id if hasattr(audio_msg, "id") else None)
                
                # Clean up audio file after sending
                try:
                    os.unlink(audio_file)
                except Exception as e:
                    logger.error(f"Error cleaning up audio file: {e}")
            
            # Also try to play through system speakers
            try:
                await asyncio.wait_for(
                    self.voice_manager.speak_text_async(text),
                    timeout=30.0
                )
            except Exception as e:
                logger.error(f"Error playing through speakers: {e}")
                
        except asyncio.TimeoutError:
            logger.error("Speech generation timed out")
            error_msg = self.cl.Message(content="⏰ Speech generation timed out")
            await error_msg.send()
        except Exception as e:
            logger.error(f"Error generating voice response: {e}")
            error_msg = self.cl.Message(content=f"❌ Error generating speech: {str(e)[:100]}")
            await error_msg.send()
    # Built-in audio handlers (FIXED)
    async def handle_audio_start(self):
        """Handle start of built-in audio recording"""
        try:
            state = self.cl.user_session.get("state", {})
            if not state.get("voice_enabled"):
                await self.cl.ErrorMessage(content="Please enable voice mode first with '/voice on'").send()
                return False
    
            if not await self._is_state(VoiceState.IDLE):
                await self.cl.ErrorMessage(content="Already recording. Please wait or use '/stop' to stop.").send()
                return False
    
            await self._transition_state(VoiceState.RECORDING)
            
            # Reset state for new recording
            self._audio_session_active = True
            self.voice_detected = False
            self._accumulated_audio = bytearray()
            self._last_audio_time = time.time()
            self._first_chunk_received = False
            self.last_chunk_time = time.time()
            
            # Initialize chunk queue
            self._chunk_queue = asyncio.Queue(maxsize=1000)
            
            # Start chunk processor
            await self._start_chunk_processor()
    
            logger.info("Built-in audio recording started")
            await self.cl.Message(content="🎤 Recording active... Speak now!").send()
    
            return True
    
        except Exception as e:
            logger.error(f"Error starting built-in audio: {e}")
            await self._transition_state(VoiceState.ERROR)
            await self.cl.ErrorMessage(content=f"Failed to start recording: {str(e)}").send()
            return False
    

    async def cleanup(self):
        """Clean up resources and update state - FIXED to be async"""
        try:
            logger.info("Starting voice integration cleanup...")
            
            self._audio_session_active = False
            self._processing_chunks = False

            # Cancel chunk processor task
            if self._chunk_processor_task and not self._chunk_processor_task.done():
                self._chunk_processor_task.cancel()
                try:
                    await self._chunk_processor_task
                except asyncio.CancelledError:
                    pass

            # Cancel recording task
            if self.recording_task and not self.recording_task.done():
                self.recording_task.cancel()
                try:
                    await self.recording_task
                except asyncio.CancelledError:
                    pass

            # Clear accumulated audio
            self._accumulated_audio.clear()

            if self.voice_manager:
                self.voice_manager.cleanup()

            # Transition to IDLE state
            await self._transition_state(VoiceState.IDLE)
            
            logger.info("Voice integration cleanup completed")

        except Exception as e:
            logger.error(f"Error in cleanup: {e}")