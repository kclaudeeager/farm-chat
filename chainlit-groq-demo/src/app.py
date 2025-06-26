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


# Initialize conversation history
conversation_history = []
mcp_tools_cache = {}


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
    """Format tool results in a farm-friendly way."""
    try:
        serialized = serialize_tool_result(result)
        
        # Extract text content if available
        if isinstance(serialized, dict):
            if "content" in serialized and isinstance(serialized["content"], list):
                # Handle list of content objects
                text_parts = []
                for item in serialized["content"]:
                    if isinstance(item, dict) and "text" in item:
                        text_parts.append(item["text"])
                    else:
                        text_parts.append(str(item))
                text_content = " ".join(text_parts)
            elif "text" in serialized:
                text_content = serialized["text"]
            else:
                text_content = json.dumps(serialized, indent=2)
        else:
            text_content = str(serialized)
        
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


if __name__ == "__main__":
    print("🚜 Starting Farm Control Chainlit + GROQ Demo...")
