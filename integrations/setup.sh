#!/usr/bin/env bash
# ORP Agent Integration Setup
# Run: bash integrations/setup.sh
# Detects which agent you're using and configures ORP

set -e

echo "ORP Agent Integration Setup"
echo "==========================="

# Detect agent
AGENT=""
if command -v codex &>/dev/null; then
    AGENT="codex"
elif command -v claude &>/dev/null; then
    AGENT="claude"
fi

if [ -z "$AGENT" ]; then
    echo "No supported agent detected (codex or claude)."
    echo ""
    echo "Manual setup:"
    echo "  1. Install ORP: pip install open-reflection-protocol"
    echo "  2. Start MCP server: orp mcp-server --transport stdio"
    echo "  3. Configure your agent to use the MCP server"
    echo ""
    echo "See AGENTS.md for agent instructions."
    exit 0
fi

echo "Detected: $AGENT"

if [ "$AGENT" = "codex" ]; then
    CONFIG_DIR="$HOME/.codex"
    mkdir -p "$CONFIG_DIR"
    CONFIG_FILE="$CONFIG_DIR/config.toml"

    # Check if ORP is already configured
    if grep -q "orp" "$CONFIG_FILE" 2>/dev/null; then
        echo "ORP already configured in $CONFIG_FILE"
    else
        cat >> "$CONFIG_FILE" << 'EOF'

[mcp_servers.orp]
command = "uv"
args = ["run", "orp", "mcp-server", "--transport", "stdio"]
EOF
        echo "Added ORP MCP server to $CONFIG_FILE"
    fi
fi

if [ "$AGENT" = "claude" ]; then
    CONFIG_DIR="$HOME/.claude"
    mkdir -p "$CONFIG_DIR"
    CONFIG_FILE="$CONFIG_DIR/settings.json"

    if [ -f "$CONFIG_FILE" ] && grep -q "orp" "$CONFIG_FILE" 2>/dev/null; then
        echo "ORP already configured in $CONFIG_FILE"
    else
        SETTINGS='{"mcpServers":{"orp":{"command":"uv","args":["run","orp","mcp-server","--transport","stdio"]}}}'
        if [ -f "$CONFIG_FILE" ]; then
            # Merge with existing settings
            python3 -c "
import json
with open('$CONFIG_FILE') as f:
    s = json.load(f)
if 'mcpServers' not in s:
    s['mcpServers'] = {}
s['mcpServers']['orp'] = {'command': 'uv', 'args': ['run', 'orp', 'mcp-server', '--transport', 'stdio']}
with open('$CONFIG_FILE', 'w') as f:
    json.dump(s, f, indent=2)
"
        else
            echo "$SETTINGS" > "$CONFIG_FILE"
        fi
        echo "Added ORP MCP server to $CONFIG_FILE"
    fi
fi

echo ""
echo "Setup complete!"
echo "Next steps:"
echo "  1. Copy AGENTS.md to your project root (already done)"
echo "  2. Your agent will now retrieve ORP lessons before tasks"
echo "  3. Run: orp mcp-server --transport stdio"
