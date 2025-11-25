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
    "add-key")
        echo "🔑 Adding new API key..."
        if [ -z "$2" ]; then
            echo "❌ Error: Key name required"
            echo "Usage: $0 add-key <key-name> [description]"
            exit 1
        fi
        if [ -z "$OPENAI_API_KEY" ]; then
            echo "❌ Error: OPENAI_API_KEY environment variable not set"
            exit 1
        fi
        if [ -n "$3" ]; then
            python3 openai_usage_monitor.py --add-key --key-name "$2" --key-description "$3"
        else
            python3 openai_usage_monitor.py --add-key --key-name "$2"
        fi
        ;;
    "list-keys")
        echo "📋 Listing all API keys..."
        python3 openai_usage_monitor.py --list-keys
        ;;
    "remove-key")
        echo "🗑️  Removing API key..."
        if [ -z "$2" ]; then
            echo "❌ Error: Key name required"
            echo "Usage: $0 remove-key <key-name>"
            exit 1
        fi
        python3 openai_usage_monitor.py --remove-key "$2"
        ;;
    "compare-keys")
        echo "📊 Comparing usage across all keys..."
        if [ -n "$2" ]; then
            python3 openai_usage_monitor.py --compare-keys --days "$2"
        else
            python3 openai_usage_monitor.py --compare-keys --days 30
        fi
        ;;
    "all-keys")
        echo "📊 Showing analytics for all keys..."
        if [ -n "$2" ]; then
            python3 openai_usage_monitor.py --all-keys --days "$2"
        else
            python3 openai_usage_monitor.py --all-keys --days 7
        fi
        ;;
    "monitor-key")
        echo "📊 Monitoring specific key..."
        if [ -z "$2" ]; then
            echo "❌ Error: Key ID required"
            echo "Usage: $0 monitor-key <key-id>"
            exit 1
        fi
        python3 openai_usage_monitor.py --key-id "$2"
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
        echo "🔑 Multi-Key Management:"
        echo "  add-key <name> [desc]  - Add a new API key"
        echo "  list-keys              - List all API keys with usage stats"
        echo "  remove-key <name>      - Remove an API key"
        echo "  compare-keys [days]    - Compare usage across all keys (default: 30 days)"
        echo "  all-keys [days]        - Show analytics for all keys (default: 7 days)"
        echo "  monitor-key <key-id>   - Monitor a specific key"
        echo ""
        echo "🔧 Other Options:"
        echo "  help          - Show this help message"
        echo ""
        echo "📋 Examples:"
        echo "  $0 demo                          # Test with simulated data"
        echo "  $0 tier2                         # Monitor with Tier 2 limits"
        echo "  $0 analytics                     # View usage analytics"
        echo "  $0 export-csv                    # Export data to CSV"
        echo "  $0 budget-50                     # Set \$50 monthly budget"
        echo "  $0 add-key \"Production\" \"Main API key\"  # Add new key"
        echo "  $0 list-keys                     # List all keys"
        echo "  $0 compare-keys 30               # Compare keys over 30 days"
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
