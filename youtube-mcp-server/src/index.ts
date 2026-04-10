import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import express from "express";
import { registerYouTubeTools } from "./tools/youtube-tools.js";

const SERVER_NAME = "youtube-mcp-server";
const SERVER_VERSION = "1.0.0";

async function main() {
  const transport = process.env.TRANSPORT || "stdio";

  const server = new McpServer({
    name: SERVER_NAME,
    version: SERVER_VERSION,
  });

  registerYouTubeTools(server);

  if (transport === "http") {
    const port = parseInt(process.env.PORT || "3000", 10);
    const app = express();
    app.use(express.json());

    app.get("/health", (_req, res) => {
      res.json({ status: "ok", server: SERVER_NAME, version: SERVER_VERSION });
    });

    const httpTransport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined });

    app.post("/mcp", async (req, res) => {
      await httpTransport.handleRequest(req, res, req.body);
    });

    app.get("/mcp", async (req, res) => {
      await httpTransport.handleRequest(req, res);
    });

    app.delete("/mcp", async (req, res) => {
      await httpTransport.handleRequest(req, res);
    });

    await server.connect(httpTransport);

    app.listen(port, () => {
      console.error(`YouTube MCP server listening on http://localhost:${port}/mcp`);
    });
  } else {
    const stdioTransport = new StdioServerTransport();
    await server.connect(stdioTransport);
    console.error("YouTube MCP server running on stdio");
  }
}

main().catch((err) => {
  console.error("Fatal error:", err);
  process.exit(1);
});
