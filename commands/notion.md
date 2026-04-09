---
description: Interact with Notion's internal API using cookie authentication
arguments:
  - name: action
    description: "Action: search, get-page, get-block, query-collection, create-page"
    required: true
  - name: query
    description: "Search query or page/block ID"
    required: false
  - name: space
    description: "Space ID (defaults to your workspace)"
    required: false
---

# Notion Internal API Skill

You are an expert at interacting with Notion's internal API using cookie-based authentication.

## Configuration

Store cookies in `~/.notion-cookies` file (one-time setup):

```bash
# Extract token_v2 and other essential cookies from browser
export NOTION_COOKIES="token_v2=v03%3A...; notion_user_id=<YOUR_USER_ID>"
```

## API Client

```python
import json
import urllib.request
import os

class NotionInternalClient:
    def __init__(self):
        self.base_url = "https://www.notion.so/api/v3"
        self.user_id = "<YOUR_USER_ID>"
        self.space_id = "<YOUR_SPACE_ID>"

        # Read cookies from env or file
        self.cookies = os.environ.get("NOTION_COOKIES", "")
        if not self.cookies:
            cookie_file = os.path.expanduser("~/.notion-cookies")
            if os.path.exists(cookie_file):
                with open(cookie_file) as f:
                    self.cookies = f.read().strip()

    def _request(self, endpoint, data=None):
        url = f"{self.base_url}/{endpoint}"
        req = urllib.request.Request(url, method="POST")

        req.add_header("Content-Type", "application/json")
        req.add_header("Cookie", self.cookies)
        req.add_header("x-notion-active-user-header", self.user_id)
        req.add_header("x-notion-space-id", self.space_id)
        req.add_header("notion-client-version", "23.13.20260119.1242")
        req.add_header("User-Agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

        if data:
            req.data = json.dumps(data).encode()
        else:
            req.data = b"{}"

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            print(f"Error {e.code}: {error_body}")
            return None

    def search(self, query, limit=20):
        """Search pages in workspace"""
        data = {
            "type": "BlocksInSpace",
            "query": query,
            "spaceId": self.space_id,
            "limit": limit,
            "filters": {
                "isDeletedOnly": False,
                "excludeTemplates": False,
                "isNavigableOnly": False,
                "requireEditPermissions": False,
                "ancestors": [],
                "createdBy": [],
                "editedBy": [],
                "lastEditedTime": {},
                "createdTime": {}
            },
            "sort": {"field": "relevance"},
            "source": "quick_find_input_change"
        }
        return self._request("search", data)

    def get_page(self, page_id):
        """Load a page with all its content"""
        # Clean page ID format
        page_id = page_id.replace("-", "")
        data = {
            "page": {"id": page_id},
            "limit": 100,
            "cursor": {"stack": []},
            "chunkNumber": 0,
            "verticalColumns": False
        }
        return self._request("loadPageChunk", data)

    def get_block(self, block_id):
        """Get a specific block"""
        block_id = block_id.replace("-", "")
        data = {"blockIds": [block_id]}
        return self._request("syncRecordValues", data)

    def get_collection(self, collection_id, view_id):
        """Query a database/collection"""
        data = {
            "collectionId": collection_id.replace("-", ""),
            "collectionViewId": view_id.replace("-", ""),
            "query": {},
            "loader": {
                "type": "table",
                "limit": 100,
                "searchQuery": "",
                "userTimeZone": "UTC",
                "loadContentCover": True
            }
        }
        return self._request("queryCollection", data)

    def get_user_info(self):
        """Get current user info"""
        return self._request("getEmailDomainSettings", {})

    def get_spaces(self):
        """Get all accessible spaces"""
        return self._request("getSpaces", {})

client = NotionInternalClient()
```

## Actions

### 1. Search (`--action search --query "term"`)

```python
results = client.search("$query")
if results and "results" in results:
    for item in results["results"]:
        block_id = item.get("id", "")
        highlight = item.get("highlight", {})
        title = highlight.get("text", "Untitled")

        # Format ID with dashes for URL
        formatted_id = f"{block_id[:8]}-{block_id[8:12]}-{block_id[12:16]}-{block_id[16:20]}-{block_id[20:]}"

        print(f"📄 {title}")
        print(f"   ID: {formatted_id}")
        print(f"   URL: https://www.notion.so/{formatted_id.replace('-', '')}")
        print()
```

