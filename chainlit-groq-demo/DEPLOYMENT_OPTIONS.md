# 🚀 Deployment Guide: Farm Control AI System

## **Deployment Options Overview**

### **Option 1: Cloud Platform (Recommended) 🌐**
**Best for**: Production deployment, automatic scaling, SSL, custom domains
**Platforms**: Render, Railway, DigitalOcean, AWS, GCP

### **Option 2: Local + ngrok (Development/Demo) 📱**
**Best for**: Quick demos, development, sharing with clients
**Use case**: Temporary public access without server setup

### **Option 3: VPS with Docker 🖥️**
**Best for**: Full control, cost optimization, custom infrastructure

---

## **🎯 Option 1: Cloud Platform Deployment**

### **A. Render Deployment (Easiest)**

1. **Create `render.yaml`**:
```yaml
services:
  - type: web
    name: farm-control-ai
    env: docker
    dockerfilePath: ./Dockerfile
    envVars:
      - key: GROQ_API_KEY
        sync: false  # Set in Render dashboard
      - key: PORT
        value: 8000
    plan: starter  # Free tier available
```

2. **Deploy Steps**:
```bash
# 1. Push to GitHub
git add .
git commit -m "Ready for Render deployment"
git push origin main

# 2. Connect to Render
# - Go to render.com
# - Connect GitHub repo
# - Select this project
# - Add GROQ_API_KEY in environment variables
# - Deploy!
```

### **B. Railway Deployment**

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Deploy
railway login
railway init
railway up

# 3. Set environment variables
railway variables set GROQ_API_KEY=your_key_here
```

### **C. DigitalOcean App Platform**

```yaml
# .do/app.yaml
name: farm-control-ai
services:
- name: web
  source_dir: /
  github:
    repo: your-username/your-repo
    branch: main
  run_command: chainlit run src/app.py --host 0.0.0.0 --port 8080
  environment_slug: python
  instance_count: 1
  instance_size_slug: basic-xxs
  envs:
  - key: GROQ_API_KEY
    scope: RUN_TIME
    type: SECRET
```

---

## **📱 Option 2: Local + ngrok (Quick Demo)**

### **Setup**
```bash
# 1. Start your services locally
docker-compose up -d

# 2. Install ngrok (if not installed)
# Download from: https://ngrok.com/download

# 3. Expose your local app
ngrok http 9001  # For the integrated interface
# OR
ngrok http 8000  # For just the AI chat

# 4. Share the ngrok URL
# Example: https://abc123.ngrok.io
```

### **Professional ngrok Setup**
```bash
# Get ngrok auth token (free account)
ngrok authtoken YOUR_AUTH_TOKEN

# Use custom subdomain (paid plan)
ngrok http 9001 --subdomain=farm-ai-demo

# Multiple services with config file
# Create ~/.ngrok2/ngrok.yml:
```

```yaml
authtoken: YOUR_AUTH_TOKEN
tunnels:
  ai-chat:
    addr: 8000
    proto: http
    subdomain: farm-ai-chat
  integration:
    addr: 9001
    proto: http
    subdomain: farm-ai-full
```

```bash
# Start all tunnels
ngrok start --all
```

---

## **🖥️ Option 3: VPS with Docker**

### **Server Setup (Ubuntu/Debian)**
```bash
# 1. Connect to your VPS
ssh user@your-server-ip

# 2. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER

# 3. Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 4. Clone your repo
git clone https://github.com/your-username/your-repo.git
cd your-repo/experiments/chainlit-groq-demo
```

### **Production Deployment**
```bash
# 1. Setup environment
cp .env.example .env
nano .env  # Add your GROQ_API_KEY

# 2. Deploy with production config
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 3. Setup SSL with Let's Encrypt (optional)
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### **Domain & SSL Setup**
```bash
# 1. Point your domain to your VPS IP
# Add A record: your-domain.com → your-server-ip

# 2. Update nginx.conf
# Change server_name from localhost to your-domain.com

# 3. Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

---

## **🔧 Configuration for Production**

### **Environment Variables**
```bash
# Required
GROQ_API_KEY=your_groq_api_key

# Optional
OPENAI_PROJECT_API_KEY=your_openai_key
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### **Monitoring & Logs**
```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f farm-control-demo

# Monitor resources
docker stats

# Health checks
curl http://your-domain.com/health
```

---

## **📊 Recommended Approach**

### **For Demo/Interview** 🎯
1. **Local + ngrok**: Fastest setup, works immediately
2. **Commands**:
   ```bash
   docker-compose up -d
   ngrok http 9001
   # Share the ngrok URL
   ```

### **For Production** 🚀
1. **Render**: Easiest cloud deployment
2. **Railway**: Good for developers
3. **DigitalOcean**: Best price/performance

### **For Development** 💻
1. **Local Docker**: Full control
2. **Add ngrok** when need to share

---

## **🔗 Access URLs After Deployment**

### **Local Development**
- AI Chat: http://localhost:8000
- Full Integration: http://localhost:9001
- ThingsBoard: http://localhost:8080

### **Production (with domain)**
- Main App: https://your-domain.com
- Integration: https://your-domain.com/integration
- ThingsBoard: https://your-domain.com/thingsboard

### **Render/Railway**
- Main App: https://your-app-name.onrender.com
- (Railway gives similar URL structure)

**Choose the option that best fits your needs!** For quick demos, use ngrok. For production, use cloud platforms like Render.
