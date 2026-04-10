export const CHARACTER_LIMIT = 50_000;

export const ResponseFormat = {
  MARKDOWN: "markdown",
  JSON: "json",
} as const;

export type ResponseFormatType = (typeof ResponseFormat)[keyof typeof ResponseFormat];

export const YOUTUBE_SCOPES = [
  "https://www.googleapis.com/auth/youtube",
  "https://www.googleapis.com/auth/youtube.upload",
  "https://www.googleapis.com/auth/youtube.force-ssl",
];
