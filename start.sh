#!/bin/bash
# Bot-hosting.net: Python Bot Startup Script (Cloudflare Tunnel removed)

# Set working directory to script location (for bot-hosting.net compatibility)
cd "$(dirname "$0")"

# Install Python dependencies (ensure pip is available in bot-hosting.net environment)
pip install --user -r requirements.txt

# Start the Python bot on the host's assigned port
python3 main.py --port=21434
