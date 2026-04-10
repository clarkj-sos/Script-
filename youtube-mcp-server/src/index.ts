import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import express from "express";
import { registerYouTubeTools } from "./tools/youtube-tools.js";

const server = new McpServer({
  name: "youtube-mcp-server",
  version: "1.0.0",
});

// Register all YouTube tools
registerYouTubeTools(server);

// ── stdio transport ─────────────────────────────────────────────────────

async function runStdio(): Promise<void> {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("YouTube MCP server running on stdio");
}

// ── Streamable HTTP transport ───────────────────────────────────────────

async function runHTTP(): Promise<void> {
  const app = express();
  app.use(express.json());

  app.post("/mcp", async (req, res) => {
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined,
      enableJsonResponse: true,
    });
    res.on("close", () => transport.close());
    await server.connect(transport);
    await transport.handleRequest(req, res, req.body);
  });

  // Health check
  app.get("/health", (_req, res) => {
    res.json({ status: "ok", server: "youtube-mcp-server" });
  });

  const port = parseInt(process.env.PORT || "3000", 10);
  app.listen(port, () => {
    console.error(`YouTube MCP server running on http://localhost:${port}/mcp`);
  });
}

// ── Transport selection ─────────────────────────────────────────────────

const transport = process.env.TRANSPORT || "stdio";
if (transport === "http") {
  runHTTP().catch((error) => {
    console.error("Server error:", error);
    process.exit(1);
  });
} else {
  runStdio().catch((error) => {
    console.error("Server error:", error);
    process.exit(1);
  });
}
