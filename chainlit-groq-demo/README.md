# Farm Control Demo with Chainlit and GROQ

A simple, live demo using Chainlit and the GROQ API that acts as a client to the `farm_control_server` MCP server. Perfect for demonstrations and interviews.

## Features

- 🚜 **Farm Management Interface**: User-friendly chat interface for farm operations
- 🤖 **GROQ AI Integration**: Fast, efficient AI responses using Llama models
- 🔧 **MCP Tool Integration**: Connects to farm control server via Model Context Protocol
- 🐳 **Docker Ready**: Easy deployment with Docker containers
- 📊 **Real-time Monitoring**: Sensor data, actuator control, and resource management

## Quick Start

### 1. Environment Setup

Create a `.env` file with your GROQ API key:

```bash
GROQ_API_KEY=your_groq_api_key_here
```

You can get a free GROQ API key at: https://console.groq.com/

### 2. Local Development

**Option A: Using uv (Recommended - faster)**
```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Quick start with uv
./start.sh

# OR manually:
uv venv
source .venv/bin/activate
uv add chainlit groq mcp python-dotenv pydantic sqlalchemy fastapi
chainlit run app.py --watch
```

**Option B: Using pip (Traditional)**
```bash
# Install dependencies with pip
./start-pip.sh

# OR manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
chainlit run app.py --watch
```

### 3. Docker Deployment

```bash
# Build the image
docker build -t farm-control-demo .

# Run the container
docker run -p 8000:8000 --env-file .env farm-control-demo
```

## Usage

1. **Start the Application**: The demo will automatically connect to the farm control MCP server
2. **Ask Questions**: Use natural language to interact with your farm systems:
   - "Show me all farms"
   - "Check sensor data for farm 1"
   - "Open the irrigation valve for field 2"
   - "What are the current resource levels?"
   - "Create an irrigation schedule for field 1"

3. **View Results**: The AI will execute the appropriate tools and format results in a farm-friendly way

## Available Tools

The demo connects to these farm management tools via MCP:

- **list_all_farms**: Get overview of all farms
- **get_farm_details**: Detailed information for a specific farm
- **get_sensor_data**: Current sensor readings
- **control_actuator**: Control irrigation valves and pumps
- **get_resource_levels**: Check water and nutrient levels
- **get_active_actuators**: See what equipment is currently running
- **update_resource_level**: Manually adjust resource levels
- **create_irrigation_schedule**: Set up automated irrigation

## Technical Details

- **Frontend**: Chainlit (web-based chat interface)
- **AI Model**: GROQ's Llama-3.1-70b-versatile (fast inference)
- **Backend**: MCP (Model Context Protocol) server
- **Deployment**: Docker containerized
- **API Integration**: RESTful endpoints for external integrations

## Demo Tips

- The interface provides real-time responses with visual indicators
- Tool executions are clearly marked and explained
- Results are formatted for farm operators (non-technical users)
- Error handling provides clear feedback for troubleshooting

## Deployment for Interviews

This demo is designed to be easily demonstrated:

1. **Pre-built Docker image**: Quick deployment anywhere
2. **Minimal dependencies**: Only requires GROQ API key
3. **Self-contained**: Includes all necessary components
4. **Visual interface**: Professional chat interface
5. **Real functionality**: Actually controls simulated farm systems

Perfect for showcasing AI integration in agricultural technology!
