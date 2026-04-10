import { z } from "zod";
import { ResponseFormat } from "../constants.js";

// ── Shared ──────────────────────────────────────────────────────────────

const responseFormatField = z
  .nativeEnum(ResponseFormat)
  .default(ResponseFormat.MARKDOWN)
  .describe("Output format: 'markdown' for human-readable or 'json' for structured data");

const paginationFields = {
  max_results: z
    .number()
    .int()
    .min(1)
    .max(50)
    .default(25)
    .describe("Maximum results to return (1-50)"),
  page_token: z
    .string()
    .optional()
    .describe("Token for next page of results (from previous response)"),
};

// ── Search ──────────────────────────────────────────────────────────────

export const SearchVideosSchema = z
  .object({
    query: z.string().min(1).max(500).describe("Search query string"),
    order: z
      .enum(["relevance", "date", "viewCount", "rating"])
      .default("relevance")
      .describe("Sort order for results"),
    published_after: z
      .string()
      .optional()
      .describe("Filter: videos published after this ISO 8601 date (e.g. 2024-01-01T00:00:00Z)"),
    published_before: z
      .string()
      .optional()
      .describe("Filter: videos published before this ISO 8601 date"),
    channel_id: z
      .string()
      .optional()
      .describe("Restrict search to a specific channel ID"),
    type: z
      .enum(["video", "channel", "playlist"])
      .default("video")
      .describe("Type of resource to search for"),
    ...paginationFields,
    response_format: responseFormatField,
  })
  .strict();

// ── Video details ───────────────────────────────────────────────────────

export const GetVideoSchema = z
  .object({
    video_id: z
      .string()
      .min(1)
      .describe("YouTube video ID (the part after v= in the URL)"),
    response_format: responseFormatField,
  })
  .strict();

// ── Channel ─────────────────────────────────────────────────────────────

export const GetChannelSchema = z
  .object({
    channel_id: z
      .string()
      .optional()
      .describe("Channel ID. If omitted and OAuth is configured, returns the authenticated user's channel."),
    for_username: z
      .string()
      .optional()
      .describe("Legacy YouTube username to look up a channel"),
    response_format: responseFormatField,
  })
  .strict();

// ── List channel videos ─────────────────────────────────────────────────

export const ListChannelVideosSchema = z
  .object({
    channel_id: z
      .string()
      .optional()
      .describe("Channel ID. If omitted and OAuth is configured, lists the authenticated user's uploads."),
    ...paginationFields,
    response_format: responseFormatField,
  })
  .strict();

// ── Video analytics ─────────────────────────────────────────────────────

export const GetVideoAnalyticsSchema = z
  .object({
    video_ids: z
      .string()
      .min(1)
      .describe("Comma-separated list of video IDs (max 50)"),
    response_format: responseFormatField,
  })
  .strict();

// ── Update video metadata ───────────────────────────────────────────────

export const UpdateVideoSchema = z
  .object({
    video_id: z.string().min(1).describe("Video ID to update"),
    title: z.string().max(100).optional().describe("New title (max 100 chars)"),
    description: z
      .string()
      .max(5000)
      .optional()
      .describe("New description (max 5000 chars)"),
    tags: z
      .array(z.string())
      .optional()
      .describe("New tags array (replaces existing tags)"),
    category_id: z.string().optional().describe("YouTube video category ID"),
    privacy_status: z
      .enum(["public", "private", "unlisted"])
      .optional()
      .describe("Video privacy status"),
    made_for_kids: z
      .boolean()
      .optional()
      .describe("Whether the video is designated as child-directed"),
    response_format: responseFormatField,
  })
  .strict();

// ── Upload video ────────────────────────────────────────────────────────

export const UploadVideoSchema = z
  .object({
    file_path: z
      .string()
      .min(1)
      .describe("Absolute path to the video file on the server"),
    title: z.string().min(1).max(100).describe("Video title (max 100 chars)"),
    description: z
      .string()
      .max(5000)
      .default("")
      .describe("Video description (max 5000 chars)"),
    tags: z
      .array(z.string())
      .default([])
      .describe("Tags for the video"),
    category_id: z
      .string()
      .default("22")
      .describe("YouTube category ID (default 22 = People & Blogs)"),
    privacy_status: z
      .enum(["public", "private", "unlisted"])
      .default("private")
      .describe("Privacy status (default: private for safety)"),
    made_for_kids: z
      .boolean()
      .default(false)
      .describe("Whether the video is made for kids"),
    notify_subscribers: z
      .boolean()
      .default(true)
      .describe("Whether to send a notification to channel subscribers"),
    response_format: responseFormatField,
  })
  .strict();

// ── Playlists ───────────────────────────────────────────────────────────

export const ListPlaylistsSchema = z
  .object({
    channel_id: z
      .string()
      .optional()
      .describe("Channel ID. If omitted and OAuth is configured, lists the authenticated user's playlists."),
    ...paginationFields,
    response_format: responseFormatField,
  })
  .strict();

export const CreatePlaylistSchema = z
  .object({
    title: z.string().min(1).max(150).describe("Playlist title"),
    description: z
      .string()
      .max(5000)
      .default("")
      .describe("Playlist description"),
    privacy_status: z
      .enum(["public", "private", "unlisted"])
      .default("private")
      .describe("Playlist privacy status"),
    response_format: responseFormatField,
  })
  .strict();

export const AddToPlaylistSchema = z
  .object({
    playlist_id: z.string().min(1).describe("Playlist ID to add the video to"),
    video_id: z.string().min(1).describe("Video ID to add"),
    position: z
      .number()
      .int()
      .min(0)
      .optional()
      .describe("Position in the playlist (0-based). Omit to add at the end."),
    response_format: responseFormatField,
  })
  .strict();

// ── Comments ────────────────────────────────────────────────────────────

export const ListCommentsSchema = z
  .object({
    video_id: z.string().min(1).describe("Video ID to fetch comments for"),
    order: z
      .enum(["time", "relevance"])
      .default("relevance")
      .describe("Sort order for comments"),
    ...paginationFields,
    response_format: responseFormatField,
  })
  .strict();

export const ReplyToCommentSchema = z
  .object({
    parent_comment_id: z
      .string()
      .min(1)
      .describe("ID of the top-level comment to reply to"),
    text: z.string().min(1).max(10000).describe("Reply text"),
    response_format: responseFormatField,
  })
  .strict();

// ── Delete video ────────────────────────────────────────────────────────

export const DeleteVideoSchema = z
  .object({
    video_id: z.string().min(1).describe("Video ID to delete. This action is irreversible."),
  })
  .strict();

// ── Thumbnails ──────────────────────────────────────────────────────────

export const SetThumbnailSchema = z
  .object({
    video_id: z.string().min(1).describe("Video ID to set the thumbnail for"),
    image_path: z
      .string()
      .min(1)
      .describe("Absolute path to the thumbnail image file (JPEG, PNG, GIF, BMP — max 2 MB)"),
    response_format: responseFormatField,
  })
  .strict();
