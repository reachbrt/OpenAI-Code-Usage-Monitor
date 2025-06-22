# 🐛 Troubleshooting Guide

Common issues and solutions for OpenAI API Usage Monitor.

## 🚨 Quick Fixes

### Most Common Issues

| Problem | Quick Fix |
|---------|-----------|
| API key not set | `export OPENAI_API_KEY="your-key"` |
| No active session | Create session with monitor or demo mode |
| Permission denied | `chmod +x openai_usage_monitor.py` (Linux/Mac) |
| Display issues | Resize terminal to 80+ characters width |
| Hidden cursor after exit | `printf '\033[?25h'` |


## 🔧 Installation Issues

### OpenAI API Key Not Set

**Error Message**:
```
Error: OpenAI API key required. Set OPENAI_API_KEY environment variable or use --api-key
```

**Solution**:
```bash
# Set API key as environment variable
export OPENAI_API_KEY="your-api-key-here"

# Or pass directly to script
./openai_usage_monitor.py --api-key "your-api-key-here"

# For Windows PowerShell:
$env:OPENAI_API_KEY="your-api-key-here"

# For Windows Command Prompt:
set OPENAI_API_KEY=your-api-key-here
```

**Alternative Solutions**:
```bash
# Test with demo mode (no API key required)
./openai_usage_monitor.py --demo

# Add to shell profile for persistence
echo 'export OPENAI_API_KEY="your-key"' >> ~/.bashrc
source ~/.bashrc
```

### Python Dependencies Missing

**Error Message**:
```
ModuleNotFoundError: No module named 'requests'
ModuleNotFoundError: No module named 'pytz'
```

**Solution**:
```bash
# Install all required dependencies
pip install -r requirements.txt

# Or install individually:
pip install requests pytz

# For virtual environment users:
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### Permission Denied (Linux/Mac)

**Error Message**:
```
Permission denied: ./openai_usage_monitor.py
```

**Solution**:
```bash
# Make script executable
chmod +x openai_usage_monitor.py

# Or run with python directly
python openai_usage_monitor.py
python3 openai_usage_monitor.py
```


## 📊 Usage Data Issues

### No Active Session Found

**Error Message**:
```
No active session found. Creating new session...
```

**Cause**: Monitor needs to create a session to track API usage.

**Solution**:
1. Ensure your OpenAI API key is set correctly
2. The monitor will automatically create a session
3. Start making API calls to see usage data
4. Or use demo mode to test the interface

**Verification**:
```bash
# Test with demo mode
./openai_usage_monitor.py --demo

# Check if API key works
./openai_usage_monitor.py --api-key "your-key"
```

### Failed to Get Usage Data

**Error Message**:
```
Error fetching usage data: <various error messages>
```

**Debugging Steps**:

1. **Check API key**:
   ```bash
   # Verify API key is set
   echo $OPENAI_API_KEY

   # Test API connection
   curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
   ```

2. **Check network connectivity**:
   ```bash
   # Test basic connectivity
   ping api.openai.com
   curl -I https://api.openai.com
   ```

3. **Verify API key permissions**:
   - Ensure your API key has usage access
   - Check if your OpenAI account is in good standing
   - Verify billing information is up to date

4. **Try demo mode**:
   ```bash
   # Test interface without API calls
   ./openai_usage_monitor.py --demo
   ```

### Incorrect Token Counts

**Issue**: Monitor shows unexpected token numbers

**Possible Causes & Solutions**:

1. **Multiple Sessions**:
   - Remember: You can have multiple 5-hour sessions
   - Each session has its own token count
   - Monitor shows aggregate across all active sessions

2. **Session Timing**:
   - Sessions last exactly 5 hours from first message
   - Reset times are reference points, not actual resets
   - Check session start times in monitor output

3. **Plan Detection Issues**:
   ```bash
   # Try different plan settings
   ./openai_usage_monitor.py --plan tier3
   ./openai_usage_monitor.py --plan tier2
   ```


## 🖥️ Display Issues

### Terminal Too Narrow

**Issue**: Overlapping text, garbled display

**Solution**:
```bash
# Check terminal width
tput cols

# Should be 80 or more characters
# Resize terminal window or use:
./openai_usage_monitor.py | less -S  # Scroll horizontally
```

### Missing Colors

**Issue**: No color output, plain text only

**Solutions**:
```bash
# Check terminal color support
echo $TERM

