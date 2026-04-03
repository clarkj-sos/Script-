# YouTube MCP Server

An MCP (Model Context Protocol) server that connects Claude (or any MCP client) to the YouTube Data API v3. Upload videos, manage metadata, pull analytics, handle playlists, and moderate comments — all through natural language.

## Tools

| Tool | Description | Auth |
|------|-------------|------|
| `youtube_search` | Search videos, channels, or playlists by keyword | API Key |
| `youtube_get_video` | Get full metadata + stats for a video | API Key |
| `youtube_get_channel` | Get channel info and subscriber counts | API Key |
| `youtube_list_channel_videos` | List a channel's uploaded videos | API Key |
| `youtube_get_video_analytics` | Batch analytics: views, likes, engagement rate | API Key |
| `youtube_update_video` | Update title, description, tags, privacy | OAuth2 |
| `youtube_upload_video` | Upload a video file to YouTube | OAuth2 |
| `youtube_list_playlists` | List playlists for a channel | API Key |
| `youtube_create_playlist` | Create a new playlist | OAuth2 |
| `youtube_add_to_playlist` | Add a video to a playlist | OAuth2 |
| `youtube_list_comments` | List comment threads on a video | API Key |
| `youtube_reply_to_comment` | Reply to a comment | OAuth2 |
| `youtube_delete_video` | Permanently delete a video | OAuth2 |
| `youtube_set_thumbnail` | Upload a custom thumbnail | OAuth2 |

## Prerequisites

1. **Google Cloud Project** with YouTube Data API v3 enabled
2. **API Key** (for read-only tools) and/or **OAuth2 credentials** (for write tools)

### Getting an API Key (read-only access)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or select an existing one)
3. Enable **YouTube Data API v3**
4. Go to **Credentials → Create Credentials → API Key**

### Getting OAuth2 Credentials (full access)

1. In the same project, go to **Credentials → Create Credentials → OAuth client ID**
2. Choose **Desktop app** or **Web application**
3. Note the **Client ID** and **Client Secret**
4. Use the [OAuth Playground](https://developers.google.com/oauthplayground/) or a script to get a **Refresh Token** with the scope `https://www.googleapis.com/auth/youtube`

## Setup

```bash
# Clone / copy the project
cd youtube-mcp-server

# Install dependencies
npm install

# Build
npm run build
```

## Environment Variables

```bash
# Read-only access (minimum)
export YOUTUBE_API_KEY="your-api-key"

# Full access (uploads, updates, deletes)
export YOUTUBE_CLIENT_ID="your-client-id"
export YOUTUBE_CLIENT_SECRET="your-client-secret"
export YOUTUBE_REFRESH_TOKEN="your-refresh-token"

# Transport (default: stdio)
export TRANSPORT="stdio"   # or "http"
export PORT="3000"          # for HTTP transport
```

## Running

### stdio (for Claude Desktop, Claude Code, etc.)

```bash
npm start
```

### HTTP (for remote/multi-client)

```bash
TRANSPORT=http npm start
# Server runs at http://localhost:3000/mcp
```

## Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "youtube": {
      "command": "node",
      "args": ["/path/to/youtube-mcp-server/dist/index.js"],
      "env": {
        "YOUTUBE_API_KEY": "your-api-key",
        "YOUTUBE_CLIENT_ID": "your-client-id",
        "YOUTUBE_CLIENT_SECRET": "your-client-secret",
        "YOUTUBE_REFRESH_TOKEN": "your-refresh-token"
      }
    }
  }
}
```

## Quota Notes

- YouTube Data API has a **10,000 unit/day** default quota
- Searches cost **100 units** each
- Video uploads cost **1,600 units** each
- Read operations (list, get) cost **1 unit** each
- Request a quota increase in Google Cloud Console if needed

## Examples

**"How are my latest videos performing?"**
→ Claude calls `youtube_list_channel_videos` then `youtube_get_video_analytics`

**"Upload my new video and add it to my Space playlist"**
→ Claude calls `youtube_upload_video` then `youtube_add_to_playlist`

**"Update the description on my black holes video"**
→ Claude calls `youtube_search` to find it, then `youtube_update_video`

**"What are people saying about my latest upload?"**
→ Claude calls `youtube_list_comments`
