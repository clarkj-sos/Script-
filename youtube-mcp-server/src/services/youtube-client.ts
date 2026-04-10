import { google, youtube_v3 } from "googleapis";
import * as fs from "fs";

let cachedClient: youtube_v3.Youtube | null = null;
let oauthAvailable = false;

interface CredentialsFile {
  installed?: {
    client_id: string;
    client_secret: string;
  };
  web?: {
    client_id: string;
    client_secret: string;
  };
  refresh_token?: string;
}

function initClient(): youtube_v3.Youtube {
  if (cachedClient) return cachedClient;

  const clientId = process.env.YOUTUBE_CLIENT_ID;
  const clientSecret = process.env.YOUTUBE_CLIENT_SECRET;
  const refreshToken = process.env.YOUTUBE_REFRESH_TOKEN;
  const apiKey = process.env.YOUTUBE_API_KEY;
  const credentialsPath = process.env.YOUTUBE_CREDENTIALS_PATH;

  // Try loading credentials from file
  if (credentialsPath && fs.existsSync(credentialsPath)) {
    const raw = JSON.parse(fs.readFileSync(credentialsPath, "utf-8")) as CredentialsFile;
    const creds = raw.installed || raw.web;

    if (creds) {
      const oauth2 = new google.auth.OAuth2(creds.client_id, creds.client_secret);
      const token = raw.refresh_token || refreshToken;
      if (token) {
        oauth2.setCredentials({ refresh_token: token });
        oauthAvailable = true;
        cachedClient = google.youtube({ version: "v3", auth: oauth2 });
        return cachedClient;
      }
    }
  }

  // Try environment variables for OAuth
  if (clientId && clientSecret && refreshToken) {
    const oauth2 = new google.auth.OAuth2(clientId, clientSecret);
    oauth2.setCredentials({ refresh_token: refreshToken });
    oauthAvailable = true;
    cachedClient = google.youtube({ version: "v3", auth: oauth2 });
    return cachedClient;
  }

  // Fall back to API key (read-only)
  if (apiKey) {
    oauthAvailable = false;
    cachedClient = google.youtube({ version: "v3", auth: apiKey });
    return cachedClient;
  }

  throw new Error(
    "No YouTube credentials found. Set YOUTUBE_CLIENT_ID + YOUTUBE_CLIENT_SECRET + YOUTUBE_REFRESH_TOKEN, " +
      "or YOUTUBE_CREDENTIALS_PATH, or YOUTUBE_API_KEY."
  );
}

export function getYouTubeClient(): youtube_v3.Youtube {
  return initClient();
}

export function hasOAuthAccess(): boolean {
  initClient();
  return oauthAvailable;
}

export function handleYouTubeError(error: unknown): string {
  if (error instanceof Error) {
    const msg = error.message;

    if (msg.includes("quotaExceeded")) {
      return "YouTube API quota exceeded. The daily quota resets at midnight Pacific Time. " +
        "Consider using a different API key or waiting until the quota resets.";
    }
    if (msg.includes("forbidden") || msg.includes("insufficientPermissions")) {
      return "Insufficient permissions. Ensure your OAuth token has the required YouTube scopes.";
    }
    if (msg.includes("notFound")) {
      return "The requested resource was not found. Check the ID and try again.";
    }
    if (msg.includes("unauthorized") || msg.includes("invalid_grant")) {
      return "Authentication failed. Your refresh token may be expired — run the OAuth setup again.";
    }

    return `YouTube API error: ${msg}`;
  }
  return `Unknown error: ${String(error)}`;
}

export function formatDate(iso: string): string {
  if (!iso) return "N/A";
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

export function formatNumber(n: string | number): string {
  const num = typeof n === "string" ? parseInt(n, 10) : n;
  if (isNaN(num)) return String(n);
  return num.toLocaleString("en-US");
}

export function formatDuration(iso8601: string): string {
  const match = iso8601.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
  if (!match) return iso8601;
  const h = match[1] ? `${match[1]}h ` : "";
  const m = match[2] ? `${match[2]}m ` : "";
  const s = match[3] ? `${match[3]}s` : "";
  return (h + m + s).trim() || "0s";
}
