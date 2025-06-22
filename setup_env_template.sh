#!/bin/bash

# OpenAI API Usage Monitor - Environment Setup Template
# Copy this file to setup_env.sh and add your actual API key

echo "🔑 Setting up OpenAI API Key..."

# Replace YOUR_API_KEY_HERE with your actual OpenAI API key
export OPENAI_API_KEY="YOUR_API_KEY_HERE"

echo "✅ API Key set for current session!"
echo "📊 You can now run: ./start_openai_monitor.sh tier2"
echo ""
echo "🔧 To make this permanent, add this line to your shell profile:"
echo "   ~/.bashrc (Linux) or ~/.zshrc (macOS):"
echo ""
echo "export OPENAI_API_KEY=\"YOUR_API_KEY_HERE\""
echo ""
echo "🚀 Quick start options:"
echo "   ./start_openai_monitor.sh demo     # Test with simulated data"
echo "   ./start_openai_monitor.sh tier1    # 100k tokens/month"
echo "   ./start_openai_monitor.sh tier2    # 500k tokens/month"
echo "   ./start_openai_monitor.sh tier3    # 1M tokens/month"
echo "   ./start_openai_monitor.sh help     # Show all options"
echo ""
echo "🔐 Security Note:"
echo "   Never commit your actual API key to version control!"
echo "   Keep your API key secure and private."
