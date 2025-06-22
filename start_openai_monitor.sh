#!/bin/bash

# OpenAI Token Usage Monitor - Quick Start Script
# This script makes it easy to start the OpenAI monitor with common configurations

echo "🚀 OpenAI Token Usage Monitor - Quick Start"
echo "============================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set. You can:"
    echo "   1. Set it: export OPENAI_API_KEY='your-key-here'"
    echo "   2. Run demo mode: ./start_openai_monitor.sh demo"
    echo "   3. Pass it directly: ./openai_usage_monitor.py --api-key 'your-key'"
    echo ""
fi

# Parse command line arguments
case "$1" in
    "demo")
        echo "🎭 Starting in DEMO mode with simulated data..."
        python3 openai_usage_monitor.py --demo
        ;;
    "tier1")
        echo "📊 Starting with Tier 1 limits (100k tokens/month)..."
        python3 openai_usage_monitor.py --plan tier1
        ;;
    "tier2")
        echo "📊 Starting with Tier 2 limits (500k tokens/month)..."
        python3 openai_usage_monitor.py --plan tier2
        ;;
    "tier3")
        echo "📊 Starting with Tier 3 limits (1M tokens/month)..."
        python3 openai_usage_monitor.py --plan tier3
        ;;
    "tier4")
        echo "📊 Starting with Tier 4 limits (5M tokens/month)..."
        python3 openai_usage_monitor.py --plan tier4
        ;;
    "tier5")
        echo "📊 Starting with Tier 5 limits (50M tokens/month)..."
        python3 openai_usage_monitor.py --plan tier5
        ;;
    "analytics")
        echo "📈 Showing usage analytics (last 7 days)..."
        python3 openai_usage_monitor.py --analytics
        ;;
    "analytics-7")
        echo "📈 Showing usage analytics (last 7 days)..."
        python3 openai_usage_monitor.py --analytics --days 7
        ;;
    "analytics-30")
        echo "📈 Showing usage analytics (last 30 days)..."
        python3 openai_usage_monitor.py --analytics --days 30
        ;;
    "export-csv")
        echo "📄 Exporting usage data to CSV..."
        python3 openai_usage_monitor.py --export csv
        ;;
    "export-json")
        echo "📄 Exporting usage data to JSON..."
        python3 openai_usage_monitor.py --export json
        ;;
    "budget-10")
        echo "💰 Setting monthly budget to $10..."
        python3 openai_usage_monitor.py --budget 10
        ;;
    "budget-50")
        echo "💰 Setting monthly budget to $50..."
        python3 openai_usage_monitor.py --budget 50
        ;;
    "budget-100")
        echo "💰 Setting monthly budget to $100..."
        python3 openai_usage_monitor.py --budget 100
        ;;
    "help"|"-h"|"--help")
        echo "🚀 OpenAI Token Usage Monitor - Enhanced Features"
        echo "================================================"
        echo ""
        echo "Usage: $0 [option]"
        echo ""
        echo "📊 Monitoring Options:"
        echo "  demo          - Run in demo mode with simulated data"
        echo "  tier1         - Run with Tier 1 limits (100k tokens/month)"
        echo "  tier2         - Run with Tier 2 limits (500k tokens/month)"
        echo "  tier3         - Run with Tier 3 limits (1M tokens/month)"
        echo "  tier4         - Run with Tier 4 limits (5M tokens/month)"
        echo "  tier5         - Run with Tier 5 limits (50M tokens/month)"
        echo ""
        echo "📈 Analytics & Reports:"
        echo "  analytics     - Show usage analytics (last 7 days)"
        echo "  analytics-7   - Show analytics for last 7 days"
        echo "  analytics-30  - Show analytics for last 30 days"
        echo "  export-csv    - Export usage data to CSV format"
        echo "  export-json   - Export usage data to JSON format"
        echo ""
        echo "💰 Budget Management:"
        echo "  budget-10     - Set monthly budget to \$10"
        echo "  budget-50     - Set monthly budget to \$50"
        echo "  budget-100    - Set monthly budget to \$100"
        echo ""
        echo "🔧 Other Options:"
        echo "  help          - Show this help message"
        echo ""
        echo "📋 Examples:"
        echo "  $0 demo              # Test with simulated data"
        echo "  $0 tier2             # Monitor with Tier 2 limits"
        echo "  $0 analytics         # View usage analytics"
        echo "  $0 export-csv        # Export data to CSV"
        echo "  $0 budget-50         # Set \$50 monthly budget"
        echo ""
        echo "🔑 Setup:"
        echo "  export OPENAI_API_KEY='sk-...' && $0 tier1"
        echo ""
        echo "For advanced options: python3 openai_usage_monitor.py --help"
        ;;
    "")
        echo "📊 Starting with default settings (Tier 1)..."
        python3 openai_usage_monitor.py
        ;;
    *)
        echo "❌ Unknown option: $1"
        echo "Run '$0 help' for available options"
        exit 1
        ;;
esac
