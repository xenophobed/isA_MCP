# MCP CLI - Quick Start Guide

A comprehensive command-line interface for interacting with the MCP server.

## 🎯 Features

- ✅ **Search** across prompts, resources, and tools
- ✅ **Get Prompts** with custom arguments
- ✅ **Call Tools** with parameters
- ✅ **Read Resources** from various URIs
- ✅ **Proper Display** for text, JSON, images, URLs, and markdown
- ✅ **Interactive Mode** with command history and auto-completion
- ✅ **Syntax Highlighting** (with rich library)
- ✅ **Direct Command Mode** for scripting

## 📦 Installation

```bash
# Optional: Install rich for better formatting
pip install rich

# Optional: Install prompt_toolkit for better interactive mode
pip install prompt_toolkit
```

## 🚀 Usage

### Interactive Mode (Recommended)

```bash
python mcp_cli.py
```

This starts an interactive session where you can type commands:

```
mcp> search web_search
mcp> tool web_search {"query": "AI trends", "count": 5}
mcp> prompt default_reason_prompt {"user_message": "Hello"}
mcp> resource event://status
mcp> capabilities
mcp> help
mcp> exit
```

### Direct Command Mode

```bash
# Search for something
python mcp_cli.py search "web search"
python mcp_cli.py search "weather" --type tool

# Call a tool
python mcp_cli.py tool web_search '{"query": "AI trends", "count": 5}'
python mcp_cli.py tool get_weather '{"city": "San Francisco"}'

# Get a prompt
python mcp_cli.py prompt default_reason_prompt '{"user_message": "Help me code"}'

# Read a resource
python mcp_cli.py resource event://status
python mcp_cli.py resource widget://system/info

# Show capabilities
python mcp_cli.py capabilities
```

### Custom Server URL

```bash
python mcp_cli.py --url http://your-server:8081
```

## 📝 Commands

### Search
Search across all MCP capabilities (prompts, tools, resources):

```bash
# In interactive mode
mcp> search web_search
mcp> search "machine learning"

# Direct mode
python mcp_cli.py search "data analysis" --max 20
python mcp_cli.py search "weather" --type tool
```

### Prompts
Get a prompt with optional arguments:

```bash
# In interactive mode
mcp> prompt default_reason_prompt
mcp> prompt default_reason_prompt {"user_message": "Help me", "tools": "web_search"}

# Direct mode
python mcp_cli.py prompt default_reason_prompt
python mcp_cli.py prompt default_response_prompt '{"task": "analyze"}'
```

### Tools
Call a tool with arguments:

```bash
# In interactive mode
mcp> tool web_search {"query": "Python", "count": 3}
mcp> tool get_weather {"city": "Tokyo"}

# Direct mode
python mcp_cli.py tool web_search '{"query": "AI", "count": 5}'
python mcp_cli.py tool create_execution_plan '{"task": "Build a website"}'
```

### Resources
Read a resource by URI:

```bash
# In interactive mode
mcp> resource event://status
mcp> resource widget://system/info
mcp> resource guardrail://config/pii

# Direct mode
python mcp_cli.py resource event://status
python mcp_cli.py resource widget://user/auth0|123/usage
```

### Capabilities
Show server capabilities:

```bash
# In interactive mode
mcp> capabilities

# Direct mode
python mcp_cli.py capabilities
```

## 🎨 Content Display

The CLI automatically handles different content types:

### Text
Plain text is displayed with formatting.

### JSON
JSON is syntax-highlighted and pretty-printed (with rich library).

### Markdown
Markdown content is rendered beautifully (with rich library).

### Images
- **URLs**: Displayed as clickable links, option to open in browser
- **Base64**: Shows preview, option to save to file

### Tables
Data is displayed in formatted tables (with rich library).

## 💡 Tips

1. **Use Tab Completion**: In interactive mode with prompt_toolkit, press Tab to auto-complete commands

2. **View History**: Use arrow keys (↑↓) to navigate command history

3. **Copy Output**: All output can be piped or redirected:
   ```bash
   python mcp_cli.py tool web_search '{"query": "AI"}' > output.json
   ```

4. **Script Integration**: Use direct mode in scripts:
   ```bash
   #!/bin/bash
   result=$(python mcp_cli.py search "weather" --type tool)
   echo "$result"
   ```

5. **JSON Arguments**: Always use single quotes around JSON in shell:
   ```bash
   # Good
   python mcp_cli.py tool my_tool '{"arg": "value"}'

   # Bad (shell interprets quotes)
   python mcp_cli.py tool my_tool {"arg": "value"}
   ```

## 🔧 Examples

### Example 1: Search and Use a Tool

```bash
# 1. Search for web tools
python mcp_cli.py search "web" --type tool

# 2. Use the web_search tool
python mcp_cli.py tool web_search '{"query": "Python async", "count": 5}'
```

### Example 2: Interactive Workflow

```bash
$ python mcp_cli.py

mcp> search digital
# See available digital tools

mcp> tool store_knowledge {"user_id": "test", "content": "Python is great", "content_type": "text"}
# Store some knowledge

mcp> tool search_knowledge {"user_id": "test", "query": "programming"}
# Search the knowledge base

mcp> exit
```

### Example 3: Resource Exploration

```bash
# Check system status
python mcp_cli.py resource event://status

# View widget information
python mcp_cli.py resource widget://system/info

# Check user usage
python mcp_cli.py resource widget://user/my_user_id/usage
```

## 🐛 Troubleshooting

### Server Not Running
```
❌ Error: Connection refused
```
**Solution**: Make sure your MCP server is running on port 8081

### Invalid JSON Arguments
```
❌ Error: JSON decode error
```
**Solution**: Ensure JSON is properly formatted and use single quotes in shell:
```bash
python mcp_cli.py tool my_tool '{"key": "value"}'
```

### No Rich Output
If you see plain text instead of colored/formatted output:
```bash
pip install rich prompt_toolkit
```

## 📚 Advanced Usage

### Piping and Redirecting

```bash
# Save output to file
python mcp_cli.py capabilities > capabilities.json

# Parse with jq
python mcp_cli.py tool web_search '{"query": "AI"}' | jq '.data.results[0]'

# Chain commands
python mcp_cli.py search "weather" | grep "get_weather"
```

### Using in Scripts

```python
import subprocess
import json

# Call MCP CLI from Python
result = subprocess.run(
    ['python', 'mcp_cli.py', 'tool', 'web_search', '{"query": "AI"}'],
    capture_output=True,
    text=True
)

data = json.loads(result.stdout)
print(data)
```

```bash
#!/bin/bash
# Call MCP CLI from Bash script

query="machine learning"
result=$(python mcp_cli.py tool web_search "{\"query\": \"$query\", \"count\": 3}")
echo "$result"
```

## 🎯 Next Steps

1. Explore available capabilities:
   ```bash
   python mcp_cli.py capabilities
   ```

2. Search for what you need:
   ```bash
   python mcp_cli.py search "your interest"
   ```

3. Test tools interactively:
   ```bash
   python mcp_cli.py
   ```

4. Build your workflows!

---

**Happy Testing! 🚀**
