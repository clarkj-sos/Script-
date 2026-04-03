import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import * as fs from "fs";
import {
  getYouTubeClient,
  hasOAuthAccess,
  handleYouTubeError,
  formatDate,
  formatNumber,
  formatDuration,
} from "../services/youtube-client.js";
import { ResponseFormat, CHARACTER_LIMIT } from "../constants.js";
import {
  SearchVideosSchema,
  GetVideoSchema,
  GetChannelSchema,
  ListChannelVideosSchema,
  GetVideoAnalyticsSchema,
  UpdateVideoSchema,
  UploadVideoSchema,
  ListPlaylistsSchema,
  CreatePlaylistSchema,
  AddToPlaylistSchema,
  ListCommentsSchema,
  ReplyToCommentSchema,
  DeleteVideoSchema,
  SetThumbnailSchema,
} from "../schemas/youtube-schemas.js";
import type {
  YouTubeVideo,
  YouTubeChannel,
  YouTubePlaylist,
  YouTubeSearchResult,
} from "../types.js";

// ── Helpers ─────────────────────────────────────────────────────────────

function truncateIfNeeded(text: string): string {
  if (text.length > CHARACTER_LIMIT) {
    return (
      text.slice(0, CHARACTER_LIMIT) +
      "\n\n⚠️ Response truncated. Use pagination or filters to see more results."
    );
  }
  return text;
}

function requireOAuth(): void {
  if (!hasOAuthAccess()) {
    throw new Error(
      "This operation requires OAuth2 authentication. " +
        "Set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, and YOUTUBE_REFRESH_TOKEN environment variables."
    );
  }
}

// ── Register all tools ──────────────────────────────────────────────────

