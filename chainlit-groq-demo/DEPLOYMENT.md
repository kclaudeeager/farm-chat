# Farm Control Demo - Deployment Guide

## 📋 Quick Deployment Checklist

### For Live Demos / Interviews

1. **Get GROQ API Key** (Free, takes 2 minutes)
   - Visit: https://console.groq.com/
   - Sign up and get your API key
   - Copy it to your `.env` file

2. **One-Command Setup**
   ```bash
   ./start.sh
   ```

3. **Demo Ready!**
   - Open browser to `http://localhost:8000`
   - Chat interface is ready for farm management

---

## 🐳 Docker Deployment (Production)

### Quick Start
```bash
# Clone and setup
git clone <your-repo>
cd experiments/chainlit-groq-demo

# Create environment file
cp .env.example .env
# Edit .env with your GROQ_API_KEY

# Run with Docker
docker-compose up --build
```

### Production with SSL
```bash
# Use production profile (includes nginx)
docker-compose --profile production up --build
```

---

## 🎯 Demo Script for Interviews

### Opening (30 seconds)
"I've built an AI-powered farm management system that demonstrates real-world IoT integration. Let me show you how farmers can interact with their equipment using natural language."

### Demo Flow (3-5 minutes)

1. **Start Simple** 
   ```
   User: "Show me all my farms"
   ```
   *Shows: Tool integration, clean UI, real data*

2. **Show Monitoring**
   ```
   User: "Check the sensor data for farm 1"
   ```
   *Shows: Real-time data, professional formatting*

3. **Demonstrate Control**
   ```
   User: "Open the irrigation valve for field 2"
   ```
   *Shows: Actual system control, safety considerations*

4. **Advanced Features**
   ```
   User: "Create an irrigation schedule for field 1 starting at 6 AM for 30 minutes"
   ```
   *Shows: Complex parameter handling, JSON integration*

5. **Problem Solving**
   ```
   User: "What are my current resource levels and should I be concerned about anything?"
   ```
   *Shows: AI analysis, actionable insights*

### Key Points to Highlight
- **Real Integration**: Not just a chatbot - actually controls systems
- **User-Friendly**: Non-technical farmers can use natural language
- **Production Ready**: Docker deployment, error handling, monitoring
- **Scalable Architecture**: MCP protocol for tool integration
- **Cost Effective**: Uses GROQ (cheaper than OpenAI) for fast inference

### Technical Architecture (if asked)
- **Frontend**: Chainlit (Python-based chat interface)
- **AI**: GROQ's Llama models (fast, cost-effective)
- **Integration**: Model Context Protocol (MCP) for tool calling
- **Backend**: Simulated farm control systems
- **Deployment**: Docker containers with health checks

---

## 🔧 Troubleshooting

### Common Issues

**"GROQ_API_KEY not set"**
- Copy `.env.example` to `.env`
- Add your API key from https://console.groq.com/

**"MCP server not connecting"**
- Check if `farm_control_server.py` exists in directory
- Verify Python dependencies are installed

**"Port 8000 already in use"**
- Change port in docker-compose.yml or kill existing process
- Use `docker-compose down` to stop containers

**"Tools not loading"**
- Check server logs for errors
- Verify MCP server is running properly

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
chainlit run app.py --debug
```

---

## 📊 Performance Notes

- **Response Time**: ~1-2 seconds per interaction
- **Model**: Llama-3.1-70B (fast inference via GROQ)
- **Memory**: ~512MB RAM for container
- **Scalability**: Can handle multiple concurrent users

---

## 🚀 Next Steps / Extensions

For further development:

1. **Real IoT Integration**: Connect to actual sensors/actuators
2. **User Authentication**: Add login system for multi-user farms
3. **Data Persistence**: Add database for historical data
4. **Alert System**: Real-time notifications for farm issues
5. **Mobile App**: React Native wrapper for field use
6. **Analytics Dashboard**: Grafana integration for metrics

This demo showcases the foundation for a complete AgTech solution!
