import { google, youtube_v3 } from "googleapis";

let youtubeClient: youtube_v3.Youtube | null = null;
let oauthClient: InstanceType<typeof google.auth.OAuth2> | null = null;

/**
 * Get or create the YouTube API client.
 * Uses OAuth2 if credentials are available, otherwise falls back to API key.
 */
export function getYouTubeClient(): youtube_v3.Youtube {
  if (youtubeClient) return youtubeClient;

  const clientId = process.env.YOUTUBE_CLIENT_ID;
  const clientSecret = process.env.YOUTUBE_CLIENT_SECRET;
  const refreshToken = process.env.YOUTUBE_REFRESH_TOKEN;
  const apiKey = process.env.YOUTUBE_API_KEY;

  if (clientId && clientSecret && refreshToken) {
    oauthClient = new google.auth.OAuth2(clientId, clientSecret);
    oauthClient.setCredentials({ refresh_token: refreshToken });
    youtubeClient = google.youtube({ version: "v3", auth: oauthClient });
  } else if (apiKey) {
    youtubeClient = google.youtube({ version: "v3", auth: apiKey });
  } else {
    throw new Error(
      "Missing YouTube credentials. Set either YOUTUBE_API_KEY for read-only access, " +
      "or YOUTUBE_CLIENT_ID + YOUTUBE_CLIENT_SECRET + YOUTUBE_REFRESH_TOKEN for full access (uploads, updates, etc.)."
    );
  }

  return youtubeClient;
}

/**
 * Check whether the client has OAuth (write) capabilities.
 */
export function hasOAuthAccess(): boolean {
  return oauthClient !== null;
}

/**
 * Standardized error handler for YouTube API errors.
 */
export function handleYouTubeError(error: unknown): string {
  if (error instanceof Error) {
    const msg = error.message;

    if (msg.includes("quotaExceeded")) {
      return "Error: YouTube API quota exceeded for today. The default quota is 10,000 units/day. Try again tomorrow or request a quota increase in Google Cloud Console.";
    }
    if (msg.includes("forbidden") || msg.includes("403")) {
      return "Error: Permission denied. This operation requires OAuth2 authentication. Ensure YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, and YOUTUBE_REFRESH_TOKEN are set.";
    }
    if (msg.includes("notFound") || msg.includes("404")) {
      return "Error: Resource not found. Please verify the ID is correct.";
    }
    if (msg.includes("badRequest") || msg.includes("400")) {
      return `Error: Bad request — ${msg}. Check parameter values and try again.`;
    }
    if (msg.includes("unauthorized") || msg.includes("401")) {
      return "Error: Authentication failed. Your API key or OAuth token may be invalid or expired. Regenerate credentials and restart the server.";
    }

    return `Error: ${msg}`;
  }

  return `Error: Unexpected error — ${String(error)}`;
}

/**
 * Format an ISO date string to a human-readable form.
 */
export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

/**
 * Format a large number with commas.
 */
export function formatNumber(n: string | number): string {
  return Number(n).toLocaleString("en-US");
}

/**
 * Parse ISO 8601 duration (PT1H2M3S) to human-readable.
 */
export function formatDuration(iso: string): string {
  const match = iso.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
  if (!match) return iso;
  const h = match[1] ? `${match[1]}h ` : "";
  const m = match[2] ? `${match[2]}m ` : "";
  const s = match[3] ? `${match[3]}s` : "";
  return (h + m + s).trim() || "0s";
}
