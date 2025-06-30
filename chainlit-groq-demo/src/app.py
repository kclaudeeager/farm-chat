"""
Farm Control Demo with Chainlit and GROQ API
A simple live demo that acts as a client to the farm_control_server MCP server.
"""

import chainlit as cl
import asyncio
import json
import os
from typing import Dict, Any, List
from groq import AsyncGroq
from utils.chainlit_voice_integration import ChainlitVoiceIntegration
import logging

# Initialize conversation history
conversation_history = []
mcp_tools_cache = {}

logger = logging.getLogger("chainlit-voice")


async def connect_to_mcp_server():
    """Connect to the real MCP farm control server"""
    from mcp import StdioServerParameters, ClientSession
    from mcp.client.stdio import stdio_client
    
    try:
        print("🔧 Connecting to real MCP farm control server...")
        
        # Create server parameters for the farm control server
        server_params = StdioServerParameters(
            command="python",
            args=["farm_control_server.py"],
            env=None,
        )
        
        # Create a persistent connection that we can store
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                
                # Get the real tools from the server
                result = await session.list_tools()
                
                tools = [
                    {
                        "name": t.name,
                        "description": t.description,
                        "input_schema": t.inputSchema,
                    }
                    for t in result.tools
                ]
                
                print(f"✅ Real MCP tools loaded: {len(tools)} tools available")
                for tool in tools:
                    print(f"   • {tool['name']}: {tool['description']}")
                
                # Store the session for later use
                mcp_tools_cache["session"] = session
                mcp_tools_cache["server_params"] = server_params
                
                return tools
                
    except Exception as e:
        print(f"❌ Failed to connect to real MCP server: {e}")
        import traceback
        traceback.print_exc()
        return []


@cl.on_chat_start
async def start():
    """Initialize the chat session with the farm control MCP server."""
    # Check for GROQ API key
    groq_api_key = os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        await cl.Message(
            content="⚠️ GROQ API key not found. Please set the GROQ_API_KEY environment variable."
        ).send()
        return

    # Initialize the GROQ client
    groq_client = AsyncGroq(api_key=groq_api_key)
    cl.user_session.set("groq_client", groq_client)

    # Initialize message history
    cl.user_session.set(
        "message_history",
        [
            {
                "role": "system",
                "content": """You are a helpful farm management AI assistant with access to farm control tools. 
                You can monitor sensor data, control actuators like irrigation systems and valves, 
                check resource levels, and manage farm operations via ThingsBoard IoT platform.
                
                When using tools:
                - Be direct and efficient
                - Explain what you're doing in simple terms
                - Provide actionable insights based on the data
                - Format responses clearly for farm operators
                - Use ThingsBoard data for real-time monitoring
                """
            }
        ]
    )

    # Send a loading message
    startup_message = cl.Message(content="🚜 Connecting to Farm Control System...")
    await startup_message.send()

    # Connect to MCP server directly
    try:
        tools = await connect_to_mcp_server()
        if tools:
            cl.user_session.set("mcp_tools", {"farm_control": tools})
            tool_names = [tool["name"] for tool in tools]
            
            await startup_message.remove()
            await cl.Message(
                content=f"✅ Farm Control System connected!\n🛠️ Available tools ({len(tools)}):\n• " + "\n• ".join(tool_names) + "\n\n🌾 Ask me about your farm operations!"
            ).send()
        else:
            await startup_message.remove()
            await cl.Message(
                content="⚠️ Farm Control System connection failed. Please check if farm_control_server.py is working.\n\nYou can still ask general farm questions!"
            ).send()
    except Exception as e:
        await startup_message.remove()
        await cl.Message(
            content=f"❌ Error connecting to Farm Control System: {str(e)}\n\nRunning in basic mode."
        ).send()