### 2. Get Page (`--action get-page --query "page-id"`)

```python
result = client.get_page("$query")
if result and "recordMap" in result:
    blocks = result["recordMap"].get("block", {})

    for block_id, block_data in blocks.items():
        block = block_data.get("value", {})
        block_type = block.get("type", "")
        properties = block.get("properties", {})

        if block_type == "page":
            title = properties.get("title", [[""]])[0][0]
            print(f"# {title}")
            print(f"ID: {block_id}")
            print()
        elif block_type == "text":
            text = properties.get("title", [[""]])[0][0] if properties.get("title") else ""
            if text:
                print(text)
        elif block_type == "header":
            text = properties.get("title", [[""]])[0][0] if properties.get("title") else ""
            print(f"# {text}")
        elif block_type == "sub_header":
            text = properties.get("title", [[""]])[0][0] if properties.get("title") else ""
            print(f"## {text}")
        elif block_type == "sub_sub_header":
            text = properties.get("title", [[""]])[0][0] if properties.get("title") else ""
            print(f"### {text}")
        elif block_type == "bulleted_list":
            text = properties.get("title", [[""]])[0][0] if properties.get("title") else ""
            print(f"• {text}")
        elif block_type == "numbered_list":
            text = properties.get("title", [[""]])[0][0] if properties.get("title") else ""
            print(f"1. {text}")
        elif block_type == "to_do":
            text = properties.get("title", [[""]])[0][0] if properties.get("title") else ""
            checked = properties.get("checked", [["No"]])[0][0] == "Yes"
            mark = "✓" if checked else "○"
            print(f"{mark} {text}")
        elif block_type == "code":
            text = properties.get("title", [[""]])[0][0] if properties.get("title") else ""
            lang = properties.get("language", [["plain text"]])[0][0]
            print(f"```{lang}")
            print(text)
            print("```")
        elif block_type == "divider":
            print("---")
        elif block_type == "callout":
            text = properties.get("title", [[""]])[0][0] if properties.get("title") else ""
            icon = block.get("format", {}).get("page_icon", "💡")
            print(f"{icon} {text}")

        print()
```

### 3. Get Spaces (`--action get-spaces`)

```python
result = client.get_spaces()
if result:
    for user_id, user_data in result.items():
        spaces = user_data.get("space", {})
        for space_id, space_info in spaces.items():
            space = space_info.get("value", {})
            name = space.get("name", "Unknown")
            print(f"🏢 {name}")
            print(f"   ID: {space_id}")
            print()
```

## Cookie Setup

1. Open Notion in Chrome
2. Open DevTools → Network tab
3. Make any request (refresh page)
4. Find any `api/v3` request
5. Copy the Cookie header value
6. Save to `~/.notion-cookies`:

```bash
echo 'token_v2=v03%3A...; notion_user_id=...' > ~/.notion-cookies
```

Or extract just the essential cookies:
- `token_v2` (required - main auth token)
- `notion_user_id` (required)
- `notion_browser_id` (optional)

## Important IDs

| Item | ID |
|------|-----|
| Workspace | `<YOUR_SPACE_ID>` |
| Your User ID | `<YOUR_USER_ID>` |

## Execution Instructions

1. Parse user arguments: $ARGUMENTS
2. Load cookies from `~/.notion-cookies` or `NOTION_COOKIES` env var
3. Execute the appropriate action
4. Parse the nested Notion response format
5. Format output readably

## Example Invocations

`/notion --action search --query "meeting notes"`
→ Search workspace for "meeting notes"

`/notion --action get-page --query "1ab836a12d9080788779e18a22a1c1ed"`
→ Get content of a specific page

`/notion --action get-spaces`
→ List all accessible workspaces

## Response Structure Notes

Notion's internal API returns nested `recordMap` structures:

```json
{
  "recordMap": {
    "block": {
      "block-id-here": {
        "value": {
          "type": "page",
          "properties": {"title": [["Page Title"]]},
          "content": ["child-block-id-1", "child-block-id-2"]
        }
      }
    },
    "collection": {...},
    "collection_view": {...}
  }
}
```

Text properties use the format: `[["text", [["formatting"]]]]`
