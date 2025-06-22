#!/usr/bin/env python3

import json
import sys
import time
from datetime import datetime, timedelta, timezone
import os
import argparse
import pytz
import requests
from typing import Dict, List, Optional, Tuple
import sqlite3
from pathlib import Path


class OpenAIUsageTracker:
    """Track OpenAI API usage and store in local database."""
    
    def __init__(self, api_key: str, db_path: str = "openai_usage.db"):
        self.api_key = api_key
        self.db_path = db_path
        self.base_url = "https://api.openai.com/v1"
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for storing usage data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                start_time TEXT,
                end_time TEXT,
                total_tokens INTEGER DEFAULT 0,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_cost REAL DEFAULT 0.0,
                model TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                timestamp TEXT,
                model TEXT,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                cost REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES usage_sessions (session_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def get_current_usage(self) -> Optional[Dict]:
        """Get current usage from OpenAI API."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Get usage data for current month
            now = datetime.now()
            start_date = now.replace(day=1).strftime("%Y-%m-%d")
            end_date = now.strftime("%Y-%m-%d")
            
            response = requests.get(
                f"{self.base_url}/usage",
                headers=headers,
                params={
                    "start_date": start_date,
                    "end_date": end_date
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error fetching usage data: {e}")
            return None
    
    def get_local_usage_data(self) -> Dict:
        """Get usage data from local database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get active session
        cursor.execute('''
            SELECT * FROM usage_sessions 
            WHERE is_active = 1 
            ORDER BY start_time DESC 
            LIMIT 1
        ''')
        active_session = cursor.fetchone()
        
        # Get recent sessions (last 24 hours)
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        cursor.execute('''
            SELECT * FROM usage_sessions 
            WHERE start_time >= ? 
            ORDER BY start_time DESC
        ''', (yesterday,))
        recent_sessions = cursor.fetchall()
        
        # Get API calls for burn rate calculation
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        cursor.execute('''
            SELECT * FROM api_calls 
            WHERE timestamp >= ? 
            ORDER BY timestamp DESC
        ''', (one_hour_ago,))
        recent_calls = cursor.fetchall()
        
        conn.close()
        
        return {
            'active_session': active_session,
            'recent_sessions': recent_sessions,
            'recent_calls': recent_calls
        }
    
    def create_session(self, session_id: str = None) -> str:
        """Create a new usage session."""
        if not session_id:
            session_id = f"session_{int(time.time())}"
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # End any existing active sessions
        cursor.execute('''
            UPDATE usage_sessions 
            SET is_active = 0, end_time = ? 
            WHERE is_active = 1
        ''', (datetime.now().isoformat(),))
        
        # Create new session
        cursor.execute('''
            INSERT OR REPLACE INTO usage_sessions 
            (session_id, start_time, is_active) 
            VALUES (?, ?, 1)
        ''', (session_id, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        return session_id
    
    def log_api_call(self, session_id: str, model: str, prompt_tokens: int, 
                     completion_tokens: int, cost: float = 0.0):
        """Log an API call to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        total_tokens = prompt_tokens + completion_tokens
        
        # Insert API call
        cursor.execute('''
            INSERT INTO api_calls 
            (session_id, timestamp, model, prompt_tokens, completion_tokens, total_tokens, cost)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, datetime.now().isoformat(), model, prompt_tokens, 
              completion_tokens, total_tokens, cost))
        
        # Update session totals
        cursor.execute('''
            UPDATE usage_sessions 
            SET total_tokens = total_tokens + ?,
                prompt_tokens = prompt_tokens + ?,
                completion_tokens = completion_tokens + ?,
                total_cost = total_cost + ?,
                model = ?
            WHERE session_id = ?
        ''', (total_tokens, prompt_tokens, completion_tokens, cost, model, session_id))
        
        conn.commit()
        conn.close()


def format_time(minutes):
    """Format minutes into human-readable time (e.g., '3h 45m')."""
    if minutes < 60:
        return f"{int(minutes)}m"
    hours = int(minutes // 60)
    mins = int(minutes % 60)
    if mins == 0:
        return f"{hours}h"
    return f"{hours}h {mins}m"


def create_token_progress_bar(percentage, width=50):
    """Create a token usage progress bar with bracket style."""
    filled = int(width * percentage / 100)
    
    # Create the bar with green fill and red empty space
    green_bar = '█' * filled
    red_bar = '░' * (width - filled)
    
    # Color codes
    green = '\033[92m'  # Bright green
    red = '\033[91m'    # Bright red
    reset = '\033[0m'
    
    return f"🟢 [{green}{green_bar}{red}{red_bar}{reset}] {percentage:.1f}%"


def create_time_progress_bar(elapsed_minutes, total_minutes, width=50):
    """Create a time progress bar showing time until reset."""
    if total_minutes <= 0:
        percentage = 0
    else:
        percentage = min(100, (elapsed_minutes / total_minutes) * 100)
    
    filled = int(width * percentage / 100)
    
    # Create the bar with blue fill and red empty space
    blue_bar = '█' * filled
    red_bar = '░' * (width - filled)
    
    # Color codes
    blue = '\033[94m'   # Bright blue
    red = '\033[91m'    # Bright red
    reset = '\033[0m'
    
    remaining_time = format_time(max(0, total_minutes - elapsed_minutes))
    return f"⏰ [{blue}{blue_bar}{red}{red_bar}{reset}] {remaining_time}"


def print_header():
    """Print the stylized header with sparkles."""
    cyan = '\033[96m'
    blue = '\033[94m'
    reset = '\033[0m'
    
    # Sparkle pattern
    sparkles = f"{cyan}✦ ✧ ✦ ✧ {reset}"
    
    print(f"{sparkles}{cyan}OPENAI TOKEN MONITOR{reset} {sparkles}")
    print(f"{blue}{'=' * 60}{reset}")
    print()


def get_velocity_indicator(burn_rate):
    """Get velocity emoji based on burn rate."""
    if burn_rate < 50:
        return '🐌'  # Slow
    elif burn_rate < 150:
        return '➡️'  # Normal
    elif burn_rate < 300:
        return '🚀'  # Fast
    else:
        return '⚡'  # Very fast


def calculate_hourly_burn_rate(recent_calls, current_time):
    """Calculate burn rate based on API calls in the last hour."""
    if not recent_calls:
        return 0
    
    total_tokens = sum(call[5] for call in recent_calls)  # total_tokens is index 5
    return total_tokens / 60 if total_tokens > 0 else 0


def get_next_reset_time(current_time, custom_reset_hour=None, timezone_str='UTC'):
    """Calculate next token reset time (monthly for OpenAI)."""
    try:
        target_tz = pytz.timezone(timezone_str)
    except pytz.exceptions.UnknownTimeZoneError:
        print(f"Warning: Unknown timezone '{timezone_str}', using UTC")
        target_tz = pytz.timezone('UTC')

    if current_time.tzinfo is not None:
        target_time = current_time.astimezone(target_tz)
    else:
        target_time = target_tz.localize(current_time)

    # For OpenAI, reset is monthly (first day of next month)
    if target_time.month == 12:
        next_reset = target_tz.localize(
            datetime(target_time.year + 1, 1, 1)
        )
    else:
        next_reset = target_tz.localize(
            datetime(target_time.year, target_time.month + 1, 1)
        )

    if current_time.tzinfo is not None and current_time.tzinfo != target_tz:
        next_reset = next_reset.astimezone(current_time.tzinfo)

    return next_reset


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='OpenAI Token Monitor - Real-time token usage monitoring')
    parser.add_argument('--api-key', type=str,
                        help='OpenAI API key (or set OPENAI_API_KEY environment variable)')
    parser.add_argument('--plan', type=str, default='tier1',
                        choices=['tier1', 'tier2', 'tier3', 'tier4', 'tier5', 'custom'],
                        help='OpenAI usage tier (default: tier1)')
    parser.add_argument('--limit', type=int,
                        help='Custom token limit per month')
    parser.add_argument('--timezone', type=str, default='UTC',
                        help='Timezone for reset times (default: UTC). Examples: US/Eastern, Asia/Tokyo, Europe/London')
    parser.add_argument('--db-path', type=str, default='openai_usage.db',
                        help='Path to SQLite database file')
    parser.add_argument('--demo', action='store_true',
                        help='Run in demo mode with simulated data')
    return parser.parse_args()


def get_token_limit(plan, custom_limit=None):
    """Get token limit based on plan type."""
    if plan == 'custom' and custom_limit:
        return custom_limit

    # OpenAI usage tiers (approximate monthly limits)
    limits = {
        'tier1': 100000,      # $100/month
        'tier2': 500000,      # $500/month
        'tier3': 1000000,     # $1000/month
        'tier4': 5000000,     # $5000/month
        'tier5': 50000000,    # $50000/month
    }
    return limits.get(plan, 100000)


def create_demo_session(tracker):
    """Create demo session with simulated data for testing."""
    session_id = tracker.create_session("demo_session")

    # Simulate some API calls over the last hour
    now = datetime.now()
    for i in range(10):
        # Simulate calls at different times in the last hour
        call_time = now - timedelta(minutes=60-i*6)

        # Simulate different models and token usage
        models = ['gpt-4', 'gpt-3.5-turbo', 'gpt-4-turbo']
        model = models[i % len(models)]
        prompt_tokens = 100 + (i * 50)
        completion_tokens = 50 + (i * 25)
        cost = (prompt_tokens * 0.00003) + (completion_tokens * 0.00006)

        # Manually insert with specific timestamp
        conn = sqlite3.connect(tracker.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO api_calls
            (session_id, timestamp, model, prompt_tokens, completion_tokens, total_tokens, cost)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, call_time.isoformat(), model, prompt_tokens,
              completion_tokens, prompt_tokens + completion_tokens, cost))
        conn.commit()
        conn.close()

    # Update session totals
    conn = sqlite3.connect(tracker.db_path)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT SUM(total_tokens), SUM(prompt_tokens), SUM(completion_tokens), SUM(cost)
        FROM api_calls WHERE session_id = ?
    ''', (session_id,))
    totals = cursor.fetchone()

    cursor.execute('''
        UPDATE usage_sessions
        SET total_tokens = ?, prompt_tokens = ?, completion_tokens = ?, total_cost = ?, model = 'gpt-4'
        WHERE session_id = ?
    ''', (*totals, session_id))

    conn.commit()
    conn.close()

    return session_id


def main():
    """Main monitoring loop."""
    args = parse_args()

    # Get API key
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')
    if not api_key and not args.demo:
        print("Error: OpenAI API key required. Set OPENAI_API_KEY environment variable or use --api-key")
        sys.exit(1)

    # Initialize tracker
    tracker = OpenAIUsageTracker(api_key or "demo", args.db_path)

    # Get token limit
    token_limit = get_token_limit(args.plan, args.limit)

    # Create demo session if in demo mode
    if args.demo:
        print("Running in demo mode with simulated data...")
        create_demo_session(tracker)
        time.sleep(1)

    try:
        # Initial screen clear and hide cursor
        os.system('clear' if os.name == 'posix' else 'cls')
        print('\033[?25l', end='', flush=True)  # Hide cursor

        while True:
            # Move cursor to top without clearing
            print('\033[H', end='', flush=True)

            # Get usage data
            data = tracker.get_local_usage_data()
            active_session = data['active_session']
            recent_calls = data['recent_calls']

            if not active_session:
                if not args.demo:
                    print("No active session found. Creating new session...")
                    tracker.create_session()
                    continue
                else:
                    print("No active session found in demo mode")
                    time.sleep(3)
                    continue

            # Extract data from active session
            tokens_used = active_session[4]  # total_tokens
            prompt_tokens = active_session[5]  # prompt_tokens
            completion_tokens = active_session[6]  # completion_tokens
            total_cost = active_session[7]  # total_cost
            model = active_session[8] or "gpt-4"  # model

            usage_percentage = (tokens_used / token_limit) * 100 if token_limit > 0 else 0
            tokens_left = token_limit - tokens_used

            # Time calculations
            start_time_str = active_session[2]  # start_time
            if start_time_str:
                start_time = datetime.fromisoformat(start_time_str)
                current_time = datetime.now()
                # Make both timezone-aware or both naive
                if start_time.tzinfo is not None:
                    current_time = current_time.replace(tzinfo=timezone.utc)
                elapsed = current_time - start_time
                elapsed_minutes = elapsed.total_seconds() / 60
            else:
                elapsed_minutes = 0
                current_time = datetime.now()

            # Calculate burn rate from recent API calls
            burn_rate = calculate_hourly_burn_rate(recent_calls, current_time)

            # Reset time calculation (monthly for OpenAI)
            # Ensure current_time is timezone-aware for reset calculation
            if current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=timezone.utc)
            reset_time = get_next_reset_time(current_time, None, args.timezone)

            # Calculate time to reset
            time_to_reset = reset_time - current_time
            minutes_to_reset = time_to_reset.total_seconds() / 60
            days_to_reset = time_to_reset.days

            # Predicted end calculation
            if burn_rate > 0 and tokens_left > 0:
                minutes_to_depletion = tokens_left / burn_rate
                predicted_end_time = current_time + timedelta(minutes=minutes_to_depletion)
            else:
                predicted_end_time = reset_time

            # Color codes
            cyan = '\033[96m'
            green = '\033[92m'
            blue = '\033[94m'
            red = '\033[91m'
            yellow = '\033[93m'
            white = '\033[97m'
            gray = '\033[90m'
            reset = '\033[0m'

            # Display header
            print_header()

            # Token Usage section
            print(f"📊 {white}Token Usage:{reset}    {create_token_progress_bar(usage_percentage)}")
            print()

            # Time to Reset section (monthly progress)
            month_start = current_time.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            month_elapsed = (current_time - month_start).total_seconds() / 60  # minutes
            month_total = (reset_time - month_start).total_seconds() / 60  # minutes
            print(f"⏳ {white}Time to Reset:{reset}  {create_time_progress_bar(month_elapsed, month_total)}")
            print()

            # Detailed stats
            print(f"🎯 {white}Tokens:{reset}         {white}{tokens_used:,}{reset} / {gray}{token_limit:,}{reset} ({cyan}{tokens_left:,} left{reset})")
            print(f"💰 {white}Cost:{reset}           ${white}{total_cost:.4f}{reset}")
            print(f"🤖 {white}Model:{reset}          {yellow}{model}{reset}")
            print(f"🔥 {white}Burn Rate:{reset}      {yellow}{burn_rate:.1f}{reset} {gray}tokens/min{reset}")
            print()

            # Predictions - convert to configured timezone for display
            try:
                local_tz = pytz.timezone(args.timezone)
            except:
                local_tz = pytz.timezone('UTC')
            predicted_end_local = predicted_end_time.astimezone(local_tz)
            reset_time_local = reset_time.astimezone(local_tz)

            predicted_end_str = predicted_end_local.strftime("%Y-%m-%d %H:%M")
            reset_time_str = reset_time_local.strftime("%Y-%m-%d %H:%M")
            print(f"🏁 {white}Predicted End:{reset} {predicted_end_str}")
            print(f"🔄 {white}Monthly Reset:{reset} {reset_time_str} ({days_to_reset} days)")
            print()

            # Notifications
            show_exceed_notification = tokens_used > token_limit

            if show_exceed_notification:
                print(f"🚨 {red}TOKENS EXCEEDED LIMIT! ({tokens_used:,} > {token_limit:,}){reset}")
                print()

            # Warning if tokens will run out before reset
            if predicted_end_time < reset_time and burn_rate > 0:
                print(f"⚠️  {red}Tokens will run out BEFORE monthly reset!{reset}")
                print()

            # Status line
            current_time_str = datetime.now().strftime("%H:%M:%S")
            status = "Demo Mode" if args.demo else "Live Monitoring"
            print(f"⏰ {gray}{current_time_str}{reset} 📝 {cyan}{status}...{reset} | {gray}Ctrl+C to exit{reset} 🟨")

            # Clear any remaining lines below to prevent artifacts
            print('\033[J', end='', flush=True)

            time.sleep(3)

    except KeyboardInterrupt:
        # Show cursor before exiting
        print('\033[?25h', end='', flush=True)
        print(f"\n\n{cyan}Monitoring stopped.{reset}")
        # Clear the terminal
        os.system('clear' if os.name == 'posix' else 'cls')
        sys.exit(0)
    except Exception as e:
        # Show cursor on any error
        print('\033[?25h', end='', flush=True)
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