@cl.step(type="tool")
async def execute_tool(tool_name: str, tool_input: Dict[str, Any]):
    """Execute a real MCP farm control tool."""
    from mcp import StdioServerParameters, ClientSession
    from mcp.client.stdio import stdio_client
    
    print(f"🔧 Executing real tool: {tool_name} with input: {tool_input}")
    
    try:
        # First try to use a cached session if available
        for session_key, session in mcp_tools_cache.items():
            if session_key.startswith("session_") and session:
                try:
                    result = await session.call_tool(tool_name, tool_input)
                    print(f"✅ Real tool result (cached session): {result}")
                    return result
                except Exception as e:
                    print(f"⚠️ Cached session failed, creating new connection: {e}")
                    break
        
        # Fallback: Create a new connection for each tool call
        server_params = StdioServerParameters(
            command="python",
            args=["farm_control_server.py"],
            env=None,
        )
        
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()
                
                # Call the actual tool
                result = await session.call_tool(tool_name, tool_input)
                
                print(f"✅ Real tool result (new session): {result}")
                return result
                
    except Exception as e:
        print(f"❌ Error executing real tool {tool_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"Error calling tool '{tool_name}': {str(e)}"}


def get_mock_data_for_demo():
    """Fallback mock data if MCP connection fails"""
    return {
        "farm_info": "Demo Farm - 100 hectares, 4 zones, 15 sensors active",
        "sensor_data": "Temp: 22.5°C, Humidity: 65%, Soil: 45%",
        "irrigation_status": "Zone 1: Active, Flow: 2.5L/min"
    }


async def format_tools_for_groq(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format MCP tools for GROQ function calling."""
    groq_tools = []
    
    for tool in tools:
        groq_tool = {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            }
        }
        groq_tools.append(groq_tool)
    
    return groq_tools


def serialize_tool_result(result):
    """Helper function to serialize tool results for display."""
    if isinstance(result, dict):
        return result
    elif hasattr(result, "content") and isinstance(result.content, list):
        # Handle MCP CallToolResult with content list
        serialized_content = []
        for item in result.content:
            if hasattr(item, "text"):
                serialized_content.append({
                    "type": getattr(item, "type", "text"),
                    "text": item.text
                })
            elif hasattr(item, "__dict__"):
                serialized_content.append(item.__dict__)
            else:
                serialized_content.append(str(item))
        return {"content": serialized_content}
    elif hasattr(result, "text"):
        # Handle TextContent objects
        return {
            "type": getattr(result, "type", "text"),
            "text": result.text
        }
    elif hasattr(result, "__dict__"):
        return result.__dict__
    return str(result)


def format_farm_response(tool_name: str, result: Any, user_query: str) -> str:
    """Format tool results in a farm-friendly way, with audio widget and auto-playback for TTS."""
    try:
        serialized = serialize_tool_result(result)
        text_content = None
        audio_path = None
        # Extract text and audio path if available
        if isinstance(serialized, dict):
            if "content" in serialized and isinstance(serialized["content"], list):
                text_parts = []
                for item in serialized["content"]:
                    if isinstance(item, dict) and "text" in item:
                        text_parts.append(item["text"])
                    else:
                        text_parts.append(str(item))
                text_content = " ".join(text_parts)
            elif "text" in serialized:
                text_content = serialized["text"]
            elif "audio_path" in serialized:
                audio_path = serialized["audio_path"]
            else:
                text_content = json.dumps(serialized, indent=2)
        else:
            text_content = str(serialized)
        # If this is a TTS tool, add an audio widget and auto-play if possible
        if tool_name == "speak_text" and (audio_path or (isinstance(result, str) and result.endswith('.wav'))):
            audio_file = audio_path or result
            # Use Chainlit's audio widget (with auto_play if supported)
            cl.Audio(name="TTS Audio", path=audio_file, auto_play=True).send()
            return f"🔊 **Audio Response**\n\nAudio file generated: {audio_file}"
        # Create context-aware responses based on tool type
        if "farm" in tool_name.lower():
            return f"🚜 **Farm Information**\n\n{text_content}"
        elif "sensor" in tool_name.lower():
            return f"📊 **Sensor Data**\n\n{text_content}"
        elif "actuator" in tool_name.lower() or "control" in tool_name.lower():
            return f"⚙️ **Control Action**\n\n{text_content}"
        elif "resource" in tool_name.lower():
            return f"💧 **Resource Status**\n\n{text_content}"
        elif "irrigation" in tool_name.lower():
            return f"🌱 **Irrigation System**\n\n{text_content}"
        else:
            return f"ℹ️ **{tool_name.replace('_', ' ').title()}**\n\n{text_content}"
    except Exception as e:
        logger.error(f"Error formatting farm response: {e}", exc_info=True)
        return f"📋 Result: {str(result)}\n\n*Note: Error formatting response: {str(e)}*"


@cl.on_message
async def on_message(message: cl.Message):
    """Process user message and generate a response using GROQ and farm control tools."""
    
    # Get GROQ client
    groq_client = cl.user_session.get("groq_client")
    if not groq_client:
        await cl.Message(content="❌ GROQ client not initialized. Please restart the chat.").send()
        return
    
    # Check MCP connection
    mcp_tools = cl.user_session.get("mcp_tools", {})
    if not mcp_tools:
        # If no MCP connection, still allow basic chat but inform user
        await cl.Message(content="⚠️ Farm Control System is not fully connected. Responding with basic assistance only.").send()
    
    # Get message history
    message_history = cl.user_session.get("message_history", [])
    
    # Add current user message
    message_history.append({"role": "user", "content": message.content})
    
    # Get available tools
    all_tools = []
    for connection_tools in mcp_tools.values():
        all_tools.extend(connection_tools)
    
    # Format tools for GROQ (only if we have MCP connection)
    groq_tools = await format_tools_for_groq(all_tools) if all_tools else None
    
    try:
        # Send thinking message
        thinking_msg = cl.Message(content="🤔 Processing your request...")
        await thinking_msg.send()
        
        # Get response from GROQ
        response = await groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # Using GROQ's latest model
            messages=message_history,
            tools=groq_tools if groq_tools else None,
            tool_choice="auto" if groq_tools else None,
            temperature=0.1,
            max_tokens=1024
        )
        
        # Remove thinking message
        await thinking_msg.remove()
        
        response_message = response.choices[0].message
        
        # Handle tool calls
        if response_message.tool_calls:
            # Add assistant message with tool calls to history
            message_history.append({
                "role": "assistant",
                "content": response_message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in response_message.tool_calls
                ]
            })
            
            # Execute each tool call
            tool_responses = []
            for tool_call in response_message.tool_calls:
                try:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    
                    # Show what tool we're using
                    await cl.Message(
                        content=f"🔧 Using tool: **{tool_name}**",
                        author="System"
                    ).send()
                    
                    # Execute the tool
                    tool_result = await execute_tool(tool_name, tool_args)
                    
                    # Format and display the result
                    formatted_result = format_farm_response(tool_name, tool_result, message.content)
                    await cl.Message(
                        content=formatted_result,
                        author="Farm System"
                    ).send()

                    # If the tool is speak_text, handle audio playback robustly (only once)
                    if tool_name == "speak_text":
                        audio_file = None
                        attempted_paths = []
                        tts_text = None
                        if isinstance(tool_result, dict):
                            if "audio_path" in tool_result:
                                candidate = tool_result["audio_path"]
                                attempted_paths.append(candidate)
                                if candidate and isinstance(candidate, str) and os.path.exists(candidate):
                                    audio_file = candidate
                            elif "content" in tool_result and isinstance(tool_result["content"], list):
                                for item in tool_result["content"]:
                                    if isinstance(item, dict) and "text" in item and isinstance(item["text"], str):
                                        attempted_paths.append(item["text"])
                                        if item["text"].endswith('.wav') and os.path.exists(item["text"]):
                                            audio_file = item["text"]
                                            break
                                    elif isinstance(item, str):
                                        attempted_paths.append(item)
                                        if item.endswith('.wav') and os.path.exists(item):
                                            audio_file = item
                                            break
                            # Try to extract the text that was spoken
                            if "text" in tool_result:
                                tts_text = tool_result["text"]
                        elif isinstance(tool_result, str):
                            attempted_paths.append(tool_result)
                            if tool_result.endswith('.wav') and os.path.exists(tool_result):
                                audio_file = tool_result
                        elif hasattr(tool_result, "content") and isinstance(tool_result.content, list):
                            for item in tool_result.content:
                                if hasattr(item, "text") and isinstance(item.text, str):
                                    attempted_paths.append(item.text)
                                    if item.text.endswith('.wav') and os.path.exists(item.text):
                                        audio_file = item.text
                                        break
                        # Try to extract the text that was spoken from tool_input if not found
                        if not tts_text and "text" in tool_args:
                            tts_text = tool_args["text"]
                        # Send the TTS text as a message
                        if tts_text:
                            await cl.Message(content=f'🗣️ TTS text: "{tts_text}"').send()
                        if audio_file:
                            audio_msg = await cl.Message(content="🔊 Playing TTS audio...").send()
                            await cl.Audio(name="TTS Audio", path=audio_file, auto_play=True).send(for_id=audio_msg.id)
                        else:
                            logger.warning(f"TTS audio file not found. Attempted paths: {attempted_paths}")
                            await cl.Message(content=f"⚠️ TTS audio file was not found or invalid. Attempted: {attempted_paths}").send()
                    # Add tool response to history
                    tool_response_content = json.dumps(serialize_tool_result(tool_result))
                    message_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_response_content
                    })
                    
                    tool_responses.append(tool_response_content)
                    
                except Exception as e:
                    error_msg = f"❌ Error executing {tool_call.function.name}: {str(e)}"
                    await cl.Message(content=error_msg).send()
                    
                    message_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": f"Error: {str(e)}"
                    })
            
            # Get final response with tool results
            final_response = await groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=message_history,
                temperature=0.1,
                max_tokens=512
            )
            
            final_content = final_response.choices[0].message.content
            if final_content:
                await cl.Message(content=final_content).send()
                message_history.append({"role": "assistant", "content": final_content})
            
        else:
            # Handle regular text response (no tool calls)
            content = response_message.content
            if content:
                await cl.Message(content=content).send()
                message_history.append({"role": "assistant", "content": content})
        
        # Update session history
        cl.user_session.set("message_history", message_history)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        await cl.Message(
            content=f"❌ **Error processing request:**\n\n{str(e)}\n\n```\n{error_details}\n```"
        ).send()


@cl.on_stop
async def cleanup():
    """Clean up resources when the chat stops."""
    print("🧹 Cleaning up Farm Control Demo session...")


@cl.on_mcp_connect
async def on_mcp_connect(connection, session):
    """Handle MCP server connection events."""
    await cl.Message(f"🔗 MCP server connected: {connection.name}").send()
    
    try:
        # Store the session for the connection
        mcp_tools_cache[f"session_{connection.name}"] = session
        
        # Get tools from this connection
        result = await session.list_tools()
        
        tools = [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.inputSchema,
            }
            for t in result.tools
        ]
        
        # Update user session with new tools
        mcp_tools = cl.user_session.get("mcp_tools", {})
        mcp_tools[connection.name] = tools
        cl.user_session.set("mcp_tools", mcp_tools)
        
        tool_names = [tool["name"] for tool in tools]
        await cl.Message(
            content=f"🛠️ Found {len(tools)} tools from {connection.name}:\n• " + "\n• ".join(tool_names)
        ).send()
        
    except Exception as e:
        await cl.Message(content=f"❌ Error listing tools from {connection.name}: {str(e)}").send()


@cl.on_mcp_disconnect
async def on_mcp_disconnect(name: str, session):
    """Handle MCP server disconnection events."""
    await cl.Message(f"🔌 MCP server disconnected: {name}").send()
    
    # Clean up cached data
    if f"session_{name}" in mcp_tools_cache:
        del mcp_tools_cache[f"session_{name}"]
    
    # Remove tools from user session
    mcp_tools = cl.user_session.get("mcp_tools", {})
    if name in mcp_tools:
        del mcp_tools[name]
        cl.user_session.set("mcp_tools", mcp_tools)

@cl.on_audio_start
async def on_audio_start():
    try:
        logger.info("🎤 Audio session starting - checking permissions...")
        
        await cl.Message(content="🎤 Microphone access requested. Please allow when prompted.").send()
        
        state = cl.user_session.get("state", {})
        state["voice_enabled"] = True
        state["auto_speak"] = True
        cl.user_session.set("state", state)
        
        voice_integration = cl.user_session.get("voice_integration")
        if not voice_integration:
            voice_integration = ChainlitVoiceIntegration(cl)
            cl.user_session.set("voice_integration", voice_integration)
        
        result = await voice_integration.handle_audio_start()
        
        if result:
            await cl.Message(content="✅ Audio recording started successfully!").send()
        else:
            await cl.Message(content="❌ Failed to start audio recording").send()
            
        return result
        
    except Exception as e:
        error_msg = f"Audio start error: {str(e)}"
        logger.error(error_msg, exc_info=True)
        await cl.ErrorMessage(content=error_msg).send()
        return False

@cl.on_audio_chunk
async def on_audio_chunk(chunk: cl.InputAudioChunk):
    try:
        # Add chunk size logging
        logger.info(f"📦 Received audio chunk: {len(chunk.data)} bytes")
        
        voice_integration = cl.user_session.get("voice_integration")
        if voice_integration:
            await voice_integration.handle_audio_chunk(chunk.data)
        else:
            logger.warning("No voice integration found for audio chunk")
            
    except Exception as e:
        logger.error(f"Error processing audio chunk: {e}")

@cl.on_audio_end
async def on_audio_end():
    """Handle end of audio stream with proper voice input processing"""
    try:
        logger.info("🏁 Audio recording ended - processing...")
        
        voice_integration = cl.user_session.get("voice_integration")
        if not voice_integration:
            logger.warning("No voice integration found for audio end")
            return
            
        # Process the recorded audio
        transcribed_text = await voice_integration.handle_audio_end()
        
        if transcribed_text and transcribed_text.strip():
            logger.info(f"Transcribed text: '{transcribed_text}'")
            
            # Create a message with voice input flag and process it
            voice_message = cl.Message(content=transcribed_text)
            voice_message.voice_input = True  # Mark as voice input
            
            # Process the voice message through the normal message handler
            await on_message(voice_message)  
        else:
            await cl.Message(content="I didn't catch that. Could you please try again?").send()
            
    except Exception as e:
        logger.error(f"Error ending audio session: {e}", exc_info=True)
        await cl.Message(content="Sorry, I had trouble processing your voice input. Please try again.").send()

if __name__ == "__main__":
    print("🚜 Starting Farm Control Chainlit + GROQ Demo...")
