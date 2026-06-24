#!/usr/bin/env python3
"""
Feishu MCP Client Wrapper (cso1z/Feishu-MCP approach)

Read documents, wikis, and message history via Feishu MCP Server.
Suitable for: company-authorized documents, content with App token permissions.

Prerequisites:
  1. Install Feishu MCP: npm install -g feishu-mcp
  2. Configure App ID and App Secret (create an enterprise self-built app in Feishu Open Platform)
  3. Grant the app the necessary permissions (see REQUIRED_PERMISSIONS below)

Permission list (Feishu Open Platform → Permission Management → Grant):
  - docs:doc:readonly          Read documents
  - wiki:wiki:readonly         Read knowledge base
  - im:message:readonly        Read messages
  - bitable:app:readonly       Read multi-dimensional tables
  - sheets:spreadsheet:readonly Read spreadsheets

Usage:
  # Configure token (one-time)
  python3 feishu_mcp_client.py --setup

  # Read a document
  python3 feishu_mcp_client.py --url "https://xxx.feishu.cn/wiki/xxx" --output out.txt

  # Read message history
  python3 feishu_mcp_client.py --chat-id "oc_xxx" --target "Zhang San" --output out.txt

  # List all documents in a space
  python3 feishu_mcp_client.py --list-wiki --space-id "xxx"
"""

from __future__ import annotations

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path
from typing import Optional


CONFIG_PATH = Path.home() / ".colleague-skill" / "feishu_config.json"


# ─── Configuration Management ─────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))
    print(f"Configuration saved to {CONFIG_PATH}")


def setup_config() -> None:
    print("=== Feishu MCP Configuration ===")
    print("Please go to Feishu Open Platform (open.feishu.cn) to create an enterprise self-built app and get the following:\n")

    app_id = input("App ID (cli_xxx): ").strip()
    app_secret = input("App Secret: ").strip()

    print("\nChoose configuration mode:")
    print("  [1] App Token (app permissions, requires granting corresponding permissions in Feishu backend)")
    print("  [2] User Token (personal permissions, can access all content you have permission to view, requires periodic refresh)")
    mode = input("Choose [1/2], default 1: ").strip() or "1"

    config = {
        "app_id": app_id,
        "app_secret": app_secret,
        "mode": "app" if mode == "1" else "user",
    }

    if mode == "2":
        print("\nGet User Token: Feishu Open Platform → OAuth 2.0 → Get user_access_token")
        user_token = input("User Access Token (u-xxx): ").strip()
        config["user_token"] = user_token
        print("Note: User Token is valid for ~2 hours and needs to be reconfigured after expiration")

    save_config(config)
    print("\n✅ Configuration complete!")


# ─── MCP Call Wrapper ─────────────────────────────────────────────────────────

def call_mcp(tool: str, params: dict, config: dict) -> dict:
    """
    Call feishu-mcp tools via npx.
    feishu-mcp supports stdio mode with direct JSON communication.
    """
    env = os.environ.copy()
    env["FEISHU_APP_ID"] = config.get("app_id", "")
    env["FEISHU_APP_SECRET"] = config.get("app_secret", "")

    if config.get("mode") == "user" and config.get("user_token"):
        env["FEISHU_USER_ACCESS_TOKEN"] = config["user_token"]

    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool,
            "arguments": params,
        },
        "id": 1,
    })

    try:
        result = subprocess.run(
            ["npx", "-y", "feishu-mcp", "--stdio"],
            input=payload,
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"MCP call failed: {result.stderr}")
        return json.loads(result.stdout)
    except FileNotFoundError:
        print("Error: npx not found, please install Node.js first", file=sys.stderr)
        print("Install Feishu MCP: npm install -g feishu-mcp", file=sys.stderr)
        sys.exit(1)


def extract_doc_token(url: str) -> tuple[str, str]:
    """Extract document token and type from a Feishu URL"""
    import re
    patterns = [
        (r"/wiki/([A-Za-z0-9]+)", "wiki"),
        (r"/docx/([A-Za-z0-9]+)", "docx"),
        (r"/docs/([A-Za-z0-9]+)", "doc"),
        (r"/sheets/([A-Za-z0-9]+)", "sheet"),
        (r"/base/([A-Za-z0-9]+)", "base"),
    ]
    for pattern, doc_type in patterns:
        m = re.search(pattern, url)
        if m:
            return m.group(1), doc_type
    raise ValueError(f"Cannot parse document token from URL: {url}")


# ─── Feature Functions ────────────────────────────────────────────────────────

