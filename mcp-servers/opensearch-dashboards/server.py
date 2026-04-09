#!/usr/bin/env python3
"""OpenSearch MCP Server via Dashboards proxy (SSO auth via cookies)"""

import json
import os
import sys
import urllib.request
import urllib.parse
import ssl

def send_response(id, result):
    msg = {"jsonrpc": "2.0", "id": id, "result": result}
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()

def send_error(id, code, message):
    msg = {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()

class OpenSearchDashboardsClient:
    def __init__(self):
        self.base_url = os.environ.get("OPENSEARCH_DASHBOARDS_URL", "https://logs.example.com")
        self.cookies = self._load_cookies()
        self.ctx = ssl.create_default_context()
        if os.environ.get("OPENSEARCH_SSL_VERIFY", "true").lower() == "false":
            self.ctx.check_hostname = False
            self.ctx.verify_mode = ssl.CERT_NONE

    def _load_cookies(self):
        cookie_file = os.environ.get("OPENSEARCH_COOKIE_FILE", os.path.expanduser("~/.claude/opensearch-cookies.json"))
        try:
            with open(cookie_file) as f:
                data = json.load(f)
                return "; ".join(f"{c['name']}={c['value']}" for c in data.get("cookies", []))
        except:
            c1 = os.environ.get("OPENSEARCH_COOKIE_AUTH", "")
            c2 = os.environ.get("OPENSEARCH_COOKIE_OIDC", "")
            if c1 or c2:
                parts = []
                if c1: parts.append(f"security_authentication={c1}")
                if c2: parts.append(f"security_authentication_oidc1={c2}")
                return "; ".join(parts)
            return ""

    def _request(self, path, method="GET", body=None):
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Cookie", self.cookies)
        req.add_header("osd-xsrf", "true")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, context=self.ctx, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            return {"error": e.code, "message": e.read().decode()[:500]}
        except Exception as e:
            return {"error": -1, "message": str(e)}

    def search(self, index, query, size=10):
        body = {"params": {"index": index, "body": {"size": size, "query": query}}}
        return self._request("/internal/search/opensearch-with-long-numerals", "POST", body)

    def list_indices(self):
        body = {"params": {"index": "*", "body": {"size": 0, "aggs": {"indices": {"terms": {"field": "_index", "size": 1000}}}}}}
        resp = self._request("/internal/search/opensearch-with-long-numerals", "POST", body)
        if "rawResponse" in resp:
            buckets = resp.get("rawResponse", {}).get("aggregations", {}).get("indices", {}).get("buckets", [])
            return {"indices": [{"name": b["key"], "doc_count": b["doc_count"]} for b in buckets]}
        return resp

    def count(self, index, query=None):
        body = {"params": {"index": index, "body": {"size": 0, "query": query or {"match_all": {}}}}}
        resp = self._request("/internal/search/opensearch-with-long-numerals", "POST", body)
        if "rawResponse" in resp:
            return {"count": resp["rawResponse"]["hits"]["total"]}
        return resp

    def cluster_health(self):
        return self._request("/api/status")

client = OpenSearchDashboardsClient()

TOOLS = [
    {"name": "opensearch_search", "description": "Search OpenSearch index with query DSL",
     "inputSchema": {"type": "object", "properties": {
         "index": {"type": "string", "description": "Index pattern (e.g., logs-* or *)"},
         "query": {"type": "object", "description": "OpenSearch query DSL object"},
         "size": {"type": "integer", "description": "Max results (default 10)", "default": 10}
     }, "required": ["index", "query"]}},
    {"name": "opensearch_list_indices", "description": "List all indices with doc counts",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "opensearch_count", "description": "Count documents matching a query",
     "inputSchema": {"type": "object", "properties": {
         "index": {"type": "string", "description": "Index pattern"},
         "query": {"type": "object", "description": "Optional query DSL"}
     }, "required": ["index"]}},
    {"name": "opensearch_health", "description": "Get cluster/dashboards health status",
     "inputSchema": {"type": "object", "properties": {}}}
]

def handle_request(req):
    method = req.get("method")
    id = req.get("id")
    params = req.get("params", {})

    if method == "initialize":
        send_response(id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "opensearch-dashboards", "version": "1.0.0"}
        })
    elif method == "tools/list":
        send_response(id, {"tools": TOOLS})
    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        try:
            if name == "opensearch_search":
                result = client.search(args["index"], args["query"], args.get("size", 10))
            elif name == "opensearch_list_indices":
                result = client.list_indices()
            elif name == "opensearch_count":
                result = client.count(args["index"], args.get("query"))
            elif name == "opensearch_health":
                result = client.cluster_health()
            else:
                send_error(id, -32601, f"Unknown tool: {name}")
                return
            send_response(id, {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]})
        except Exception as e:
            send_response(id, {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True})
    elif method == "notifications/initialized":
        pass
    else:
        send_error(id, -32601, f"Method not found: {method}")

def main():
    for line in sys.stdin:
        try:
            req = json.loads(line.strip())
            handle_request(req)
        except json.JSONDecodeError:
            pass
        except Exception as e:
            sys.stderr.write(f"Error: {e}\n")

if __name__ == "__main__":
    main()
