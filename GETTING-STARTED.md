# YouTube MCP Server — Setup Guide

The server has been **built and is ready to use**. Follow the steps below to connect it to Claude.

---

## Step 1 — Get a Google API Key (read-only access)

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g. "YouTube MCP")
3. Click **APIs & Services → Enable APIs** and enable **YouTube Data API v3**
4. Go to **APIs & Services → Credentials → Create Credentials → API Key**
5. Copy the key — you'll need it below

---

## Step 2 — Get OAuth2 Credentials (upload, edit & manage videos)

1. In the same Google Cloud project, go to **Credentials → Create Credentials → OAuth client ID**
2. Choose **Desktop app**, give it a name, and click **Create**
3. Note your **Client ID** and **Client Secret**
4. Go to [OAuth Playground](https://developers.google.com/oauthplayground/)
   - Click the gear icon (⚙️) → check **Use your own OAuth credentials**
   - Enter your Client ID and Client Secret
5. In the left panel, find and select the scope:
   `https://www.googleapis.com/auth/youtube`
6. Click **Authorize APIs** → sign in with your Google account
7. Click **Exchange authorization code for tokens**
8. Copy the **Refresh Token** — you'll need it below

---

## Step 3 — Add the MCP Server to Claude

Open your Claude Desktop config file:

- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Add the following inside `"mcpServers"` (update the path to match where you saved the folder):

```json
{
  "mcpServers": {
    "youtube": {
      "command": "node",
      "args": ["PATH_TO_FOLDER/youtube-mcp-server/dist/index.js"],
      "env": {
        "YOUTUBE_API_KEY": "your-api-key-here",
        "YOUTUBE_CLIENT_ID": "your-client-id-here",
        "YOUTUBE_CLIENT_SECRET": "your-client-secret-here",
        "YOUTUBE_REFRESH_TOKEN": "your-refresh-token-here"
      }
    }
  }
}
```

Replace `PATH_TO_FOLDER` with the full path to the parent folder that contains `youtube-mcp-server/` (typically your cloned `Script-` directory).

---

## Step 4 — Restart Claude

Quit and reopen Claude Desktop. The YouTube tools will now be available in your conversations.

---

## Building from Source

If `youtube-mcp-server/dist/index.js` does not exist (e.g. fresh clone), build it first:

```bash
cd youtube-mcp-server
npm install
npm run build
```

Then continue with Step 3 above.

---

## What You Can Do Once Connected

| Ask | Tool called |
|-----|-------------|
| "Upload my new video" | `youtube_upload_video` |
| "How are my videos performing?" | `youtube_get_video_analytics` |
| "Update the description on my latest video" | `youtube_update_video` |
| "Create a playlist called 'Tutorials'" | `youtube_create_playlist` |
| "What are people saying in my comments?" | `youtube_list_comments` |
| "Set a thumbnail for my latest video" | `youtube_set_thumbnail` |

---

## Quota Limits (YouTube Data API)

- Default: **10,000 units/day**
- Searches: 100 units each
- Uploads: 1,600 units each
- Read operations: 1 unit each

Request a quota increase in Google Cloud Console if needed.

---

## Legacy: Python Flask Remote Desktop Control App

This repository also contains an unrelated **Python Flask Remote Desktop Control** application (`server.py`, `app/`, `config.py`, `requirements.txt`) that coexists alongside the YouTube MCP server. It is preserved for historical reasons and is not required for the YouTube MCP server to function.

If you need to run the Python app:

```bash
# From the repository root
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python server.py
```

The server starts at `https://localhost:6100` with a randomly generated password printed to the console (or use the `RDC_PASSWORD` environment variable to set your own).
