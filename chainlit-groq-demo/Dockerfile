FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (including portaudio for pyaudio and espeak for pyttsx3)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    portaudio19-dev \
    espeak \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Clean any possibly corrupted Whisper model cache
RUN rm -f /root/.cache/whisper/base.pt /home/app/.cache/whisper/base.pt || true

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Copy application files from src directory
COPY src/ .

# Create a non-root user
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app
USER app

# Expose the port Chainlit runs on
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
