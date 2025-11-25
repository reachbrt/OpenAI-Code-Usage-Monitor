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
import hashlib


class OpenAIUsageTracker:
    """Track OpenAI API usage and store in local database."""

    def __init__(self, api_key: str = None, db_path: str = "openai_usage.db", key_id: str = None):
        self.api_key = api_key
        self.db_path = db_path
        self.base_url = "https://api.openai.com/v1"
        self.key_id = key_id
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database for storing usage data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # New table for API keys/users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id TEXT UNIQUE,
                key_name TEXT,
                key_description TEXT,
                api_key_hash TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT UNIQUE,
                key_id TEXT,
                start_time TEXT,
                end_time TEXT,
                total_tokens INTEGER DEFAULT 0,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_cost REAL DEFAULT 0.0,
                model TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (key_id) REFERENCES api_keys (key_id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                key_id TEXT,
                timestamp TEXT,
                model TEXT,
                prompt_tokens INTEGER,
                completion_tokens INTEGER,
                total_tokens INTEGER,
                cost REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES usage_sessions (session_id),
                FOREIGN KEY (key_id) REFERENCES api_keys (key_id)
            )
        ''')

        # New table for daily usage summaries
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                key_id TEXT,
                total_tokens INTEGER DEFAULT 0,
                total_cost REAL DEFAULT 0.0,
                api_calls_count INTEGER DEFAULT 0,
                models_used TEXT,
                avg_burn_rate REAL DEFAULT 0.0,
                peak_burn_rate REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, key_id),
                FOREIGN KEY (key_id) REFERENCES api_keys (key_id)
            )
        ''')

        # New table for usage alerts and notifications
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id TEXT,
                alert_type TEXT,
                threshold_value REAL,
                current_value REAL,
                message TEXT,
                is_active BOOLEAN DEFAULT 1,
                triggered_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (key_id) REFERENCES api_keys (key_id)
            )
        ''')

        # New table for budget tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS budget_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month_year TEXT,
                key_id TEXT,
                budget_limit REAL,
                token_limit INTEGER,
                alert_thresholds TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(month_year, key_id),
                FOREIGN KEY (key_id) REFERENCES api_keys (key_id)
            )
        ''')

        # Migration: Add key_id column to existing tables if not exists
        self._migrate_schema(cursor)

        conn.commit()
        conn.close()

    def _migrate_schema(self, cursor):
        """Migrate existing database schema to support multi-key tracking."""
        # Check if key_id column exists in usage_sessions
        cursor.execute("PRAGMA table_info(usage_sessions)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'key_id' not in columns:
            try:
                cursor.execute("ALTER TABLE usage_sessions ADD COLUMN key_id TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists

        # Check if key_id column exists in api_calls
        cursor.execute("PRAGMA table_info(api_calls)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'key_id' not in columns:
            try:
                cursor.execute("ALTER TABLE api_calls ADD COLUMN key_id TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists

        # Check if key_id column exists in daily_usage
        cursor.execute("PRAGMA table_info(daily_usage)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'key_id' not in columns:
            try:
                cursor.execute("ALTER TABLE daily_usage ADD COLUMN key_id TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists

        # Check if key_id column exists in usage_alerts
        cursor.execute("PRAGMA table_info(usage_alerts)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'key_id' not in columns:
            try:
                cursor.execute("ALTER TABLE usage_alerts ADD COLUMN key_id TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists

        # Check if key_id column exists in budget_settings
        cursor.execute("PRAGMA table_info(budget_settings)")
        columns = [col[1] for col in cursor.fetchall()]

        if 'key_id' not in columns:
            try:
                cursor.execute("ALTER TABLE budget_settings ADD COLUMN key_id TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists

    # ============================================================================
    # KEY MANAGEMENT METHODS
    # ============================================================================

    def _hash_api_key(self, api_key: str) -> str:
        """Hash API key for secure storage."""
        return hashlib.sha256(api_key.encode()).hexdigest()

    def _mask_api_key(self, api_key: str) -> str:
        """Mask API key for display (show only last 4 characters)."""
        if len(api_key) <= 4:
            return "****"
        return f"sk-...{api_key[-4:]}"

    def add_key(self, api_key: str, key_name: str, key_description: str = "") -> str:
        """Add a new API key to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Generate unique key_id
        key_id = f"key_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        api_key_hash = self._hash_api_key(api_key)

        try:
            cursor.execute('''
                INSERT INTO api_keys (key_id, key_name, key_description, api_key_hash, is_active)
                VALUES (?, ?, ?, ?, 1)
            ''', (key_id, key_name, key_description, api_key_hash))

            conn.commit()
            conn.close()
            return key_id
        except sqlite3.IntegrityError:
            conn.close()
            raise ValueError(f"Key with name '{key_name}' already exists")

    def remove_key(self, key_id: str = None, key_name: str = None):
        """Remove an API key from the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if key_id:
            cursor.execute("DELETE FROM api_keys WHERE key_id = ?", (key_id,))
        elif key_name:
            cursor.execute("DELETE FROM api_keys WHERE key_name = ?", (key_name,))
        else:
            conn.close()
            raise ValueError("Either key_id or key_name must be provided")

        conn.commit()
        conn.close()

    def list_keys(self) -> List[Dict]:
        """List all API keys in the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT key_id, key_name, key_description, is_active, created_at
            FROM api_keys
            ORDER BY created_at DESC
        ''')

        keys = []
        for row in cursor.fetchall():
            keys.append({
                'key_id': row[0],
                'key_name': row[1],
                'key_description': row[2],
                'is_active': bool(row[3]),
                'created_at': row[4]
            })

        conn.close()
        return keys

    def get_key(self, key_id: str = None, key_name: str = None) -> Optional[Dict]:
        """Get a specific API key by ID or name."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if key_id:
            cursor.execute('''
                SELECT key_id, key_name, key_description, is_active, created_at
                FROM api_keys WHERE key_id = ?
            ''', (key_id,))
        elif key_name:
            cursor.execute('''
                SELECT key_id, key_name, key_description, is_active, created_at
                FROM api_keys WHERE key_name = ?
            ''', (key_name,))
        else:
            conn.close()
            return None

        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'key_id': row[0],
                'key_name': row[1],
                'key_description': row[2],
                'is_active': bool(row[3]),
                'created_at': row[4]
            }
        return None

    def update_key_status(self, key_id: str, is_active: bool):
        """Enable or disable an API key."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE api_keys SET is_active = ? WHERE key_id = ?
        ''', (1 if is_active else 0, key_id))

        conn.commit()
        conn.close()

    def get_key_usage_summary(self, key_id: str, days: int = 30) -> Dict:
        """Get usage summary for a specific key."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get total usage for the key
        cursor.execute('''
            SELECT
                SUM(total_tokens) as total_tokens,
                SUM(cost) as total_cost,
                COUNT(*) as total_calls
            FROM api_calls
            WHERE key_id = ? AND timestamp >= DATETIME('now', '-{} days')
        '''.format(days), (key_id,))

        result = cursor.fetchone()
        conn.close()

        return {
            'key_id': key_id,
            'total_tokens': result[0] or 0,
            'total_cost': result[1] or 0.0,
            'total_calls': result[2] or 0,
            'days': days
        }

    # ============================================================================
    # END KEY MANAGEMENT METHODS
    # ============================================================================

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
    
    def create_session(self, session_id: str = None, key_id: str = None) -> str:
        """Create a new usage session."""
        if not session_id:
            session_id = f"session_{int(time.time())}"

        # Use instance key_id if not provided
        if key_id is None:
            key_id = self.key_id

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # End any existing active sessions for this key
        if key_id:
            cursor.execute('''
                UPDATE usage_sessions
                SET is_active = 0, end_time = ?
                WHERE is_active = 1 AND key_id = ?
            ''', (datetime.now().isoformat(), key_id))
        else:
            cursor.execute('''
                UPDATE usage_sessions
                SET is_active = 0, end_time = ?
                WHERE is_active = 1 AND key_id IS NULL
            ''', (datetime.now().isoformat(),))

        # Create new session
        cursor.execute('''
            INSERT OR REPLACE INTO usage_sessions
            (session_id, key_id, start_time, is_active)
            VALUES (?, ?, ?, 1)
        ''', (session_id, key_id, datetime.now().isoformat()))

        conn.commit()
        conn.close()

        return session_id
    
    def log_api_call(self, session_id: str, model: str, prompt_tokens: int,
                     completion_tokens: int, cost: float = 0.0, key_id: str = None):
        """Log an API call to the database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Use instance key_id if not provided
        if key_id is None:
            key_id = self.key_id

        total_tokens = prompt_tokens + completion_tokens

        # Insert API call
        cursor.execute('''
            INSERT INTO api_calls
            (session_id, key_id, timestamp, model, prompt_tokens, completion_tokens, total_tokens, cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, key_id, datetime.now().isoformat(), model, prompt_tokens,
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

    def update_daily_usage(self, key_id: str = None):
        """Update daily usage summary."""
        today = datetime.now().strftime("%Y-%m-%d")

        # Use instance key_id if not provided
        if key_id is None:
            key_id = self.key_id

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get today's usage data for this key
        if key_id:
            cursor.execute('''
                SELECT
                    SUM(total_tokens) as total_tokens,
                    SUM(cost) as total_cost,
                    COUNT(*) as api_calls_count,
                    GROUP_CONCAT(DISTINCT model) as models_used
                FROM api_calls
                WHERE DATE(timestamp) = ? AND key_id = ?
            ''', (today, key_id))
        else:
            cursor.execute('''
                SELECT
                    SUM(total_tokens) as total_tokens,
                    SUM(cost) as total_cost,
                    COUNT(*) as api_calls_count,
                    GROUP_CONCAT(DISTINCT model) as models_used
                FROM api_calls
                WHERE DATE(timestamp) = ? AND key_id IS NULL
            ''', (today,))

        result = cursor.fetchone()
        if result and result[0]:
            total_tokens, total_cost, api_calls_count, models_used = result

            # Calculate burn rates for today
            if key_id:
                cursor.execute('''
                    SELECT total_tokens, timestamp FROM api_calls
                    WHERE DATE(timestamp) = ? AND key_id = ?
                    ORDER BY timestamp
                ''', (today, key_id))
            else:
                cursor.execute('''
                    SELECT total_tokens, timestamp FROM api_calls
                    WHERE DATE(timestamp) = ? AND key_id IS NULL
                    ORDER BY timestamp
                ''', (today,))

            calls = cursor.fetchall()
            burn_rates = []

            if len(calls) > 1:
                for i in range(1, len(calls)):
                    prev_time = datetime.fromisoformat(calls[i-1][1])
                    curr_time = datetime.fromisoformat(calls[i][1])
                    time_diff = (curr_time - prev_time).total_seconds() / 60  # minutes

                    if time_diff > 0:
                        tokens_diff = calls[i][0] - calls[i-1][0]
                        burn_rate = tokens_diff / time_diff
                        burn_rates.append(burn_rate)

            avg_burn_rate = sum(burn_rates) / len(burn_rates) if burn_rates else 0
            peak_burn_rate = max(burn_rates) if burn_rates else 0

            # Insert or update daily summary
            cursor.execute('''
                INSERT OR REPLACE INTO daily_usage
                (date, key_id, total_tokens, total_cost, api_calls_count, models_used, avg_burn_rate, peak_burn_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (today, key_id, total_tokens, total_cost, api_calls_count, models_used, avg_burn_rate, peak_burn_rate))

        conn.commit()
        conn.close()

    def get_usage_analytics(self, days=7, key_id: str = None) -> Dict:
        """Get usage analytics for the last N days."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Use instance key_id if not provided
        if key_id is None:
            key_id = self.key_id

        # Get daily usage for last N days
        if key_id:
            cursor.execute('''
                SELECT * FROM daily_usage
                WHERE date >= DATE('now', '-{} days') AND key_id = ?
                ORDER BY date DESC
            '''.format(days), (key_id,))
        else:
            cursor.execute('''
                SELECT * FROM daily_usage
                WHERE date >= DATE('now', '-{} days') AND key_id IS NULL
                ORDER BY date DESC
            '''.format(days))

        daily_data = cursor.fetchall()

        # Get model usage breakdown
        if key_id:
            cursor.execute('''
                SELECT
                    model,
                    SUM(total_tokens) as total_tokens,
                    SUM(cost) as total_cost,
                    COUNT(*) as call_count
                FROM api_calls
                WHERE timestamp >= DATETIME('now', '-{} days') AND key_id = ?
                GROUP BY model
                ORDER BY total_tokens DESC
            '''.format(days), (key_id,))
        else:
            cursor.execute('''
                SELECT
                    model,
                    SUM(total_tokens) as total_tokens,
                    SUM(cost) as total_cost,
                    COUNT(*) as call_count
                FROM api_calls
                WHERE timestamp >= DATETIME('now', '-{} days') AND key_id IS NULL
                GROUP BY model
                ORDER BY total_tokens DESC
            '''.format(days))

        model_breakdown = cursor.fetchall()

        # Get hourly usage pattern
        if key_id:
            cursor.execute('''
                SELECT
                    strftime('%H', timestamp) as hour,
                    AVG(total_tokens) as avg_tokens,
                    COUNT(*) as call_count
                FROM api_calls
                WHERE timestamp >= DATETIME('now', '-{} days') AND key_id = ?
                GROUP BY strftime('%H', timestamp)
                ORDER BY hour
            '''.format(days), (key_id,))
        else:
            cursor.execute('''
                SELECT
                    strftime('%H', timestamp) as hour,
                    AVG(total_tokens) as avg_tokens,
                    COUNT(*) as call_count
                FROM api_calls
                WHERE timestamp >= DATETIME('now', '-{} days') AND key_id IS NULL
                GROUP BY strftime('%H', timestamp)
                ORDER BY hour
            '''.format(days))

        hourly_pattern = cursor.fetchall()

        conn.close()

        return {
            'daily_data': daily_data,
            'model_breakdown': model_breakdown,
            'hourly_pattern': hourly_pattern,
            'period_days': days,
            'key_id': key_id
        }

    def get_all_keys_analytics(self, days=7) -> List[Dict]:
        """Get analytics for all keys."""
        keys = self.list_keys()
        all_analytics = []

        for key in keys:
            if key['is_active']:
                analytics = self.get_usage_analytics(days=days, key_id=key['key_id'])
                usage_summary = self.get_key_usage_summary(key['key_id'], days=days)

                all_analytics.append({
                    'key_info': key,
                    'analytics': analytics,
                    'summary': usage_summary
                })

        return all_analytics

    def compare_keys(self, days=30) -> Dict:
        """Compare usage across all keys."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get usage summary for each key
        cursor.execute('''
            SELECT
                k.key_id,
                k.key_name,
                SUM(a.total_tokens) as total_tokens,
                SUM(a.cost) as total_cost,
                COUNT(a.id) as total_calls
            FROM api_keys k
            LEFT JOIN api_calls a ON k.key_id = a.key_id
            WHERE a.timestamp >= DATETIME('now', '-{} days')
            GROUP BY k.key_id, k.key_name
            ORDER BY total_tokens DESC
        '''.format(days))

        key_comparisons = []
        for row in cursor.fetchall():
            key_comparisons.append({
                'key_id': row[0],
                'key_name': row[1],
                'total_tokens': row[2] or 0,
                'total_cost': row[3] or 0.0,
                'total_calls': row[4] or 0
            })

        # Get total across all keys
        cursor.execute('''
            SELECT
                SUM(total_tokens) as total_tokens,
                SUM(cost) as total_cost,
                COUNT(*) as total_calls
            FROM api_calls
            WHERE timestamp >= DATETIME('now', '-{} days')
        '''.format(days))

        total_row = cursor.fetchone()
        conn.close()

        return {
            'key_comparisons': key_comparisons,
            'total_tokens': total_row[0] or 0,
            'total_cost': total_row[1] or 0.0,
            'total_calls': total_row[2] or 0,
            'period_days': days
        }

    def check_and_create_alerts(self, current_usage: Dict):
        """Check usage against thresholds and create alerts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Define alert thresholds
        alerts_to_check = [
            ('token_usage_50', 0.5, 'Token usage exceeded 50%'),
            ('token_usage_75', 0.75, 'Token usage exceeded 75%'),
            ('token_usage_90', 0.9, 'Token usage exceeded 90%'),
            ('cost_threshold_10', 10.0, 'Monthly cost exceeded $10'),
            ('cost_threshold_50', 50.0, 'Monthly cost exceeded $50'),
            ('high_burn_rate', 500.0, 'High burn rate detected (>500 tokens/min)'),
        ]

        tokens_used = current_usage.get('tokens_used', 0)
        token_limit = current_usage.get('token_limit', 1)
        total_cost = current_usage.get('total_cost', 0)
        burn_rate = current_usage.get('burn_rate', 0)

        usage_percentage = tokens_used / token_limit if token_limit > 0 else 0

        for alert_type, threshold, message in alerts_to_check:
            should_trigger = False
            current_value = 0

            if 'token_usage' in alert_type:
                should_trigger = usage_percentage >= threshold
                current_value = usage_percentage
            elif 'cost_threshold' in alert_type:
                should_trigger = total_cost >= threshold
                current_value = total_cost
            elif 'burn_rate' in alert_type:
                should_trigger = burn_rate >= threshold
                current_value = burn_rate

            if should_trigger:
                # Check if alert already exists for today
                today = datetime.now().strftime("%Y-%m-%d")
                cursor.execute('''
                    SELECT id FROM usage_alerts
                    WHERE alert_type = ? AND DATE(triggered_at) = ?
                ''', (alert_type, today))

                if not cursor.fetchone():
                    # Create new alert
                    cursor.execute('''
                        INSERT INTO usage_alerts
                        (alert_type, threshold_value, current_value, message)
                        VALUES (?, ?, ?, ?)
                    ''', (alert_type, threshold, current_value, message))

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
    parser.add_argument('--analytics', action='store_true',
                        help='Show usage analytics and exit')
    parser.add_argument('--export', type=str, choices=['csv', 'json'],
                        help='Export usage data to CSV or JSON format')
    parser.add_argument('--days', type=int, default=7,
                        help='Number of days for analytics (default: 7)')
    parser.add_argument('--budget', type=float,
                        help='Set monthly budget limit in USD')

    # Multi-key management arguments
    parser.add_argument('--add-key', action='store_true',
                        help='Add a new API key')
    parser.add_argument('--key-name', type=str,
                        help='Name for the API key (required with --add-key)')
    parser.add_argument('--key-description', type=str, default='',
                        help='Description for the API key')
    parser.add_argument('--list-keys', action='store_true',
                        help='List all API keys')
    parser.add_argument('--remove-key', type=str,
                        help='Remove an API key by name or ID')
    parser.add_argument('--key-id', type=str,
                        help='Specific key ID to use for monitoring/analytics')
    parser.add_argument('--compare-keys', action='store_true',
                        help='Compare usage across all keys')
    parser.add_argument('--all-keys', action='store_true',
                        help='Show analytics for all keys')

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
    session_id = tracker.create_session("demo_session", key_id=tracker.key_id)

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
            (session_id, key_id, timestamp, model, prompt_tokens, completion_tokens, total_tokens, cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (session_id, tracker.key_id, call_time.isoformat(), model, prompt_tokens,
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


def display_analytics(tracker, days=7):
    """Display usage analytics in a beautiful format."""
    analytics = tracker.get_usage_analytics(days)

    # Color codes
    cyan = '\033[96m'
    green = '\033[92m'
    blue = '\033[94m'
    yellow = '\033[93m'
    white = '\033[97m'
    gray = '\033[90m'
    reset = '\033[0m'

    print(f"\n{cyan}📊 USAGE ANALYTICS - Last {days} Days{reset}")
    print(f"{blue}{'=' * 60}{reset}\n")

    # Daily usage summary
    if analytics['daily_data']:
        print(f"{white}📅 Daily Usage Summary:{reset}")
        print(f"{'Date':<12} {'Tokens':<10} {'Cost':<8} {'Calls':<6} {'Avg Rate':<10} {'Peak Rate':<10}")
        print(f"{gray}{'-' * 70}{reset}")

        total_tokens = 0
        total_cost = 0.0
        total_calls = 0

        for day in analytics['daily_data']:
            date = day[1]
            tokens = day[2] or 0
            cost = day[3] or 0.0
            calls = day[4] or 0
            avg_rate = day[6] or 0.0
            peak_rate = day[7] or 0.0

            total_tokens += tokens
            total_cost += cost
            total_calls += calls

            print(f"{date:<12} {tokens:<10,} ${cost:<7.2f} {calls:<6} {avg_rate:<10.1f} {peak_rate:<10.1f}")

        print(f"{gray}{'-' * 70}{reset}")
        print(f"{'TOTAL':<12} {total_tokens:<10,} ${total_cost:<7.2f} {total_calls:<6}")
        print()

    # Model breakdown
    if analytics['model_breakdown']:
        print(f"{white}🤖 Model Usage Breakdown:{reset}")
        print(f"{'Model':<15} {'Tokens':<12} {'Cost':<10} {'Calls':<8} {'%':<6}")
        print(f"{gray}{'-' * 55}{reset}")

        total_model_tokens = sum(model[1] for model in analytics['model_breakdown'])

        for model in analytics['model_breakdown']:
            model_name = model[0]
            tokens = model[1]
            cost = model[2]
            calls = model[3]
            percentage = (tokens / total_model_tokens * 100) if total_model_tokens > 0 else 0

            print(f"{model_name:<15} {tokens:<12,} ${cost:<9.2f} {calls:<8} {percentage:<5.1f}%")
        print()

    # Hourly usage pattern
    if analytics['hourly_pattern']:
        print(f"{white}⏰ Hourly Usage Pattern:{reset}")
        print(f"{'Hour':<6} {'Avg Tokens':<12} {'Calls':<8} {'Activity':<20}")
        print(f"{gray}{'-' * 50}{reset}")

        max_tokens = max(hour[1] for hour in analytics['hourly_pattern']) if analytics['hourly_pattern'] else 1

        for hour in analytics['hourly_pattern']:
            hour_str = f"{int(hour[0]):02d}:00"
            avg_tokens = hour[1] or 0
            calls = hour[2] or 0

            # Create simple bar chart
            bar_length = int((avg_tokens / max_tokens) * 15) if max_tokens > 0 else 0
            bar = '█' * bar_length + '░' * (15 - bar_length)

            print(f"{hour_str:<6} {avg_tokens:<12.1f} {calls:<8} {green}{bar}{reset}")
        print()


def export_usage_data(tracker, format_type='csv', days=7):
    """Export usage data to CSV or JSON."""
    analytics = tracker.get_usage_analytics(days)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format_type == 'csv':
        import csv
        filename = f"openai_usage_{timestamp}.csv"

        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)

            # Daily usage data
            writer.writerow(['=== DAILY USAGE ==='])
            writer.writerow(['Date', 'Total Tokens', 'Total Cost', 'API Calls', 'Avg Burn Rate', 'Peak Burn Rate'])

            for day in analytics['daily_data']:
                writer.writerow([day[1], day[2], day[3], day[4], day[6], day[7]])

            writer.writerow([])  # Empty row

            # Model breakdown
            writer.writerow(['=== MODEL BREAKDOWN ==='])
            writer.writerow(['Model', 'Total Tokens', 'Total Cost', 'Call Count'])

            for model in analytics['model_breakdown']:
                writer.writerow([model[0], model[1], model[2], model[3]])

        print(f"✅ Data exported to {filename}")

    elif format_type == 'json':
        import json
        filename = f"openai_usage_{timestamp}.json"

        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'period_days': days,
            'daily_usage': [
                {
                    'date': day[1],
                    'total_tokens': day[2],
                    'total_cost': day[3],
                    'api_calls': day[4],
                    'avg_burn_rate': day[6],
                    'peak_burn_rate': day[7]
                } for day in analytics['daily_data']
            ],
            'model_breakdown': [
                {
                    'model': model[0],
                    'total_tokens': model[1],
                    'total_cost': model[2],
                    'call_count': model[3]
                } for model in analytics['model_breakdown']
            ],
            'hourly_pattern': [
                {
                    'hour': hour[0],
                    'avg_tokens': hour[1],
                    'call_count': hour[2]
                } for hour in analytics['hourly_pattern']
            ]
        }

        with open(filename, 'w') as jsonfile:
            json.dump(export_data, jsonfile, indent=2)

        print(f"✅ Data exported to {filename}")


def main():
    """Main monitoring loop."""
    args = parse_args()

    # Get API key
    api_key = args.api_key or os.getenv('OPENAI_API_KEY')

    # Initialize tracker (key_id will be set later if needed)
    tracker = OpenAIUsageTracker(api_key or "demo", args.db_path, key_id=args.key_id)

    # Handle key management commands
    if args.add_key:
        if not api_key:
            print("❌ Error: API key required. Use --api-key or set OPENAI_API_KEY")
            sys.exit(1)
        if not args.key_name:
            print("❌ Error: --key-name required when adding a key")
            sys.exit(1)

        try:
            key_id = tracker.add_key(api_key, args.key_name, args.key_description)
            print(f"✅ API key added successfully!")
            print(f"   Key ID: {key_id}")
            print(f"   Name: {args.key_name}")
            if args.key_description:
                print(f"   Description: {args.key_description}")
        except ValueError as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
        return

    if args.list_keys:
        keys = tracker.list_keys()
        if not keys:
            print("📋 No API keys found. Add one with --add-key")
            return

        print("\n" + "="*80)
        print("📋 API KEYS")
        print("="*80 + "\n")

        for key in keys:
            status = "🟢 Active" if key['is_active'] else "🔴 Inactive"
            print(f"{status} {key['key_name']}")
            print(f"   ID: {key['key_id']}")
            if key['key_description']:
                print(f"   Description: {key['key_description']}")
            print(f"   Created: {key['created_at']}")

            # Get usage summary
            summary = tracker.get_key_usage_summary(key['key_id'], days=30)
            print(f"   Usage (30 days): {summary['total_tokens']:,} tokens, ${summary['total_cost']:.2f}, {summary['total_calls']} calls")
            print()

        return

    if args.remove_key:
        try:
            tracker.remove_key(key_name=args.remove_key)
            print(f"✅ API key '{args.remove_key}' removed successfully")
        except Exception as e:
            print(f"❌ Error removing key: {e}")
            sys.exit(1)
        return

    if args.compare_keys:
        comparison = tracker.compare_keys(days=args.days)

        print("\n" + "="*80)
        print(f"📊 KEY COMPARISON - Last {args.days} Days")
        print("="*80 + "\n")

        if not comparison['key_comparisons']:
            print("No usage data found for any keys")
            return

        # Print header
        print(f"{'Key Name':<20} {'Tokens':>15} {'Cost':>12} {'Calls':>10} {'%':>8}")
        print("-" * 80)

        # Print each key
        for key_data in comparison['key_comparisons']:
            percentage = (key_data['total_tokens'] / comparison['total_tokens'] * 100) if comparison['total_tokens'] > 0 else 0
            print(f"{key_data['key_name']:<20} {key_data['total_tokens']:>15,} ${key_data['total_cost']:>10.2f} {key_data['total_calls']:>10} {percentage:>7.1f}%")

        print("-" * 80)
        print(f"{'TOTAL':<20} {comparison['total_tokens']:>15,} ${comparison['total_cost']:>10.2f} {comparison['total_calls']:>10} {'100.0':>7}%")
        print()
        return

    if args.all_keys:
        all_analytics = tracker.get_all_keys_analytics(days=args.days)

        if not all_analytics:
            print("No active keys found")
            return

        for key_analytics in all_analytics:
            key_info = key_analytics['key_info']
            summary = key_analytics['summary']

            print("\n" + "="*80)
            print(f"📊 {key_info['key_name']} - Last {args.days} Days")
            print("="*80 + "\n")

            print(f"🎯 Total Tokens: {summary['total_tokens']:,}")
            print(f"💰 Total Cost:   ${summary['total_cost']:.2f}")
            print(f"📞 Total Calls:  {summary['total_calls']}")
            print()

            # Show model breakdown
            analytics = key_analytics['analytics']
            if analytics['model_breakdown']:
                print("🤖 Model Usage:")
                for model_data in analytics['model_breakdown']:
                    print(f"   {model_data[0]}: {model_data[1]:,} tokens, ${model_data[2]:.2f}")
                print()

        return

    # Check if API key is required for remaining operations
    if not api_key and not args.demo:
        print("Error: OpenAI API key required. Set OPENAI_API_KEY environment variable or use --api-key")
        sys.exit(1)

    # Handle analytics mode
    if args.analytics:
        display_analytics(tracker, args.days)
        return

    # Handle export mode
    if args.export:
        export_usage_data(tracker, args.export, args.days)
        return

    # Handle budget setting
    if args.budget:
        month_year = datetime.now().strftime("%Y-%m")
        conn = sqlite3.connect(args.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO budget_settings
            (month_year, budget_limit, token_limit, alert_thresholds)
            VALUES (?, ?, ?, ?)
        ''', (month_year, args.budget, get_token_limit(args.plan, args.limit),
              json.dumps([0.5, 0.75, 0.9])))
        conn.commit()
        conn.close()
        print(f"✅ Monthly budget set to ${args.budget:.2f}")
        return

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

            # Update daily usage summary (every 10 minutes)
            if int(elapsed_minutes) % 10 == 0:
                tracker.update_daily_usage()

            # Check for alerts
            usage_data = {
                'tokens_used': tokens_used,
                'token_limit': token_limit,
                'total_cost': total_cost,
                'burn_rate': burn_rate
            }
            tracker.check_and_create_alerts(usage_data)

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

            # Show recent alerts (last 24 hours)
            conn = sqlite3.connect(args.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT alert_type, message, triggered_at FROM usage_alerts
                WHERE triggered_at >= DATETIME('now', '-1 day') AND is_active = 1
                ORDER BY triggered_at DESC LIMIT 3
            ''')
            recent_alerts = cursor.fetchall()
            conn.close()

            if recent_alerts:
                for alert in recent_alerts:
                    alert_time = datetime.fromisoformat(alert[2]).strftime("%H:%M")
                    print(f"🔔 {yellow}{alert[1]}{reset} {gray}({alert_time}){reset}")
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
