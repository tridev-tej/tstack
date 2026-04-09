#!/usr/bin/env python3
"""Notion MCP Server using cookie-based session authentication."""

import json
import os
import re
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

NOTION_BASE_URL = "https://www.notion.so/api/v3"

COOKIES = os.environ.get("NOTION_COOKIES", "")
USER_ID = os.environ.get("NOTION_USER_ID", "")
SPACE_ID = os.environ.get("NOTION_SPACE_ID", "")

server = Server("notion")


def get_headers() -> dict[str, str]:
    return {
        "accept": "*/*",
        "content-type": "application/json",
        "notion-audit-log-platform": "web",
        "notion-client-version": "23.13.20260119.1242",
        "origin": "https://www.notion.so",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
        "x-notion-active-user-header": USER_ID,
        "x-notion-space-id": SPACE_ID,
    }


def parse_cookies(cookie_str: str) -> dict[str, str]:
    """Parse cookie string into dict."""
    cookies = {}
    for part in cookie_str.split("; "):
        if "=" in part:
            key, val = part.split("=", 1)
            cookies[key] = val
    return cookies


async def notion_request(endpoint: str, data: dict[str, Any] | None = None) -> dict:
    """Make request to Notion API."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{NOTION_BASE_URL}/{endpoint}",
            headers=get_headers(),
            cookies=parse_cookies(COOKIES),
            json=data or {},
        )
        resp.raise_for_status()
        return resp.json()


def extract_text_from_block(block: dict) -> str:
    """Extract text content from a Notion block."""
    props = block.get("properties", {})
    title = props.get("title", [])
    texts = []
    for item in title:
        if isinstance(item, list) and item:
            texts.append(item[0])
    return "".join(texts)


def format_block(block: dict, indent: int = 0) -> str:
    """Format a block for display."""
    block_type = block.get("type", "unknown")
    text = extract_text_from_block(block)
    prefix = "  " * indent

    if block_type == "header":
        return f"{prefix}# {text}"
    elif block_type == "sub_header":
        return f"{prefix}## {text}"
    elif block_type == "sub_sub_header":
        return f"{prefix}### {text}"
    elif block_type == "bulleted_list":
        return f"{prefix}- {text}"
    elif block_type == "numbered_list":
        return f"{prefix}1. {text}"
    elif block_type == "to_do":
        checked = block.get("properties", {}).get("checked", [[""]])[0][0] == "Yes"
        return f"{prefix}[{'x' if checked else ' '}] {text}"
    elif block_type == "code":
        return f"{prefix}```\n{text}\n{prefix}```"
    elif block_type == "quote":
        return f"{prefix}> {text}"
    elif block_type == "divider":
        return f"{prefix}---"
    elif text:
        return f"{prefix}{text}"
    return ""


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="notion_search",
            description="Search Notion pages and databases. Returns matching pages with titles and IDs.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query text"},
                    "limit": {"type": "integer", "description": "Max results (default 20)", "default": 20},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="notion_get_page",
            description="Get full content of a Notion page by ID or URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "Page ID or full Notion URL"},
                },
                "required": ["page_id"],
            },
        ),
        Tool(
            name="notion_get_block_children",
            description="Get children blocks of a specific block/page.",
            inputSchema={
                "type": "object",
                "properties": {
                    "block_id": {"type": "string", "description": "Block or page ID"},
                },
                "required": ["block_id"],
            },
        ),
        Tool(
            name="notion_query_collection",
            description="Query a Notion database/collection.",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection_id": {"type": "string", "description": "Collection/database ID"},
                    "collection_view_id": {"type": "string", "description": "View ID"},
                    "limit": {"type": "integer", "description": "Max results", "default": 50},
                },
                "required": ["collection_id", "collection_view_id"],
            },
        ),
        Tool(
            name="notion_get_space",
            description="Get workspace/space information.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="notion_get_user_content",
            description="Get user's recent pages and content.",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


def normalize_page_id(page_id: str) -> str:
    """Extract and normalize page ID from URL or raw ID."""
    match = re.search(r"([a-f0-9]{32})$", page_id.replace("-", ""))
    if match:
        raw = match.group(1)
        return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"

    if re.match(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", page_id):
        return page_id

    if re.match(r"^[a-f0-9]{32}$", page_id):
        return f"{page_id[:8]}-{page_id[8:12]}-{page_id[12:16]}-{page_id[16:20]}-{page_id[20:]}"

    return page_id


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    try:
        if name == "notion_search":
            query = arguments.get("query", "")
            limit = arguments.get("limit", 20)

            data = {
                "type": "BlocksInSpace",
                "query": query,
                "spaceId": SPACE_ID,
                "limit": limit,
                "filters": {
                    "isDeletedOnly": False,
                    "excludeTemplates": False,
                    "isNavigableOnly": True,
                    "requireEditPermissions": False,
                },
                "sort": {"field": "relevance"},
                "source": "quick_find_input_change",
            }

            result = await notion_request("search", data)

            records = result.get("recordMap", {}).get("block", {})
            output = []
            for block_id, record in records.items():
                block = record.get("value", {})
                if block.get("type") == "page":
                    title = extract_text_from_block(block) or "Untitled"
                    output.append(f"- {title}\n  ID: {block_id}")

            return [TextContent(type="text", text=f"Found {len(output)} pages:\n\n" + "\n\n".join(output) if output else "No results found")]

        elif name == "notion_get_page":
            page_id = normalize_page_id(arguments["page_id"])

            data = {
                "requests": [{"pointer": {"table": "block", "id": page_id}, "version": -1}]
            }
            result = await notion_request("syncRecordValues", data)

            block = result.get("recordMap", {}).get("block", {}).get(page_id, {}).get("value", {})
            if not block:
                return [TextContent(type="text", text=f"Page not found: {page_id}")]

            title = extract_text_from_block(block) or "Untitled"
            content_ids = block.get("content", [])

            if content_ids:
                content_data = {
                    "requests": [{"pointer": {"table": "block", "id": cid}, "version": -1} for cid in content_ids[:100]]
                }
                content_result = await notion_request("syncRecordValues", content_data)
                blocks = content_result.get("recordMap", {}).get("block", {})

                lines = [f"# {title}\n"]
                for cid in content_ids[:100]:
                    if cid in blocks:
                        block_data = blocks[cid].get("value", {})
                        line = format_block(block_data)
                        if line:
                            lines.append(line)

                return [TextContent(type="text", text="\n".join(lines))]

            return [TextContent(type="text", text=f"# {title}\n\n(Empty page)")]

        elif name == "notion_get_block_children":
            block_id = normalize_page_id(arguments["block_id"])

            data = {
                "requests": [{"pointer": {"table": "block", "id": block_id}, "version": -1}]
            }
            result = await notion_request("syncRecordValues", data)

            block = result.get("recordMap", {}).get("block", {}).get(block_id, {}).get("value", {})
            content_ids = block.get("content", [])

            if not content_ids:
                return [TextContent(type="text", text="No children found")]

            content_data = {
                "requests": [{"pointer": {"table": "block", "id": cid}, "version": -1} for cid in content_ids[:100]]
            }
            content_result = await notion_request("syncRecordValues", content_data)
            blocks = content_result.get("recordMap", {}).get("block", {})

            lines = []
            for cid in content_ids[:100]:
                if cid in blocks:
                    block_data = blocks[cid].get("value", {})
                    line = format_block(block_data)
                    if line:
                        lines.append(f"{line}\n  (ID: {cid})")

            return [TextContent(type="text", text="\n\n".join(lines) if lines else "No content")]

        elif name == "notion_query_collection":
            collection_id = arguments["collection_id"]
            view_id = arguments["collection_view_id"]
            limit = arguments.get("limit", 50)

            data = {
                "collection": {"id": collection_id},
                "collectionView": {"id": view_id},
                "loader": {
                    "type": "table",
                    "limit": limit,
                    "searchQuery": "",
                    "userTimeZone": "America/Los_Angeles",
                    "loadContentCover": True,
                },
            }

            result = await notion_request("queryCollection", data)

            records = result.get("recordMap", {}).get("block", {})
            output = []
            for block_id, record in records.items():
                block = record.get("value", {})
                if block.get("type") == "page":
                    title = extract_text_from_block(block) or "Untitled"
                    output.append(f"- {title} (ID: {block_id})")

            return [TextContent(type="text", text=f"Collection items:\n\n" + "\n".join(output) if output else "No items found")]

        elif name == "notion_get_space":
            data = {"spaceId": SPACE_ID}
            result = await notion_request("getPublicSpaceData", data)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif name == "notion_get_user_content":
            data = {}
            result = await notion_request("loadUserContent", data)

            records = result.get("recordMap", {}).get("block", {})
            output = []
            for block_id, record in records.items():
                block = record.get("value", {})
                if block.get("type") == "page":
                    title = extract_text_from_block(block) or "Untitled"
                    output.append(f"- {title}\n  ID: {block_id}")

            return [TextContent(type="text", text=f"Your pages:\n\n" + "\n\n".join(output[:30]) if output else "No pages found")]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except httpx.HTTPStatusError as e:
        return [TextContent(type="text", text=f"HTTP error: {e.response.status_code} - {e.response.text[:500]}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {type(e).__name__}: {str(e)}")]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
