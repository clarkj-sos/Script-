# Getting Started: YouTube MCP Server for Your Faceless Channel

A step-by-step guide to setting up and using the YouTube MCP Server to manage your faceless YouTube channel entirely through Claude.

---

## Table of Contents

1. [What You'll Need](#what-youll-need)
2. [Step 1: Set Up a Google Cloud Project](#step-1-set-up-a-google-cloud-project)
3. [Step 2: Get Your API Key (Read-Only Access)](#step-2-get-your-api-key-read-only-access)
4. [Step 3: Get OAuth2 Credentials (Full Access)](#step-3-get-oauth2-credentials-full-access)
5. [Step 4: Install and Build the Server](#step-4-install-and-build-the-server)
6. [Step 5: Configure Environment Variables](#step-5-configure-environment-variables)
7. [Step 6: Connect to Claude](#step-6-connect-to-claude)
8. [Step 7: Start Managing Your Channel](#step-7-start-managing-your-channel)
9. [Faceless Channel Workflows](#faceless-channel-workflows)
10. [Quota Management](#quota-management)
11. [Troubleshooting](#troubleshooting)

---

## What You'll Need

- **Python 3.9+** and **pip**
- A **Google account** with a YouTube channel
- **Claude Desktop**, **Claude Code**, or another MCP-compatible client
- Basic comfort with the terminal

---

## Step 1: Set Up a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a Project** (top bar) then **New Project**
3. Name it something like `youtube-mcp` and click **Create**
4. Once created, select it as your active project
5. Navigate to **APIs & Services > Library**
6. Search for **YouTube Data API v3** and click **Enable**

---

## Step 2: Get Your API Key (Read-Only Access)

An API key lets you use read-only tools (search, get video info, list comments, view analytics).

1. In Google Cloud Console, go to **APIs & Services > Credentials**
2. Click **Create Credentials > API Key**
3. Copy the key and save it somewhere safe
4. (Recommended) Click **Restrict Key** to limit it to the YouTube Data API v3

---

## Step 3: Get OAuth2 Credentials (Full Access)

OAuth2 is required for write operations: uploading videos, updating metadata, managing playlists, replying to comments, setting thumbnails, and deleting videos.

### Create OAuth Client

1. In **APIs & Services > Credentials**, click **Create Credentials > OAuth client ID**
2. If prompted, configure the **OAuth consent screen** first:
   - Choose **External** user type
   - Fill in the app name and your email
   - Add the scope: `https://www.googleapis.com/auth/youtube`
   - Add your Google account as a test user
3. Back in Credentials, select **Desktop app** as the application type
4. Note your **Client ID** and **Client Secret**

### Get a Refresh Token

Use the [Google OAuth Playground](https://developers.google.com/oauthplayground/) to generate a refresh token:

1. Click the gear icon (top right) and check **Use your own OAuth credentials**
2. Enter your **Client ID** and **Client Secret**
3. In the left panel, find **YouTube Data API v3** and select the scope:
   ```
   https://www.googleapis.com/auth/youtube
   ```
4. Click **Authorize APIs** and sign in with your Google account
5. Click **Exchange authorization code for tokens**
6. Copy the **Refresh Token**

---

## Step 4: Install and Build the Server

```bash
# Clone the repository
git clone https://github.com/clarkj-sos/Script-.git
cd Script-

# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 5: Configure Environment Variables

Create a `.env` file or export the variables in your shell:

```bash
# Required: Read-only access
export YOUTUBE_API_KEY="your-api-key-here"

# Required for uploads, updates, and channel management
export YOUTUBE_CLIENT_ID="your-client-id-here"
export YOUTUBE_CLIENT_SECRET="your-client-secret-here"
export YOUTUBE_REFRESH_TOKEN="your-refresh-token-here"

# Optional: Transport mode (default: stdio)
export TRANSPORT="stdio"    # Use "http" for remote/multi-client access
export PORT="3000"           # Only used with HTTP transport
```

---

## Step 6: Connect to Claude

### Option A: Claude Desktop

Add the server to your `claude_desktop_config.json`:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "youtube": {
      "command": "python3",
      "args": ["/absolute/path/to/Script-/server.py"],
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

Restart Claude Desktop after saving.

### Option B: Claude Code (CLI)

Add the MCP server via the CLI:

```bash
claude mcp add youtube -- python3 /absolute/path/to/Script-/server.py
```

Then set the environment variables in your shell before launching Claude Code.

### Option C: HTTP Transport (Remote Access)

```bash
TRANSPORT=http RDC_PORT=3000 python3 server.py
# Server runs at https://0.0.0.0:3000
```

---

## Step 7: Start Managing Your Channel

Once connected, you can talk to Claude naturally. Here are some things to try:

### Check your channel stats
> "How is my channel doing? Show me my subscriber count and total views."

### Search and analyze content
> "Search for the top 10 trending videos about AI tools."

### Upload a video
> "Upload the file `/path/to/video.mp4` with the title 'Top 5 AI Tools in 2026' and add it to my Tools playlist."

### Update video metadata
> "Update the description on my latest video to include these links..."

### Manage playlists
> "Create a new playlist called 'AI Weekly' and add my last 3 videos to it."

### Monitor comments
> "What are people saying about my latest upload? Reply to the top comment thanking them."

### Set a thumbnail
> "Set the thumbnail for video ID abc123 to `/path/to/thumbnail.jpg`."

---

## Faceless Channel Workflows

Running a faceless YouTube channel means the content speaks for itself — no camera needed. Here's how to use the MCP server to streamline your workflow:

### Content Pipeline

1. **Research** — Ask Claude to search YouTube for trending topics in your niche:
   > "Search YouTube for the most viewed videos about productivity tips in the last 7 days."

2. **Upload** — Once your video is ready (screen recording, slideshow, AI-generated), upload it directly:
   > "Upload `/videos/productivity-hacks.mp4` as unlisted with the title 'Top 10 Productivity Hacks'."

3. **Optimize** — Update metadata for SEO before publishing:
   > "Update the description, tags, and title for my latest upload to be SEO-friendly for 'productivity tips 2026'."

4. **Publish** — Set it live:
   > "Change the privacy of video ID xyz789 to public."

5. **Organize** — Keep your content organized in playlists:
   > "Add my last 5 uploads to the 'Productivity' playlist."

6. **Engage** — Monitor and respond to comments:
   > "List comments on my latest video and reply to anyone asking questions."

### Batch Analytics

> "Give me analytics for my last 10 videos — views, likes, and engagement rate."

This helps you identify what content performs best so you can double down on winning topics.

---

## Quota Management

The YouTube Data API has a **10,000 units/day** default quota. Plan your usage:

| Operation | Cost |
|-----------|------|
| Search | 100 units |
| Video upload | 1,600 units |
| Thumbnail set | 50 units |
| Read operations (get, list) | 1 unit |
| Update operations | 50 units |
| Delete operations | 50 units |

**Tips:**
- Batch your analytics requests instead of checking one video at a time
- Use `youtube_list_channel_videos` (1 unit) instead of `youtube_search` (100 units) when browsing your own content
- Request a quota increase in the Google Cloud Console if you need more

---

## Troubleshooting

### "This operation requires OAuth2 authentication"
You're trying to use a write tool (upload, update, delete) without OAuth2 credentials. Make sure `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, and `YOUTUBE_REFRESH_TOKEN` are all set.

### "API key not valid"
Double-check your `YOUTUBE_API_KEY` value. Make sure the YouTube Data API v3 is enabled in your Google Cloud project.

### "Quota exceeded"
You've hit the 10,000 unit daily limit. Wait until midnight Pacific Time for the quota to reset, or request an increase in Google Cloud Console.

### "Access Not Configured" or "Forbidden"
- Make sure the YouTube Data API v3 is enabled
- If using OAuth, confirm your account is listed as a test user in the OAuth consent screen

### Server won't start
- Ensure Python 3.9+ is installed: `python3 --version`
- Run `pip install -r requirements.txt` again
- Check that all required environment variables are set

### Claude doesn't see the YouTube tools
- Verify the path in your MCP configuration is correct
- Restart Claude Desktop or Claude Code after changing the config
- Check the server logs for startup errors

---

## Next Steps

- Explore all 14 available tools listed in the [README](README.md)
- Set up a content calendar and use Claude to batch-upload videos
- Use analytics to track growth and optimize your content strategy
- Consider setting up HTTP transport if you want to access the server from multiple devices

Happy creating!
