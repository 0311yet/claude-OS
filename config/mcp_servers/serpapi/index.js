#!/usr/bin/env node

/**
 * SerpAPI MCP Server - Web search via Google using SerpAPI.
 *
 * Required environment variable:
 *   SERPAPI_API_KEY — your SerpAPI key (https://serpapi.com)
 *
 * Provides tools:
 *   web_search — search the web and return structured results
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { getJson } from "serpapi";
import { z } from "zod";

const MAX_QUERY_LENGTH = 500;
const MAX_RESULTS = 20;

const server = new McpServer({
  name: "serpapi-search",
  version: "1.0.0",
});

// ---------- Tools ----------

server.tool(
  "web_search",
  "Search the web using Google via SerpAPI. Returns titles, URLs, and snippets.",
  {
    query: z.string().max(MAX_QUERY_LENGTH).describe("Search query string"),
    num: z.number().optional().default(10).describe("Number of results (1-20)"),
  },
  async ({ query, num }) => {
    const apiKey = process.env.SERPAPI_API_KEY;
    if (!apiKey) {
      return {
        content: [
          {
            type: "text",
            text: "Error: SERPAPI_API_KEY is not configured. Add it to config/secrets.json.",
          },
        ],
        isError: true,
      };
    }

    // Sanitize: trim and limit length
    const safeQuery = query.trim().slice(0, MAX_QUERY_LENGTH);
    if (!safeQuery) {
      return {
        content: [{ type: "text", text: "Error: empty search query." }],
        isError: true,
      };
    }

    const safeNum = Math.min(Math.max(num, 1), MAX_RESULTS);

    try {
      const results = await getJson({
        engine: "google",
        q: safeQuery,
        api_key: apiKey,
        num: safeNum,
      });

      // Check for API-level errors
      if (results.error) {
        const errMsg = String(results.error);
        if (errMsg.includes("Invalid API key") || errMsg.includes("invalid")) {
          return { content: [{ type: "text", text: "Error: Invalid API key. Check config/secrets.json." }], isError: true };
        }
        if (errMsg.includes("limit") || errMsg.includes("quota") || errMsg.includes("429")) {
          return { content: [{ type: "text", text: "Error: API quota exhausted. Try again later." }], isError: true };
        }
        return { content: [{ type: "text", text: `Search API error: ${errMsg.slice(0, 100)}` }], isError: true };
      }

      const organic = results.organic_results || [];
      if (organic.length === 0) {
        return {
          content: [{ type: "text", text: "No results found for: " + safeQuery }],
        };
      }

      const formatted = organic
        .map(
          (r, i) =>
            `${i + 1}. ${r.title || "No title"}\n   URL: ${r.link || ""}\n   ${r.snippet || ""}`
        )
        .join("\n\n");

      return {
        content: [{ type: "text", text: formatted }],
      };
    } catch (e) {
      // Classify error type without exposing internals
      const msg = e.message || String(e);
      if (msg.includes("ECONNREFUSED") || msg.includes("ENOTFOUND") || msg.includes("fetch failed")) {
        return { content: [{ type: "text", text: "Error: Network error — cannot reach SerpAPI." }], isError: true };
      }
      if (msg.includes("timeout") || msg.includes("ETIMEDOUT")) {
        return { content: [{ type: "text", text: "Error: Request timed out." }], isError: true };
      }
      return { content: [{ type: "text", text: `Search failed: ${e.name || "Unknown error"}` }], isError: true };
    }
  }
);

// ---------- Start ----------

const transport = new StdioServerTransport();
await server.connect(transport);