def fetch_doc_via_mcp(url: str, config: dict) -> str:
    """Read a Feishu document or Wiki via MCP"""
    token, doc_type = extract_doc_token(url)

    if doc_type == "wiki":
        result = call_mcp("get_wiki_node", {"token": token}, config)
    elif doc_type in ("docx", "doc"):
        result = call_mcp("get_doc_content", {"doc_token": token}, config)
    elif doc_type == "sheet":
        result = call_mcp("get_spreadsheet_content", {"spreadsheet_token": token}, config)
    else:
        raise ValueError(f"Unsupported document type: {doc_type}")

    # Extract content from MCP response
    if "result" in result:
        content = result["result"]
        if isinstance(content, list):
            # MCP tool result format
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    return item.get("text", "")
        elif isinstance(content, str):
            return content
    elif "error" in result:
        raise RuntimeError(f"MCP returned error: {result['error']}")

    return json.dumps(result, ensure_ascii=False, indent=2)


def fetch_messages_via_mcp(
    chat_id: str,
    target_name: str,
    limit: int,
    config: dict,
) -> str:
    """Read group chat message history via MCP"""
    result = call_mcp(
        "get_chat_messages",
        {
            "chat_id": chat_id,
            "page_size": min(limit, 50),  # Feishu API max 50 per request
        },
        config,
    )

    messages = []
    raw = result.get("result", [])
    if isinstance(raw, list):
        messages = raw
    elif isinstance(raw, str):
        try:
            messages = json.loads(raw)
        except Exception:
            return raw

    # Filter by target person
    if target_name:
        messages = [
            m for m in messages
            if target_name in str(m.get("sender", {}).get("name", ""))
        ]

    # Categorized output
    long_msgs = [m for m in messages if len(str(m.get("content", ""))) > 50]
    short_msgs = [m for m in messages if len(str(m.get("content", ""))) <= 50]

    lines = [
        "# Feishu Message History (MCP approach)",
        f"Group chat ID: {chat_id}",
        f"Target: {target_name or 'All'}",
        f"Total {len(messages)} messages",
        "",
        "---",
        "",
        "## Long Messages",
        "",
    ]
    for m in long_msgs:
        sender = m.get("sender", {}).get("name", "")
        content = m.get("content", "")
        ts = m.get("create_time", "")
        lines.append(f"[{ts}] {sender}: {content}")
        lines.append("")

    lines += ["---", "", "## Everyday Messages", ""]
    for m in short_msgs[:200]:
        sender = m.get("sender", {}).get("name", "")
        content = m.get("content", "")
        lines.append(f"{sender}: {content}")

    return "\n".join(lines)


def list_wiki_docs(space_id: str, config: dict) -> str:
    """List all documents under a knowledge base space"""
    result = call_mcp("list_wiki_nodes", {"space_id": space_id}, config)
    raw = result.get("result", "")
    if isinstance(raw, str):
        return raw
    return json.dumps(raw, ensure_ascii=False, indent=2)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Feishu MCP Client")
    parser.add_argument("--setup", action="store_true", help="Initialize configuration (App ID / Secret)")
    parser.add_argument("--url", help="Feishu document/Wiki/spreadsheet link")
    parser.add_argument("--chat-id", help="Group chat ID (oc_xxx format)")
    parser.add_argument("--target", help="Target person's name")
    parser.add_argument("--limit", type=int, default=500, help="Maximum messages to retrieve")
    parser.add_argument("--list-wiki", action="store_true", help="List knowledge base documents")
    parser.add_argument("--space-id", help="Knowledge base Space ID")
    parser.add_argument("--output", default=None, help="Output file path")

    args = parser.parse_args()

    if args.setup:
        setup_config()
        return

    config = load_config()
    if not config:
        print("Error: not configured yet. Please run: python3 feishu_mcp_client.py --setup", file=sys.stderr)
        sys.exit(1)

    content = ""

    if args.url:
        print(f"Reading via MCP: {args.url}", file=sys.stderr)
        content = fetch_doc_via_mcp(args.url, config)

    elif args.chat_id:
        print(f"Reading messages via MCP: {args.chat_id}", file=sys.stderr)
        content = fetch_messages_via_mcp(
            args.chat_id,
            args.target or "",
            args.limit,
            config,
        )

    elif args.list_wiki:
        if not args.space_id:
            print("Error: --list-wiki requires --space-id", file=sys.stderr)
            sys.exit(1)
        content = list_wiki_docs(args.space_id, config)

    else:
        parser.print_help()
        return

    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
        print(f"✅ Saved to {args.output}", file=sys.stderr)
    else:
        print(content)


if __name__ == "__main__":
    main()
