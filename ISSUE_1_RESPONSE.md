# Response to Issue #1: Monitor Usage Per Key/User

## Issue Summary
**Requested by**: @Smitellos  
**Request**: Add functionality to monitor usage per user/key in OpenAI projects

## Response

Hi @Smitellos! 👋

Thank you for this excellent feature request! This is a highly valuable addition that would benefit teams and users managing multiple OpenAI API keys or projects.

## 🎯 Proposed Implementation

I'm planning to implement **multi-key/user tracking** with the following features:

### 1. **Multi-Key Support**
- Track usage across multiple OpenAI API keys
- Assign friendly names/labels to each key (e.g., "Production", "Development", "User-John")
- Store key metadata (name, description, created date)
- Switch between keys easily

### 2. **Per-Key Analytics**
- Individual usage statistics for each key
- Model-specific breakdowns per key
- Cost tracking per key
- Burn rate calculations per key
- Hourly usage patterns per key

### 3. **Comparative Analytics**
- Compare usage across different keys
- Team-wide usage summaries
- Cost allocation reports
- Top consumers identification

### 4. **Key Management**
- Add/remove keys dynamically
- Set per-key budgets and alerts
- Enable/disable keys
- Export per-key reports

## 📊 Proposed Database Schema Changes

```sql
-- New table for API keys/users
CREATE TABLE api_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key_id TEXT UNIQUE,
    key_name TEXT,
    key_description TEXT,
    api_key_hash TEXT,  -- Hashed for security
    is_active BOOLEAN DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Update existing tables to include key_id
ALTER TABLE usage_sessions ADD COLUMN key_id TEXT;
ALTER TABLE api_calls ADD COLUMN key_id TEXT;
ALTER TABLE budget_settings ADD COLUMN key_id TEXT;
```

## 🚀 Proposed CLI Commands

```bash
# Add a new key
./start_openai_monitor.sh add-key --name "Production" --key "sk-..."

# List all keys
./start_openai_monitor.sh list-keys

# Monitor specific key
./start_openai_monitor.sh monitor --key "Production"

# Analytics for specific key
./start_openai_monitor.sh analytics --key "Production" --days 7

# Compare all keys
./start_openai_monitor.sh compare-keys --days 30

# Export per-key report
./start_openai_monitor.sh export-csv --key "Production"

# Set budget for specific key
./start_openai_monitor.sh budget-50 --key "Development"
```

## 📈 Proposed UI Enhancements

### Multi-Key Dashboard
```
✦ ✧ ✦ ✧ OPENAI MULTI-KEY MONITOR ✦ ✧ ✦ ✧ 
============================================================

📊 ACTIVE KEYS: 3

Key: Production (sk-...abc)
  🎯 Tokens:  45,230 / 500,000 (9.0%)
  💰 Cost:    $12.45
  🔥 Burn:    45.2 tokens/min

Key: Development (sk-...def)
  🎯 Tokens:  12,450 / 200,000 (6.2%)
  💰 Cost:    $3.21
  🔥 Burn:    12.1 tokens/min

Key: Testing (sk-...ghi)
  🎯 Tokens:  5,120 / 100,000 (5.1%)
  💰 Cost:    $0.89
  🔥 Burn:    3.4 tokens/min

============================================================
📊 TOTAL USAGE ACROSS ALL KEYS
  🎯 Tokens:  62,800
  💰 Cost:    $16.55
```

### Per-Key Analytics
```
📊 KEY ANALYTICS: Production - Last 7 Days
============================================================

🤖 Model Usage Breakdown:
Model           Tokens       Cost       Calls    %     
-------------------------------------------------------
gpt-4           25,350       $1.01      52       56.0 %
gpt-3.5-turbo   19,880       $0.79      48       44.0 %

⏰ Hourly Usage Pattern:
Hour   Avg Tokens   Calls    Activity            
--------------------------------------------------
09:00  1,254.2      45       ████████████████████
14:00  892.4        38       ███████████████
22:00  456.1        22       ████████
```

## 🔒 Security Considerations

1. **API Key Storage**: Keys will be hashed/encrypted in the database
2. **Display Masking**: Only show last 4 characters (e.g., "sk-...abc")
3. **Environment Variables**: Support for secure key management
4. **Access Control**: Optional password protection for multi-user setups

## 📅 Implementation Timeline

I can implement this feature in phases:

**Phase 1** (Week 1): Core multi-key support
- Database schema updates
- Key management (add/remove/list)
- Basic per-key tracking

**Phase 2** (Week 2): Analytics and reporting
- Per-key analytics
- Comparative analytics
- Export functionality

**Phase 3** (Week 3): Advanced features
- Per-key budgets and alerts
- Team collaboration features
- Web dashboard (if requested)

## 💬 Questions for You

To make sure I build exactly what you need:

1. **Use Case**: Are you tracking:
   - Multiple API keys for different environments (prod/dev/test)?
   - Multiple users sharing the same project?
   - Different projects with separate keys?

2. **Priority Features**: Which features are most important to you?
   - Per-key usage tracking?
   - Cost allocation/reporting?
   - Budget management per key?
   - Team collaboration?

3. **Reporting**: What kind of reports would be most valuable?
   - Daily/weekly/monthly summaries per key?
   - Cost allocation for billing purposes?
   - Usage trends and forecasting?

4. **Integration**: Do you need:
   - Export to specific formats (CSV, JSON, Excel)?
   - Integration with other tools (Slack, email alerts)?
   - Web dashboard for team visibility?

## 🎯 Next Steps

1. Please let me know your thoughts on the proposed implementation
2. Answer the questions above so I can prioritize features
3. I'll start working on Phase 1 and create a pull request for review

Looking forward to your feedback! This will be a great addition to the tool. 🚀

---

**Want to contribute?** Feel free to fork the repo and submit a PR if you'd like to help implement this feature!

**Need it urgently?** Let me know your timeline and I can prioritize accordingly.