# Force color output (if supported)
export FORCE_COLOR=1
./openai_usage_monitor.py

# Alternative terminals with better color support:
# - Use modern terminal (iTerm2, Windows Terminal, etc.)
# - Check terminal settings for ANSI color support
```

### Screen Flicker

**Issue**: Excessive screen clearing/redrawing

**Cause**: Terminal compatibility issues

**Solutions**:
1. Use a modern terminal emulator
2. Check terminal size (minimum 80 characters)
3. Ensure stable window size during monitoring

### Cursor Remains Hidden After Exit

**Issue**: Terminal cursor invisible after Ctrl+C

**Quick Fix**:
```bash
# Restore cursor visibility
printf '\033[?25h'

# Or reset terminal completely
reset
```

**Prevention**: Always exit with Ctrl+C for graceful shutdown


## ⏰ Time & Timezone Issues

### Incorrect Reset Times

**Issue**: Reset predictions don't match your schedule

**Solution**:
```bash
# Set your timezone explicitly
./openai_usage_monitor.py --timezone America/New_York
./openai_usage_monitor.py --timezone Europe/London
./openai_usage_monitor.py --timezone Asia/Tokyo
```

**Find Your Timezone**:
```bash
# Linux/Mac - find available timezones
timedatectl list-timezones | grep -i america
timedatectl list-timezones | grep -i europe

# Or use online timezone finder
# https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
```

### Session Expiration Confusion

**Issue**: Don't understand when sessions expire

**Explanation**:
- Sessions last **exactly 5 hours** from your first message
- Default reset times (4:00, 9:00, 14:00, 18:00, 23:00) are reference points
- Your actual session resets 5 hours after YOU start each session

**Example**:
```
10:30 AM - You send first message → Session expires 3:30 PM
02:00 PM - You start new session → Session expires 7:00 PM
```

## 🔧 Platform-Specific Issues

### Windows Issues

**PowerShell Execution Policy**:
```powershell
# If scripts are blocked
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Run with Python directly
python3 openai_usage_monitor.py
```

**Path Issues**:
```bash
# If Python not found, check Python installation
which python3
python3 --version
```

**Virtual Environment on Windows**:
```cmd
# Activate virtual environment
venv\Scripts\activate

# Deactivate
deactivate
```

### macOS Issues

**Permission Issues with Homebrew Python**:
```bash
# Use system Python if Homebrew Python has issues
/usr/bin/python3 -m venv venv

# Or reinstall Python via Homebrew
brew reinstall python3
```

**Python Installation Issues**:
```bash
# If Python permission issues
sudo chown -R $(whoami) /usr/local/lib/python3.*

# Or use pyenv for Python management
curl https://pyenv.run | bash
pyenv install 3.11.0
pyenv global 3.11.0
```

### Linux Issues

**Missing Python venv Module**:
```bash
# Ubuntu/Debian
sudo apt-get install python3-venv

# Fedora/CentOS
sudo dnf install python3-venv

# Arch Linux
sudo pacman -S python-virtualenv
```

**npm Permission Issues**:
```bash
# Configure npm to use different directory
mkdir ~/.npm-global
npm config set prefix '~/.npm-global'
echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.profile
source ~/.profile
```


## 🧠 Performance Issues

### High CPU Usage

**Cause**: Monitor updates every 3 seconds

**Solutions**:
1. **Normal behavior**: 3-second updates are intentional for real-time monitoring
2. **Reduce frequency**: Currently not configurable, but will be in future versions
3. **Close when not needed**: Use Ctrl+C to exit when not actively monitoring

### Memory Usage Growing

**Issue**: Memory usage increases over time

**Debugging**:
```bash
# Monitor memory usage
top -p $(pgrep -f openai_usage_monitor)
htop  # Look for openai_usage_monitor process

