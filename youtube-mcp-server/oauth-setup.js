#!/usr/bin/env node

/**
 * OAuth setup wizard for the YouTube MCP server.
 *
 * Usage:
 *   node oauth-setup.js
 *
 * Prerequisites:
 *   1. Create a project at https://console.cloud.google.com
 *   2. Enable "YouTube Data API v3"
 *   3. Create OAuth 2.0 credentials (Desktop app type)
 *   4. Download the JSON and save it as youtube-credentials.json in this directory
 *      OR be ready to paste your Client ID and Client Secret when prompted.
 */

import { google } from "googleapis";
import * as fs from "fs";
import * as http from "http";
import * as url from "url";
import * as readline from "readline";

const SCOPES = [
  "https://www.googleapis.com/auth/youtube",
  "https://www.googleapis.com/auth/youtube.upload",
  "https://www.googleapis.com/auth/youtube.force-ssl",
];
const CREDS_PATH = "./youtube-credentials.json";
const REDIRECT_PORT = 8976;
const REDIRECT_URI = `http://localhost:${REDIRECT_PORT}/callback`;

function ask(question) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => rl.question(question, (ans) => { rl.close(); resolve(ans.trim()); }));
}

async function getCredentials() {
  if (fs.existsSync(CREDS_PATH)) {
    console.log(`\nFound ${CREDS_PATH} — reading credentials...`);
    const raw = JSON.parse(fs.readFileSync(CREDS_PATH, "utf-8"));
    const creds = raw.installed || raw.web;
    if (creds) return { clientId: creds.client_id, clientSecret: creds.client_secret };
    console.log("Could not parse credentials file. Falling back to manual entry.\n");
  }

  const clientId = await ask("Enter your YouTube OAuth Client ID: ");
  const clientSecret = await ask("Enter your YouTube OAuth Client Secret: ");
  return { clientId, clientSecret };
}

async function waitForAuthCode(authUrl) {
  // Try to open the URL in a browser
  let opened = false;
  try {
    const open = (await import("open")).default;
    await open(authUrl);
    opened = true;
  } catch {
    // 'open' package not installed — that's fine
  }

  if (opened) {
    console.log("\nA browser window should have opened. If not, visit this URL:\n");
  } else {
    console.log("\nOpen this URL in your browser:\n");
  }
  console.log(`  ${authUrl}\n`);

  return new Promise((resolve, reject) => {
    const server = http.createServer((req, res) => {
      const parsed = url.parse(req.url, true);
      if (parsed.pathname === "/callback" && parsed.query.code) {
        res.writeHead(200, { "Content-Type": "text/html" });
        res.end("<h2>Authorization successful!</h2><p>You can close this tab.</p>");
        server.close();
        resolve(parsed.query.code);
      } else {
        res.writeHead(400);
        res.end("Missing authorization code");
      }
    });

    server.listen(REDIRECT_PORT, () => {
      console.log(`Listening for OAuth callback on port ${REDIRECT_PORT}...`);
    });

    server.on("error", (err) => {
      if (err.code === "EADDRINUSE") {
        reject(new Error(`Port ${REDIRECT_PORT} is in use. Close the process using it and try again.`));
      } else {
        reject(err);
      }
    });

    // Timeout after 5 minutes
    setTimeout(() => { server.close(); reject(new Error("Timed out waiting for authorization")); }, 300_000);
  });
}

async function main() {
  console.log("");
  console.log("╔══════════════════════════════════════════════════════════╗");
  console.log("║         YouTube MCP Server — OAuth Setup Wizard         ║");
  console.log("╚══════════════════════════════════════════════════════════╝");
  console.log("");

  const { clientId, clientSecret } = await getCredentials();

  const oauth2 = new google.auth.OAuth2(clientId, clientSecret, REDIRECT_URI);

  const authUrl = oauth2.generateAuthUrl({
    access_type: "offline",
    scope: SCOPES,
    prompt: "consent",
  });

  const code = await waitForAuthCode(authUrl);
  console.log("\nExchanging authorization code for tokens...");

  const { tokens } = await oauth2.getToken(code);

  if (!tokens.refresh_token) {
    console.error("\nWarning: No refresh token received. You may need to revoke access and try again.");
    console.error("Revoke at: https://myaccount.google.com/permissions\n");
  }

  // Save credentials
  const output = {
    installed: { client_id: clientId, client_secret: clientSecret },
    refresh_token: tokens.refresh_token,
    access_token: tokens.access_token,
    token_type: tokens.token_type,
    expiry_date: tokens.expiry_date,
  };

  fs.writeFileSync(CREDS_PATH, JSON.stringify(output, null, 2));
  console.log(`\nCredentials saved to ${CREDS_PATH}`);

  console.log("\nYou can now start the server:");
  console.log("  bash launch.sh");
  console.log("");
  console.log("Or set environment variables instead:");
  console.log(`  export YOUTUBE_CLIENT_ID='${clientId}'`);
  console.log(`  export YOUTUBE_CLIENT_SECRET='${clientSecret}'`);
  console.log(`  export YOUTUBE_REFRESH_TOKEN='${tokens.refresh_token}'`);
  console.log("");
}

main().catch((err) => {
  console.error("Setup failed:", err.message || err);
  process.exit(1);
});