export function registerYouTubeTools(server: McpServer): void {
  // ━━ youtube_search ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  server.registerTool(
    "youtube_search",
    {
      title: "Search YouTube",
      description: `Search YouTube for videos, channels, or playlists by keyword.

Args:
  - query (string): Search terms
  - order ('relevance'|'date'|'viewCount'|'rating'): Sort order (default: relevance)
  - type ('video'|'channel'|'playlist'): Resource type (default: video)
  - channel_id (string, optional): Restrict to a specific channel
  - published_after / published_before (ISO 8601, optional): Date filters
  - max_results (number 1-50, default 25): Results per page
  - page_token (string, optional): Pagination token
  - response_format ('markdown'|'json'): Output format

Returns: List of search results with titles, IDs, publish dates, and thumbnails.`,
      inputSchema: SearchVideosSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async (params: z.infer<typeof SearchVideosSchema>) => {
      try {
        const yt = getYouTubeClient();
        const res = await yt.search.list({
          part: ["snippet"],
          q: params.query,
          type: [params.type],
          order: params.order,
          maxResults: params.max_results,
          pageToken: params.page_token,
          channelId: params.channel_id,
          publishedAfter: params.published_after,
          publishedBefore: params.published_before,
        });

        const items = (res.data.items || []) as YouTubeSearchResult[];
        const total = res.data.pageInfo?.totalResults || 0;

        if (!items.length) {
          return {
            content: [{ type: "text" as const, text: `No results found for "${params.query}".` }],
          };
        }

        const output = {
          total_results: total,
          results_per_page: res.data.pageInfo?.resultsPerPage || params.max_results,
          next_page_token: res.data.nextPageToken || undefined,
          prev_page_token: res.data.prevPageToken || undefined,
          has_more: !!res.data.nextPageToken,
          items: items.map((item) => ({
            kind: item.id.kind,
            video_id: item.id.videoId,
            channel_id: item.id.channelId,
            playlist_id: item.id.playlistId,
            title: item.snippet.title,
            description: item.snippet.description,
            channel_title: item.snippet.channelTitle,
            published_at: item.snippet.publishedAt,
            thumbnail: item.snippet.thumbnails?.medium?.url || item.snippet.thumbnails?.default?.url,
          })),
        };

        let text: string;
        if (params.response_format === ResponseFormat.MARKDOWN) {
          const lines = [
            `# YouTube Search: "${params.query}"`,
            `Found ${formatNumber(total)} results\n`,
          ];
          for (const item of output.items) {
            const id = item.video_id || item.channel_id || item.playlist_id || "?";
            lines.push(`## ${item.title}`);
            lines.push(`- **ID**: ${id}`);
            lines.push(`- **Channel**: ${item.channel_title}`);
            lines.push(`- **Published**: ${formatDate(item.published_at)}`);
            if (item.video_id) lines.push(`- **URL**: https://youtu.be/${item.video_id}`);
            lines.push("");
          }
          if (output.next_page_token) {
            lines.push(`_Next page token: \`${output.next_page_token}\`_`);
          }
          text = lines.join("\n");
        } else {
          text = JSON.stringify(output, null, 2);
        }

        return { content: [{ type: "text" as const, text: truncateIfNeeded(text) }] };
      } catch (error) {
        return { content: [{ type: "text" as const, text: handleYouTubeError(error) }] };
      }
    }
  );

  // ━━ youtube_get_video ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  server.registerTool(
    "youtube_get_video",
    {
      title: "Get Video Details",
      description: `Get detailed metadata, statistics, and status for a YouTube video.

Args:
  - video_id (string): YouTube video ID
  - response_format ('markdown'|'json'): Output format

Returns: Title, description, tags, view/like/comment counts, duration, privacy status, category, publish date.`,
      inputSchema: GetVideoSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async (params: z.infer<typeof GetVideoSchema>) => {
      try {
        const yt = getYouTubeClient();
        const res = await yt.videos.list({
          part: ["snippet", "contentDetails", "statistics", "status"],
          id: [params.video_id],
        });

        const video = res.data.items?.[0] as YouTubeVideo | undefined;
        if (!video) {
          return {
            content: [{ type: "text" as const, text: `No video found with ID "${params.video_id}".` }],
          };
        }

        const output = {
          id: video.id,
          title: video.snippet.title,
          description: video.snippet.description,
          channel: video.snippet.channelTitle,
          channel_id: video.snippet.channelId,
          published_at: video.snippet.publishedAt,
          tags: video.snippet.tags || [],
          category_id: video.snippet.categoryId,
          duration: video.contentDetails?.duration,
          definition: video.contentDetails?.definition,
          privacy_status: video.status?.privacyStatus,
          made_for_kids: video.status?.madeForKids,
          views: video.statistics?.viewCount,
          likes: video.statistics?.likeCount,
          comments: video.statistics?.commentCount,
          url: `https://youtu.be/${video.id}`,
          thumbnail: video.snippet.thumbnails?.maxres?.url ||
            video.snippet.thumbnails?.high?.url ||
            video.snippet.thumbnails?.medium?.url,
        };

        let text: string;
        if (params.response_format === ResponseFormat.MARKDOWN) {
          text = [
            `# ${output.title}`,
            `**URL**: ${output.url}`,
            `**Channel**: ${output.channel}`,
            `**Published**: ${formatDate(output.published_at)}`,
            `**Duration**: ${output.duration ? formatDuration(output.duration) : "N/A"}`,
            `**Privacy**: ${output.privacy_status || "N/A"}`,
            "",
            `## Statistics`,
            `- Views: ${output.views ? formatNumber(output.views) : "N/A"}`,
            `- Likes: ${output.likes ? formatNumber(output.likes) : "N/A"}`,
            `- Comments: ${output.comments ? formatNumber(output.comments) : "N/A"}`,
            "",
            `## Tags`,
            output.tags.length ? output.tags.map((t) => `\`${t}\``).join(", ") : "_No tags_",
            "",
            `## Description`,
            output.description || "_No description_",
          ].join("\n");
        } else {
          text = JSON.stringify(output, null, 2);
        }

        return { content: [{ type: "text" as const, text: truncateIfNeeded(text) }] };
      } catch (error) {
        return { content: [{ type: "text" as const, text: handleYouTubeError(error) }] };
      }
    }
  );

  // ━━ youtube_get_channel ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  server.registerTool(
    "youtube_get_channel",
    {
      title: "Get Channel Info",
      description: `Get metadata and statistics for a YouTube channel.

Args:
  - channel_id (string, optional): Channel ID. Omit + use OAuth to get your own channel.
  - for_username (string, optional): Legacy YouTube username
  - response_format ('markdown'|'json'): Output format

Returns: Channel name, description, subscriber/view/video counts, custom URL, creation date.`,
      inputSchema: GetChannelSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async (params: z.infer<typeof GetChannelSchema>) => {
      try {
        const yt = getYouTubeClient();
        const query: Record<string, unknown> = {
          part: ["snippet", "statistics", "contentDetails"],
        };
        if (params.channel_id) query.id = [params.channel_id];
        else if (params.for_username) query.forUsername = params.for_username;
        else query.mine = true;

        const res = await yt.channels.list(query as Parameters<typeof yt.channels.list>[0]);
        const ch = res.data.items?.[0] as YouTubeChannel | undefined;
        if (!ch) {
          return { content: [{ type: "text" as const, text: "Channel not found." }] };
        }

        const output = {
          id: ch.id,
          title: ch.snippet.title,
          description: ch.snippet.description,
          custom_url: ch.snippet.customUrl,
          country: ch.snippet.country,
          created_at: ch.snippet.publishedAt,
          subscribers: ch.statistics?.subscriberCount,
          total_views: ch.statistics?.viewCount,
          video_count: ch.statistics?.videoCount,
          uploads_playlist: ch.contentDetails?.relatedPlaylists?.uploads,
          thumbnail: ch.snippet.thumbnails?.high?.url || ch.snippet.thumbnails?.default?.url,
        };

        let text: string;
        if (params.response_format === ResponseFormat.MARKDOWN) {
          text = [
            `# ${output.title}`,
            output.custom_url ? `**URL**: https://youtube.com/${output.custom_url}` : "",
            `**Created**: ${formatDate(output.created_at)}`,
            output.country ? `**Country**: ${output.country}` : "",
            "",
            `## Statistics`,
            `- Subscribers: ${output.subscribers ? formatNumber(output.subscribers) : "Hidden"}`,
            `- Total Views: ${output.total_views ? formatNumber(output.total_views) : "N/A"}`,
            `- Videos: ${output.video_count ? formatNumber(output.video_count) : "N/A"}`,
            "",
            output.uploads_playlist ? `**Uploads Playlist**: ${output.uploads_playlist}` : "",
            "",
            `## About`,
            output.description || "_No description_",
          ]
            .filter(Boolean)
            .join("\n");
        } else {
          text = JSON.stringify(output, null, 2);
        }

        return { content: [{ type: "text" as const, text: truncateIfNeeded(text) }] };
      } catch (error) {
        return { content: [{ type: "text" as const, text: handleYouTubeError(error) }] };
      }
    }
  );

  // ━━ youtube_list_channel_videos ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  server.registerTool(
    "youtube_list_channel_videos",
    {
      title: "List Channel Videos",
      description: `List videos uploaded to a channel (via the uploads playlist).

Args:
  - channel_id (string, optional): Channel ID. Omit + use OAuth to list your own uploads.
  - max_results (number 1-50, default 25): Results per page
  - page_token (string, optional): Pagination token
  - response_format ('markdown'|'json'): Output format

Returns: List of videos with titles, IDs, publish dates, and thumbnails.`,
      inputSchema: ListChannelVideosSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async (params: z.infer<typeof ListChannelVideosSchema>) => {
      try {
        const yt = getYouTubeClient();

        // First get the uploads playlist ID
        const chQuery: Record<string, unknown> = {
          part: ["contentDetails"],
        };
        if (params.channel_id) chQuery.id = [params.channel_id];
        else chQuery.mine = true;

        const chRes = await yt.channels.list(chQuery as Parameters<typeof yt.channels.list>[0]);
        const uploadsPlaylist =
          chRes.data.items?.[0]?.contentDetails?.relatedPlaylists?.uploads;

        if (!uploadsPlaylist) {
          return {
            content: [{ type: "text" as const, text: "Could not find uploads playlist for this channel." }],
          };
        }

        const res = await yt.playlistItems.list({
          part: ["snippet"],
          playlistId: uploadsPlaylist,
          maxResults: params.max_results,
          pageToken: params.page_token,
        });

        const items = res.data.items || [];
        const total = res.data.pageInfo?.totalResults || 0;

        const output = {
          total_results: total,
          has_more: !!res.data.nextPageToken,
          next_page_token: res.data.nextPageToken || undefined,
          items: items.map((item) => ({
            video_id: item.snippet?.resourceId?.videoId,
            title: item.snippet?.title,
            published_at: item.snippet?.publishedAt,
            description: item.snippet?.description?.slice(0, 200),
            thumbnail: item.snippet?.thumbnails?.medium?.url,
            position: item.snippet?.position,
          })),
        };

        let text: string;
        if (params.response_format === ResponseFormat.MARKDOWN) {
          const lines = [`# Channel Uploads`, `${formatNumber(total)} videos total\n`];
          for (const v of output.items) {
            lines.push(`- **${v.title}** (${v.video_id}) — ${formatDate(v.published_at || "")}`);
          }
          if (output.next_page_token) {
            lines.push(`\n_Next page token: \`${output.next_page_token}\`_`);
          }
          text = lines.join("\n");
        } else {
          text = JSON.stringify(output, null, 2);
        }

        return { content: [{ type: "text" as const, text: truncateIfNeeded(text) }] };
      } catch (error) {
        return { content: [{ type: "text" as const, text: handleYouTubeError(error) }] };
      }
    }
  );

  // ━━ youtube_get_video_analytics ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  server.registerTool(
    "youtube_get_video_analytics",
    {
      title: "Get Video Analytics",
      description: `Get view counts, likes, comments, duration, and engagement metrics for one or more videos.

Args:
  - video_ids (string): Comma-separated video IDs (max 50)
  - response_format ('markdown'|'json'): Output format

Returns: Per-video statistics including views, likes, comments, duration, and engagement rate.`,
      inputSchema: GetVideoAnalyticsSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async (params: z.infer<typeof GetVideoAnalyticsSchema>) => {
      try {
        const yt = getYouTubeClient();
        const ids = params.video_ids.split(",").map((s) => s.trim());

        const res = await yt.videos.list({
          part: ["snippet", "statistics", "contentDetails"],
          id: ids,
        });

        const videos = (res.data.items || []) as YouTubeVideo[];
        if (!videos.length) {
          return {
            content: [{ type: "text" as const, text: "No videos found for the provided IDs." }],
          };
        }

        const analytics = videos.map((v) => {
          const views = parseInt(v.statistics?.viewCount || "0", 10);
          const likes = parseInt(v.statistics?.likeCount || "0", 10);
          const comments = parseInt(v.statistics?.commentCount || "0", 10);
          const engagement = views > 0 ? (((likes + comments) / views) * 100).toFixed(2) : "0.00";

          return {
            id: v.id,
            title: v.snippet.title,
            published_at: v.snippet.publishedAt,
            duration: v.contentDetails?.duration,
            views,
            likes,
            comments,
            engagement_rate: `${engagement}%`,
            url: `https://youtu.be/${v.id}`,
          };
        });

        let text: string;
        if (params.response_format === ResponseFormat.MARKDOWN) {
          const lines = [`# Video Analytics\n`];
          for (const a of analytics) {
            lines.push(`## ${a.title}`);
            lines.push(`- **URL**: ${a.url}`);
            lines.push(`- **Published**: ${formatDate(a.published_at)}`);
            lines.push(`- **Duration**: ${a.duration ? formatDuration(a.duration) : "N/A"}`);
            lines.push(`- **Views**: ${formatNumber(a.views)}`);
            lines.push(`- **Likes**: ${formatNumber(a.likes)}`);
            lines.push(`- **Comments**: ${formatNumber(a.comments)}`);
            lines.push(`- **Engagement Rate**: ${a.engagement_rate}`);
            lines.push("");
          }
          text = lines.join("\n");
        } else {
          text = JSON.stringify({ videos: analytics }, null, 2);
        }

        return { content: [{ type: "text" as const, text: truncateIfNeeded(text) }] };
      } catch (error) {
        return { content: [{ type: "text" as const, text: handleYouTubeError(error) }] };
      }
    }
  );

  // ━━ youtube_update_video ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  server.registerTool(
    "youtube_update_video",
    {
      title: "Update Video Metadata",
      description: `Update the title, description, tags, privacy, or category of a YouTube video. Requires OAuth2.

Args:
  - video_id (string): Video to update
  - title (string, optional): New title
  - description (string, optional): New description
  - tags (string[], optional): New tags (replaces all existing)
  - category_id (string, optional): New category ID
  - privacy_status ('public'|'private'|'unlisted', optional): New privacy
  - made_for_kids (boolean, optional): Child-directed designation
  - response_format ('markdown'|'json'): Output format

Returns: Updated video details.`,
      inputSchema: UpdateVideoSchema,
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async (params: z.infer<typeof UpdateVideoSchema>) => {
      try {
        requireOAuth();
        const yt = getYouTubeClient();

        // First fetch current video data so we don't overwrite fields
        const current = await yt.videos.list({
          part: ["snippet", "status"],
          id: [params.video_id],
        });
        const video = current.data.items?.[0];
        if (!video) {
          return {
            content: [{ type: "text" as const, text: `Video "${params.video_id}" not found.` }],
          };
        }

        const snippet = video.snippet || {};
        const status = video.status || {};

        const updateBody: Record<string, unknown> = {
          id: params.video_id,
          snippet: {
            title: params.title ?? snippet.title,
            description: params.description ?? snippet.description,
            tags: params.tags ?? snippet.tags,
            categoryId: params.category_id ?? snippet.categoryId,
          },
          status: {
            privacyStatus: params.privacy_status ?? status.privacyStatus,
            madeForKids: params.made_for_kids ?? status.madeForKids,
          },
        };

        const res = await yt.videos.update({
          part: ["snippet", "status"],
          requestBody: updateBody as Parameters<typeof yt.videos.update>[0]["requestBody"],
        });

        const updated = res.data;
        const output = {
          id: updated.id,
          title: updated.snippet?.title,
          description: updated.snippet?.description,
          tags: updated.snippet?.tags,
          privacy_status: updated.status?.privacyStatus,
          made_for_kids: updated.status?.madeForKids,
        };

        let text: string;
        if (params.response_format === ResponseFormat.MARKDOWN) {
          text = [
            `✅ Video updated successfully!`,
            `- **Title**: ${output.title}`,
            `- **Privacy**: ${output.privacy_status}`,
            `- **URL**: https://youtu.be/${output.id}`,
          ].join("\n");
        } else {
          text = JSON.stringify(output, null, 2);
        }

        return { content: [{ type: "text" as const, text }] };
      } catch (error) {
        return { content: [{ type: "text" as const, text: handleYouTubeError(error) }] };
      }
    }
  );

  // ━━ youtube_upload_video ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  server.registerTool(
    "youtube_upload_video",
    {
      title: "Upload Video",
      description: `Upload a video file to YouTube. Requires OAuth2. Costs 1600 quota units.

Args:
  - file_path (string): Absolute path to video file on the server
  - title (string): Video title (max 100 chars)
  - description (string, optional): Description (max 5000 chars)
  - tags (string[], optional): Tags
  - category_id (string, default '22'): YouTube category ID
  - privacy_status ('public'|'private'|'unlisted', default 'private'): Privacy
  - made_for_kids (boolean, default false): Child-directed designation
  - notify_subscribers (boolean, default true): Send subscriber notification
  - response_format ('markdown'|'json'): Output format

Returns: Uploaded video ID and URL.`,
      inputSchema: UploadVideoSchema,
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: true,
      },
    },
    async (params: z.infer<typeof UploadVideoSchema>) => {
      try {
        requireOAuth();

        if (!fs.existsSync(params.file_path)) {
          return {
            content: [
              {
                type: "text" as const,
                text: `Error: File not found at "${params.file_path}". Provide an absolute path to the video file.`,
              },
            ],
          };
        }

        const yt = getYouTubeClient();
        const res = await yt.videos.insert({
          part: ["snippet", "status"],
          notifySubscribers: params.notify_subscribers,
          requestBody: {
            snippet: {
              title: params.title,
              description: params.description,
              tags: params.tags,
              categoryId: params.category_id,
            },
            status: {
              privacyStatus: params.privacy_status,
              madeForKids: params.made_for_kids,
            },
          },
          media: {
            body: fs.createReadStream(params.file_path),
          },
        });

        const videoId = res.data.id;
        const output = {
          id: videoId,
          title: res.data.snippet?.title,
          privacy_status: res.data.status?.privacyStatus,
          url: `https://youtu.be/${videoId}`,
        };

        let text: string;
        if (params.response_format === ResponseFormat.MARKDOWN) {
          text = [
            `✅ Video uploaded successfully!`,
            `- **Title**: ${output.title}`,
            `- **ID**: ${output.id}`,
            `- **Privacy**: ${output.privacy_status}`,
            `- **URL**: ${output.url}`,
          ].join("\n");
        } else {
          text = JSON.stringify(output, null, 2);
        }

        return { content: [{ type: "text" as const, text }] };
      } catch (error) {
        return { content: [{ type: "text" as const, text: handleYouTubeError(error) }] };
      }
    }
  );

  // ━━ youtube_list_playlists ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  server.registerTool(
    "youtube_list_playlists",
    {
      title: "List Playlists",
      description: `List playlists for a channel. Omit channel_id with OAuth to list your own.

Args:
  - channel_id (string, optional): Channel ID
  - max_results (number 1-50, default 25): Results per page
  - page_token (string, optional): Pagination token
  - response_format ('markdown'|'json'): Output format

Returns: List of playlists with titles, IDs, item counts, and privacy status.`,
      inputSchema: ListPlaylistsSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async (params: z.infer<typeof ListPlaylistsSchema>) => {
      try {
        const yt = getYouTubeClient();
        const query: Record<string, unknown> = {
          part: ["snippet", "contentDetails", "status"],
          maxResults: params.max_results,
          pageToken: params.page_token,
        };
        if (params.channel_id) query.channelId = params.channel_id;
        else query.mine = true;

        const res = await yt.playlists.list(query as Parameters<typeof yt.playlists.list>[0]);
        const items = (res.data.items || []) as YouTubePlaylist[];

        const output = {
          total: res.data.pageInfo?.totalResults || 0,
          has_more: !!res.data.nextPageToken,
          next_page_token: res.data.nextPageToken || undefined,
          items: items.map((pl) => ({
            id: pl.id,
            title: pl.snippet.title,
            description: pl.snippet.description?.slice(0, 200),
            item_count: pl.contentDetails?.itemCount,
            privacy: pl.status?.privacyStatus,
            published_at: pl.snippet.publishedAt,
          })),
        };

        let text: string;
        if (params.response_format === ResponseFormat.MARKDOWN) {
          const lines = [`# Playlists (${output.total} total)\n`];
          for (const pl of output.items) {
            lines.push(`- **${pl.title}** (${pl.id}) — ${pl.item_count} videos, ${pl.privacy}`);
          }
          if (output.next_page_token) {
            lines.push(`\n_Next page token: \`${output.next_page_token}\`_`);
          }
          text = lines.join("\n");
        } else {
          text = JSON.stringify(output, null, 2);
        }

        return { content: [{ type: "text" as const, text: truncateIfNeeded(text) }] };
      } catch (error) {
        return { content: [{ type: "text" as const, text: handleYouTubeError(error) }] };
      }
    }
  );

  // ━━ youtube_create_playlist ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  server.registerTool(
    "youtube_create_playlist",
    {
      title: "Create Playlist",
      description: `Create a new YouTube playlist. Requires OAuth2.

Args:
  - title (string): Playlist title
  - description (string, optional): Description
  - privacy_status ('public'|'private'|'unlisted', default 'private'): Privacy
  - response_format ('markdown'|'json'): Output format

Returns: New playlist ID and URL.`,
      inputSchema: CreatePlaylistSchema,
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: true,
      },
    },
    async (params: z.infer<typeof CreatePlaylistSchema>) => {
      try {
        requireOAuth();
        const yt = getYouTubeClient();
        const res = await yt.playlists.insert({
          part: ["snippet", "status"],
          requestBody: {
            snippet: { title: params.title, description: params.description },
            status: { privacyStatus: params.privacy_status },
          },
        });

        const output = {
          id: res.data.id,
          title: res.data.snippet?.title,
          privacy: res.data.status?.privacyStatus,
          url: `https://youtube.com/playlist?list=${res.data.id}`,
        };

        let text: string;
        if (params.response_format === ResponseFormat.MARKDOWN) {
          text = `✅ Playlist created!\n- **Title**: ${output.title}\n- **ID**: ${output.id}\n- **URL**: ${output.url}`;
        } else {
          text = JSON.stringify(output, null, 2);
        }
        return { content: [{ type: "text" as const, text }] };
      } catch (error) {
        return { content: [{ type: "text" as const, text: handleYouTubeError(error) }] };
      }
    }
  );

  // ━━ youtube_add_to_playlist ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  server.registerTool(
    "youtube_add_to_playlist",
    {
      title: "Add Video to Playlist",
      description: `Add a video to an existing YouTube playlist. Requires OAuth2.

Args:
  - playlist_id (string): Target playlist ID
  - video_id (string): Video ID to add
  - position (number, optional): 0-based position (omit to add at end)
  - response_format ('markdown'|'json'): Output format

Returns: Confirmation with playlist item ID.`,
      inputSchema: AddToPlaylistSchema,
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: true,
      },
    },
    async (params: z.infer<typeof AddToPlaylistSchema>) => {
      try {
        requireOAuth();
        const yt = getYouTubeClient();

        const body: Record<string, unknown> = {
          snippet: {
            playlistId: params.playlist_id,
            resourceId: { kind: "youtube#video", videoId: params.video_id },
            ...(params.position !== undefined ? { position: params.position } : {}),
          },
        };

        const res = await yt.playlistItems.insert({
          part: ["snippet"],
          requestBody: body as Parameters<typeof yt.playlistItems.insert>[0]["requestBody"],
        });

        const output = {
          playlist_item_id: res.data.id,
          video_id: params.video_id,
          playlist_id: params.playlist_id,
          position: res.data.snippet?.position,
        };

        let text: string;
        if (params.response_format === ResponseFormat.MARKDOWN) {
          text = `✅ Video \`${params.video_id}\` added to playlist \`${params.playlist_id}\` at position ${output.position}.`;
        } else {
          text = JSON.stringify(output, null, 2);
        }
        return { content: [{ type: "text" as const, text }] };
      } catch (error) {
        return { content: [{ type: "text" as const, text: handleYouTubeError(error) }] };
      }
    }
  );

  // ━━ youtube_list_comments ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  server.registerTool(
    "youtube_list_comments",
    {
      title: "List Video Comments",
      description: `List top-level comment threads on a YouTube video.

Args:
  - video_id (string): Video ID
  - order ('time'|'relevance', default 'relevance'): Sort order
  - max_results (number 1-50, default 25): Results per page
  - page_token (string, optional): Pagination token
  - response_format ('markdown'|'json'): Output format

Returns: Comments with author, text, like count, reply count, and publish date.`,
      inputSchema: ListCommentsSchema,
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async (params: z.infer<typeof ListCommentsSchema>) => {
      try {
        const yt = getYouTubeClient();
        const res = await yt.commentThreads.list({
          part: ["snippet"],
          videoId: params.video_id,
          order: params.order,
          maxResults: params.max_results,
          pageToken: params.page_token,
        });

        const items = res.data.items || [];

        const output = {
          total: res.data.pageInfo?.totalResults || items.length,
          has_more: !!res.data.nextPageToken,
          next_page_token: res.data.nextPageToken || undefined,
          comments: items.map((item) => {
            const c = item.snippet?.topLevelComment?.snippet;
            return {
              comment_id: item.id,
              author: c?.authorDisplayName,
              text: c?.textDisplay,
              likes: c?.likeCount,
              replies: item.snippet?.totalReplyCount,
              published_at: c?.publishedAt,
            };
          }),
        };

        let text: string;
        if (params.response_format === ResponseFormat.MARKDOWN) {
          const lines = [`# Comments on ${params.video_id}\n`];
          for (const c of output.comments) {
            lines.push(`**${c.author}** (${formatDate(c.published_at || "")}) — ${c.likes} likes, ${c.replies} replies`);
            lines.push(`> ${c.text}\n`);
          }
          if (output.next_page_token) {
            lines.push(`_Next page token: \`${output.next_page_token}\`_`);
          }
          text = lines.join("\n");
        } else {
          text = JSON.stringify(output, null, 2);
        }

        return { content: [{ type: "text" as const, text: truncateIfNeeded(text) }] };
      } catch (error) {
        return { content: [{ type: "text" as const, text: handleYouTubeError(error) }] };
      }
    }
  );

  // ━━ youtube_reply_to_comment ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  server.registerTool(
    "youtube_reply_to_comment",
    {
      title: "Reply to Comment",
      description: `Reply to a top-level YouTube comment. Requires OAuth2.

Args:
  - parent_comment_id (string): ID of the top-level comment
  - text (string): Reply text
  - response_format ('markdown'|'json'): Output format

Returns: Reply ID and confirmation.`,
      inputSchema: ReplyToCommentSchema,
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
        openWorldHint: true,
      },
    },
    async (params: z.infer<typeof ReplyToCommentSchema>) => {
      try {
        requireOAuth();
        const yt = getYouTubeClient();
        const res = await yt.comments.insert({
          part: ["snippet"],
          requestBody: {
            snippet: {
              parentId: params.parent_comment_id,
              textOriginal: params.text,
            },
          },
        });

        const output = { reply_id: res.data.id, text: res.data.snippet?.textDisplay };

        let text: string;
        if (params.response_format === ResponseFormat.MARKDOWN) {
          text = `✅ Reply posted (ID: ${output.reply_id})`;
        } else {
          text = JSON.stringify(output, null, 2);
        }
        return { content: [{ type: "text" as const, text }] };
      } catch (error) {
        return { content: [{ type: "text" as const, text: handleYouTubeError(error) }] };
      }
    }
  );

  // ━━ youtube_delete_video ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  server.registerTool(
    "youtube_delete_video",
    {
      title: "Delete Video",
      description: `Permanently delete a YouTube video. This action is IRREVERSIBLE. Requires OAuth2.

Args:
  - video_id (string): Video ID to delete

Returns: Confirmation of deletion.`,
      inputSchema: DeleteVideoSchema,
      annotations: {
        readOnlyHint: false,
        destructiveHint: true,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async (params: z.infer<typeof DeleteVideoSchema>) => {
      try {
        requireOAuth();
        const yt = getYouTubeClient();
        await yt.videos.delete({ id: params.video_id });
        return {
          content: [{ type: "text" as const, text: `✅ Video \`${params.video_id}\` deleted permanently.` }],
        };
      } catch (error) {
        return { content: [{ type: "text" as const, text: handleYouTubeError(error) }] };
      }
    }
  );

  // ━━ youtube_set_thumbnail ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  server.registerTool(
    "youtube_set_thumbnail",
    {
      title: "Set Video Thumbnail",
      description: `Upload a custom thumbnail for a YouTube video. Requires OAuth2 and a verified account.

Args:
  - video_id (string): Video ID
  - image_path (string): Absolute path to image file (JPEG/PNG/GIF/BMP, max 2 MB)
  - response_format ('markdown'|'json'): Output format

Returns: Thumbnail URLs for all sizes.`,
      inputSchema: SetThumbnailSchema,
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: true,
      },
    },
    async (params: z.infer<typeof SetThumbnailSchema>) => {
      try {
        requireOAuth();

        if (!fs.existsSync(params.image_path)) {
          return {
            content: [
              { type: "text" as const, text: `Error: Image file not found at "${params.image_path}".` },
            ],
          };
        }

        const yt = getYouTubeClient();
        const res = await yt.thumbnails.set({
          videoId: params.video_id,
          media: {
            body: fs.createReadStream(params.image_path),
          },
        });

        const thumbs = res.data.items?.[0] || {};
        const output = { video_id: params.video_id, thumbnails: thumbs };

        let text: string;
        if (params.response_format === ResponseFormat.MARKDOWN) {
          text = `✅ Thumbnail updated for video \`${params.video_id}\`.`;
        } else {
          text = JSON.stringify(output, null, 2);
        }
        return { content: [{ type: "text" as const, text }] };
      } catch (error) {
        return { content: [{ type: "text" as const, text: handleYouTubeError(error) }] };
      }
    }
  );
}
