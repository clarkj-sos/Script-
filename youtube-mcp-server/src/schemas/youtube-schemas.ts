import { z } from "zod";

const responseFormat = z
  .enum(["markdown", "json"])
  .default("markdown")
  .describe("Output format: markdown for human-readable, json for structured data");

// ── youtube_search ─────────────────────────────────────────────────────

export const SearchVideosSchema = z.object({
  query: z.string().describe("Search terms"),
  order: z
    .enum(["relevance", "date", "viewCount", "rating"])
    .default("relevance")
    .describe("Sort order"),
  type: z
    .enum(["video", "channel", "playlist"])
    .default("video")
    .describe("Resource type to search"),
  channel_id: z.string().optional().describe("Restrict results to this channel"),
  published_after: z
    .string()
    .optional()
    .describe("ISO 8601 date — only results after this date"),
  published_before: z
    .string()
    .optional()
    .describe("ISO 8601 date — only results before this date"),
  max_results: z.number().min(1).max(50).default(25).describe("Results per page"),
  page_token: z.string().optional().describe("Pagination token from a previous response"),
  response_format: responseFormat,
});

// ── youtube_get_video ──────────────────────────────────────────────────

export const GetVideoSchema = z.object({
  video_id: z.string().describe("YouTube video ID"),
  response_format: responseFormat,
});

// ── youtube_get_channel ────────────────────────────────────────────────

export const GetChannelSchema = z.object({
  channel_id: z.string().optional().describe("Channel ID. Omit with OAuth to get your own channel"),
  for_username: z.string().optional().describe("Legacy YouTube username"),
  response_format: responseFormat,
});

// ── youtube_list_channel_videos ────────────────────────────────────────

export const ListChannelVideosSchema = z.object({
  channel_id: z
    .string()
    .optional()
    .describe("Channel ID. Omit with OAuth to list your own uploads"),
  max_results: z.number().min(1).max(50).default(25).describe("Results per page"),
  page_token: z.string().optional().describe("Pagination token"),
  response_format: responseFormat,
});

// ── youtube_get_video_analytics ────────────────────────────────────────

export const GetVideoAnalyticsSchema = z.object({
  video_ids: z.string().describe("Comma-separated video IDs (max 50)"),
  response_format: responseFormat,
});

// ── youtube_update_video ───────────────────────────────────────────────

export const UpdateVideoSchema = z.object({
  video_id: z.string().describe("Video ID to update"),
  title: z.string().optional().describe("New title"),
  description: z.string().optional().describe("New description"),
  tags: z.array(z.string()).optional().describe("New tags (replaces all existing)"),
  category_id: z.string().optional().describe("New category ID"),
  privacy_status: z
    .enum(["public", "private", "unlisted"])
    .optional()
    .describe("New privacy status"),
  made_for_kids: z.boolean().optional().describe("Child-directed designation"),
  response_format: responseFormat,
});

// ── youtube_upload_video ───────────────────────────────────────────────

export const UploadVideoSchema = z.object({
  file_path: z.string().describe("Absolute path to video file on the server"),
  title: z.string().max(100).describe("Video title (max 100 chars)"),
  description: z.string().max(5000).optional().describe("Description (max 5000 chars)"),
  tags: z.array(z.string()).optional().describe("Tags"),
  category_id: z.string().default("22").describe("YouTube category ID"),
  privacy_status: z
    .enum(["public", "private", "unlisted"])
    .default("private")
    .describe("Privacy status"),
  made_for_kids: z.boolean().default(false).describe("Child-directed designation"),
  notify_subscribers: z.boolean().default(true).describe("Send subscriber notification"),
  response_format: responseFormat,
});

// ── youtube_list_playlists ─────────────────────────────────────────────

export const ListPlaylistsSchema = z.object({
  channel_id: z.string().optional().describe("Channel ID. Omit with OAuth to list your own"),
  max_results: z.number().min(1).max(50).default(25).describe("Results per page"),
  page_token: z.string().optional().describe("Pagination token"),
  response_format: responseFormat,
});

// ── youtube_create_playlist ────────────────────────────────────────────

export const CreatePlaylistSchema = z.object({
  title: z.string().describe("Playlist title"),
  description: z.string().optional().describe("Description"),
  privacy_status: z
    .enum(["public", "private", "unlisted"])
    .default("private")
    .describe("Privacy status"),
  response_format: responseFormat,
});

// ── youtube_add_to_playlist ────────────────────────────────────────────

export const AddToPlaylistSchema = z.object({
  playlist_id: z.string().describe("Target playlist ID"),
  video_id: z.string().describe("Video ID to add"),
  position: z.number().optional().describe("0-based position (omit to add at end)"),
  response_format: responseFormat,
});

// ── youtube_list_comments ──────────────────────────────────────────────

export const ListCommentsSchema = z.object({
  video_id: z.string().describe("Video ID"),
  order: z.enum(["time", "relevance"]).default("relevance").describe("Sort order"),
  max_results: z.number().min(1).max(50).default(25).describe("Results per page"),
  page_token: z.string().optional().describe("Pagination token"),
  response_format: responseFormat,
});

// ── youtube_reply_to_comment ───────────────────────────────────────────

export const ReplyToCommentSchema = z.object({
  parent_comment_id: z.string().describe("ID of the top-level comment"),
  text: z.string().describe("Reply text"),
  response_format: responseFormat,
});

// ── youtube_delete_video ───────────────────────────────────────────────

export const DeleteVideoSchema = z.object({
  video_id: z.string().describe("Video ID to delete"),
});

// ── youtube_set_thumbnail ──────────────────────────────────────────────

export const SetThumbnailSchema = z.object({
  video_id: z.string().describe("Video ID"),
  image_path: z.string().describe("Absolute path to image file (JPEG/PNG/GIF/BMP, max 2 MB)"),
  response_format: responseFormat,
});
