#!/bin/bash
# Bot-hosting.net: Cloudflare Tunnel & Python Bot Startup Script

# Set working directory to script location (for bot-hosting.net compatibility)
cd "$(dirname "$0")"

# Authenticate Cloudflare Tunnel if not already authenticated
if [ ! -f ~/.cloudflared/cert.pem ]; then
  echo "Cloudflare Tunnel not authenticated. Running 'cloudflared login'..."
  cloudflared login
fi

# Start Cloudflare Tunnel in the background (replace with your tunnel name)
cloudflared tunnel run ConversoAI-Image_Gen &
CLOUDFLARED_PID=$!

# Wait a few seconds to ensure tunnel is up (optional, but helps with race conditions)
sleep 5

# Install Python dependencies (ensure pip is available in bot-hosting.net environment)
pip install --user -r requirements.txt

# Start the Python bot
python3 main.py

# Wait for cloudflared to finish (optional, keeps tunnel open if bot exits)
wait $CLOUDFLARED_PID