# Check for memory leaks
python3 -m tracemalloc openai_usage_monitor.py
```

**Solutions**:
1. Restart monitor periodically for long sessions
2. Report issue with system details
3. Use virtual environment to isolate dependencies

### Slow Startup

**Cause**: API connection needs to be established

**Normal**: First run may take 5-10 seconds

**If consistently slow**:
1. Check internet connection
2. Verify OpenAI API key is valid
3. Check OpenAI service status


## 🔄 Data Accuracy Issues

### Token Counts Don't Match OpenAI Dashboard

**Possible Causes**:

1. **Different Counting Methods**:
   - Monitor counts tokens used in current monitoring session
   - OpenAI dashboard might show different time periods
   - Multiple API calls can cause brief discrepancies

2. **Timing Differences**:
   - Monitor updates every 3 seconds
   - OpenAI dashboard updates periodically
   - Brief discrepancies are normal

3. **Time Period Boundaries**:
   - Monitor tracks monthly billing cycles
   - Verify you're comparing the same time periods

**Debugging**:
```bash
# Check API connection
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/usage

# Compare with monitor output
./openai_usage_monitor.py --plan tier2
```

### Burn Rate Calculations Seem Wrong

**Understanding Burn Rate**:
- Calculated from token usage in the last hour
- Includes all active sessions
- May fluctuate based on recent activity

**If still seems incorrect**:
1. Monitor for longer period (10+ minutes)
2. Check if multiple sessions are active
3. Verify recent usage patterns match expectations


## 🆘 Getting Help

### Before Asking for Help

1. **Check this troubleshooting guide**
2. **Search existing GitHub issues**
3. **Try basic debugging steps**
4. **Gather system information**

### What Information to Include

When reporting issues, include:

```bash
# System information
uname -a  # Linux/Mac
systeminfo  # Windows

# Python version
python --version
python3 --version

# Python version
python3 --version

# OpenAI API test
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models

# Test monitor directly
./openai_usage_monitor.py --demo
```

### Where to Get Help

1. **GitHub Issues**: [Create new issue](https://github.com/reachbrt/OpenAI-Code-Usage-Monitor/issues/new)
2. **Email**: [reachbrt@gmail.com](mailto:reachbrt@gmail.com)
3. **Documentation**: Check [README.md](README.md) for installation and usage

### Issue Template

```markdown
**Problem Description**
Clear description of the issue.

**Steps to Reproduce**
1. Command run: `./openai_usage_monitor.py --plan tier2`
2. Expected result: ...
3. Actual result: ...

**Environment**
- OS: [Ubuntu 20.04 / Windows 11 / macOS 12]
- Python: [3.9.7]
- OpenAI API Key: [Set/Not Set]

**Error Output**
```
Paste full error messages here
```

**Additional Context**
Any other relevant information.
```


## 🔧 Advanced Debugging

### Enable Debug Mode

```bash
# Run with Python verbose output
python3 -v openai_usage_monitor.py

# Check API debug output
./openai_usage_monitor.py --demo

# Monitor system calls (Linux/Mac)
strace -e trace=execve python3 openai_usage_monitor.py
```

### Network Debugging

```bash
# Check if monitor makes network requests
netstat -p | grep openai_usage_monitor  # Linux
lsof -i | grep openai_usage_monitor     # Mac

# Monitor network traffic
tcpdump -i any host api.openai.com  # Requires sudo
```

### File System Debugging

```bash
# Check if monitor accesses config files
strace -e trace=file python3 openai_usage_monitor.py  # Linux
dtruss python3 openai_usage_monitor.py               # Mac

# Look for config directories
ls ~/.openai_monitor/  # Monitor config
ls ~/.config/openai/   # Potential config location
```


## 🔄 Reset Solutions

### Complete Reset

If all else fails, complete reset:

```bash
# 1. Clean up old installation
pip uninstall requests pytz

# 2. Clear Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete

# 3. Remove virtual environment
rm -rf venv

# 4. Fresh installation
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Test basic functionality
python3 openai_usage_monitor.py --demo
python3 openai_usage_monitor.py --help
```

### API Key Reset

```bash
# Reset OpenAI API key if having issues
# 1. Generate new API key at https://platform.openai.com/api-keys
# 2. Update environment variable: export OPENAI_API_KEY="new-key"
# 3. Test API connection: curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
# 4. Run monitor: ./openai_usage_monitor.py --demo
```

---

**Still having issues?** Don't hesitate to [create an issue](https://github.com/reachbrt/OpenAI-Code-Usage-Monitor/issues/new) or [contact us directly](mailto:reachbrt@gmail.com)!
