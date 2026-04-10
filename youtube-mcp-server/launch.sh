#!/bin/bash
# launch.sh — Install, configure, and start the YouTube MCP server

set -e

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║       YouTube MCP Server — Faceless Channel Launcher    ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Install dependencies
if [ ! -d "node_modules" ]; then
  echo "📦 Installing dependencies..."
  npm install
  echo ""
fi

# Step 2: Build TypeScript
echo "🔨 Building TypeScript..."
npm run build
echo ""

# Step 3: Check for credentials
if [ -z "$YOUTUBE_CLIENT_ID" ] && [ -z "$YOUTUBE_CREDENTIALS_PATH" ]; then
  if [ -f "youtube-credentials.json" ]; then
    export YOUTUBE_CREDENTIALS_PATH="./youtube-credentials.json"
    echo "🔑 Found youtube-credentials.json"
  else
    echo "⚠️  No YouTube credentials found."
    echo ""
    echo "   You have two options:"
    echo ""
    echo "   1. Run the OAuth setup wizard:"
    echo "      npm install open    # one-time dependency"
    echo "      node oauth-setup.js"
    echo ""
    echo "   2. Set environment variables manually:"
    echo "      export YOUTUBE_CLIENT_ID='...'"
    echo "      export YOUTUBE_CLIENT_SECRET='...'"
    echo "      export YOUTUBE_REFRESH_TOKEN='...'"
    echo ""
    echo "   Then re-run this script."
    echo ""
    exit 1
  fi
fi

# Step 4: Choose transport
TRANSPORT=${TRANSPORT:-stdio}
echo ""
echo "🚀 Starting YouTube MCP server (transport: $TRANSPORT)..."
echo ""

if [ "$TRANSPORT" = "http" ]; then
  PORT=${PORT:-3000}
  echo "   HTTP endpoint: http://localhost:$PORT/mcp"
  echo "   Health check:  http://localhost:$PORT/health"
  echo ""
  echo "   Add to Claude Desktop config:"
  echo '   {'
  echo '     "mcpServers": {'
  echo '       "youtube": {'
  echo "         \"url\": \"http://localhost:$PORT/mcp\""
  echo '       }'
  echo '     }'
  echo '   }'
  echo ""
  TRANSPORT=http PORT=$PORT node dist/index.js
else
  echo "   Running in stdio mode (for Claude Desktop / Claude Code)"
  echo ""
  echo "   Add to claude_desktop_config.json:"
  echo '   {'
  echo '     "mcpServers": {'
  echo '       "youtube": {'
  echo '         "command": "node",'
  echo "         \"args\": [\"$(pwd)/dist/index.js\"],"
  echo '         "env": {'
  echo '           "YOUTUBE_CREDENTIALS_PATH": "'$(pwd)/youtube-credentials.json'"'
  echo '         }'
  echo '       }'
  echo '     }'
  echo '   }'
  echo ""
  node dist/index.js
fi
