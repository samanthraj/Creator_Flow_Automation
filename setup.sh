#!/bin/bash
# ============================================================
# YouTube Agent - One-time Setup Script
# Run this once on your laptop: bash setup.sh
# ============================================================

echo "🚀 Installing YouTube Agent dependencies..."

# Install Python packages
pip install openai-whisper \
            yt-dlp \
            google-api-python-client \
            google-auth-httplib2 \
            google-auth-oauthlib \
            requests \
            pillow \
            groq

echo ""
echo "✅ All packages installed!"
echo ""
echo "📋 Next steps:"
echo "  1. Add your API keys to agent.py (GROQ_API_KEY, IDEOGRAM_API_KEY)"
echo "  2. Add your YouTube Channel ID to agent.py"
echo "  3. Put your Google client_secret.json in the credentials/ folder"
echo "  4. Run: python agent.py"
