#!/usr/bin/env python3
"""
DingTalk Auto Collector

Input a colleague's name and automatically:
  1. Search for the DingTalk user and get userId
  2. Search for documents and knowledge base content they created/edited
  3. Pull multi-dimensional tables (if any)
  4. Message history (API does not support historical pull, automatically switches to browser approach)
  5. Output in a unified format, ready for the create-colleague analysis pipeline

DingTalk Limitations:
  DingTalk Open API does not provide historical message retrieval endpoints.
  The message history section automatically uses the Playwright browser approach for collection.

Prerequisites:
  pip3 install requests playwright
  playwright install chromium
  python3 dingtalk_auto_collector.py --setup

Usage:
  python3 dingtalk_auto_collector.py --name "Zhang San" --output-dir ./knowledge/zhangsan
  python3 dingtalk_auto_collector.py --name "Zhang San" --skip-messages   # skip message collection
  python3 dingtalk_auto_collector.py --name "Zhang San" --doc-limit 20
"""

from __future__ import annotations

import json
import sys
import time
import argparse
import platform
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

try:
    import requests
except ImportError:
    print("Error: please install dependencies first: pip3 install requests", file=sys.stderr)
    sys.exit(1)


CONFIG_PATH = Path.home() / ".colleague-skill" / "dingtalk_config.json"
API_BASE = "https://api.dingtalk.com"


# ─── Configuration ────────────────────────────────────────────────────────────

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print("Configuration not found. Please run: python3 dingtalk_auto_collector.py --setup", file=sys.stderr)
        sys.exit(1)
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False))


def setup_config() -> None:
    print("=== DingTalk Auto Collector Configuration ===\n")
    print("Please go to https://open-dev.dingtalk.com to create an enterprise internal app with the following permissions:\n")
    print("  Contacts:")
    print("    qyapi_get_member_detail     Query user details")
    print("    Contact.User.mobile         Read user phone number (optional)")
    print()
    print("  Messaging (optional, only for sending messages; historical messages require browser approach):")
    print("    qyapi_robot_sendmsg         Robot send message")
    print()
    print("  Documents:")
    print("    Doc.WorkSpace.READ          Read workspace")
    print("    Doc.File.READ               Read files")
    print()
    print("  Multi-dimensional tables:")
    print("    Bitable.Record.READ         Read records")
    print()

    app_key = input("AppKey (ding_xxx): ").strip()
    app_secret = input("AppSecret: ").strip()

    config = {"app_key": app_key, "app_secret": app_secret}
    save_config(config)
    print(f"\n✅ Configuration saved to {CONFIG_PATH}")
    print("\nNote: message history collection requires Playwright, please confirm it is installed:")
    print("  pip3 install playwright && playwright install chromium")


# ─── Token ───────────────────────────────────────────────────────────────────

_token_cache: dict = {}


def get_access_token(config: dict) -> str:
    """Get DingTalk access_token with caching"""
    now = time.time()
    if _token_cache.get("token") and _token_cache.get("expire", 0) > now + 60:
        return _token_cache["token"]

    resp = requests.post(
        f"{API_BASE}/v1.0/oauth2/accessToken",
        json={"appKey": config["app_key"], "appSecret": config["app_secret"]},
        timeout=10,
    )
    data = resp.json()

    if "accessToken" not in data:
        print(f"Failed to get token: {data}", file=sys.stderr)
        sys.exit(1)

    token = data["accessToken"]
    _token_cache["token"] = token
    _token_cache["expire"] = now + data.get("expireIn", 7200)
    return token


def api_get(path: str, params: dict, config: dict) -> dict:
    token = get_access_token(config)
    resp = requests.get(
        f"{API_BASE}{path}",
        params=params,
        headers={"x-acs-dingtalk-access-token": token},
        timeout=15,
    )
    return resp.json()


def api_post(path: str, body: dict, config: dict) -> dict:
    token = get_access_token(config)
    resp = requests.post(
        f"{API_BASE}{path}",
        json=body,
        headers={"x-acs-dingtalk-access-token": token},
        timeout=15,
    )
    return resp.json()


# ─── User Search ──────────────────────────────────────────────────────────────

def find_user(name: str, config: dict) -> Optional[dict]:
    """Search for a DingTalk user by name"""
    print(f"  Searching for user: {name}...", file=sys.stderr)

    data = api_post(
        "/v1.0/contact/users/search",
        {"searchText": name, "offset": 0, "size": 10},
        config,
    )

    users = data.get("list", []) or data.get("result", {}).get("list", [])

    if not users:
        # Fallback: search by department traversal
        print("  API search returned no results, trying to traverse contacts...", file=sys.stderr)
        users = search_users_by_dept(name, config)

    if not users:
        print(f"  User not found: {name}", file=sys.stderr)
        return None

    if len(users) == 1:
        u = users[0]
        print(f"  Found user: {u.get('name')} ({u.get('deptNameList', [''])[0] if isinstance(u.get('deptNameList'), list) else ''})", file=sys.stderr)
        return u

    print(f"\n  Found {len(users)} results, please choose:")
    for i, u in enumerate(users):
        dept = u.get("deptNameList", [""])
        dept_str = dept[0] if isinstance(dept, list) and dept else ""
        print(f"    [{i+1}] {u.get('name')}  {dept_str}  {u.get('unionId', '')}")

    choice = input("\n  Enter number (default 1): ").strip() or "1"
    try:
        return users[int(choice) - 1]
    except (ValueError, IndexError):
        return users[0]


def search_users_by_dept(name: str, config: dict, dept_id: int = 1, depth: int = 0) -> list:
    """Recursively traverse departments to search for users (depth limit: 3 levels)"""
    if depth > 3:
        return []

    results = []

    # Get department user list
    data = api_post(
        "/v1.0/contact/users/simplelist",
        {"deptId": dept_id, "cursor": 0, "size": 100},
        config,
    )
    users = data.get("list", [])
    for u in users:
        if name in u.get("name", ""):
            # Get detailed info
            detail = api_get(f"/v1.0/contact/users/{u.get('userId')}", {}, config)
            results.append(detail.get("result", u))

    # Get sub-departments
    sub_data = api_get(
        "/v1.0/contact/departments/listSubDepts",
        {"deptId": dept_id},
        config,
    )
    for sub in sub_data.get("result", []):
        results.extend(search_users_by_dept(name, config, sub.get("deptId"), depth + 1))

    return results


# ─── Document Collection ──────────────────────────────────────────────────────

def list_workspaces(config: dict) -> list:
    """Get all workspaces"""
    data = api_get("/v1.0/doc/workspaces", {"maxResults": 50}, config)
    return data.get("workspaceModels", []) or data.get("result", {}).get("workspaceModels", [])


def search_docs_by_user(user_id: str, name: str, doc_limit: int, config: dict) -> list:
    """Search for documents created by the user"""
    print(f"  Searching for {name}'s documents...", file=sys.stderr)

    # Method 1: Global search
    data = api_post(
        "/v1.0/doc/search",
        {
            "keyword": name,
            "size": doc_limit,
            "offset": 0,
        },
        config,
    )

    docs = []
    items = data.get("docList", []) or data.get("result", {}).get("docList", [])

    for item in items:
        creator_id = item.get("creatorId", "") or item.get("creator", {}).get("userId", "")
        # Filter: only keep documents created by the target user
        if user_id and creator_id and creator_id != user_id:
            continue
        docs.append({
            "title": item.get("title", "Untitled"),
            "docId": item.get("docId", ""),
            "spaceId": item.get("spaceId", ""),
            "type": item.get("docType", ""),
            "url": item.get("shareUrl", ""),
            "creator": item.get("creatorName", name),
        })

    if not docs:
        # Method 2: Traverse workspaces to find documents
        print("  Search returned no results, traversing workspaces...", file=sys.stderr)
        workspaces = list_workspaces(config)
        for ws in workspaces[:5]:  # Check at most 5 spaces
            ws_id = ws.get("spaceId") or ws.get("workspaceId")
            if not ws_id:
                continue
            files_data = api_get(
                f"/v1.0/doc/workspaces/{ws_id}/files",
                {"maxResults": 20, "orderBy": "modified_time", "order": "DESC"},
                config,
            )
            for f in files_data.get("files", []):
                creator_id = f.get("creatorId", "")
                if user_id and creator_id and creator_id != user_id:
                    continue
                docs.append({
                    "title": f.get("fileName", "Untitled"),
                    "docId": f.get("docId", ""),
                    "spaceId": ws_id,
                    "type": f.get("docType", ""),
                    "url": f.get("shareUrl", ""),
                    "creator": name,
                })

    print(f"  Found {len(docs)} documents", file=sys.stderr)
    return docs[:doc_limit]


def fetch_doc_content(doc_id: str, space_id: str, config: dict) -> str:
    """Pull the text content of a single document"""
    # Method 1: Get document content directly
    data = api_get(
        f"/v1.0/doc/workspaces/{space_id}/files/{doc_id}/content",
        {},
        config,
    )

    content = (
        data.get("content")
        or data.get("result", {}).get("content")
        or data.get("markdown")
        or data.get("result", {}).get("markdown")
        or ""
    )

    if content:
        return content

    # Method 2: Get download URL and download
    dl_data = api_get(
        f"/v1.0/doc/workspaces/{space_id}/files/{doc_id}/download",
        {},
        config,
    )
    dl_url = dl_data.get("downloadUrl") or dl_data.get("result", {}).get("downloadUrl")
    if dl_url:
        try:
            resp = requests.get(dl_url, timeout=15)
            return resp.text
        except Exception:
            pass

    return ""


def collect_docs(user: dict, doc_limit: int, config: dict) -> str:
    """Collect documents for the target user"""
    user_id = user.get("userId", "")
    name = user.get("name", "")

    docs = search_docs_by_user(user_id, name, doc_limit, config)
    if not docs:
        return f"# Document Content\n\nNo documents found for {name}\n"

    lines = [
        "# Document Content (DingTalk Auto-collected)",
        f"Target: {name}",
        f"Total: {len(docs)} documents",
        "",
    ]

    for doc in docs:
        title = doc.get("title", "Untitled")
        doc_id = doc.get("docId", "")
        space_id = doc.get("spaceId", "")
        url = doc.get("url", "")

        if not doc_id or not space_id:
            continue

        print(f"  Pulling document: {title}...", file=sys.stderr)
        content = fetch_doc_content(doc_id, space_id, config)

        if not content or len(content.strip()) < 20:
            print(f"    Content is empty, skipping", file=sys.stderr)
            continue

        lines += [
            "---",
            f"## \"{title}\"",
            f"URL: {url}",
            f"Creator: {doc.get('creator', '')}",
            "",
            content.strip(),
            "",
        ]

    return "\n".join(lines)


# ─── Multi-dimensional Tables ─────────────────────────────────────────────────

def search_bitables(user_id: str, name: str, config: dict) -> list:
    """Search for the target user's multi-dimensional tables"""
    print(f"  Searching for {name}'s multi-dimensional tables...", file=sys.stderr)

    data = api_post(
        "/v1.0/doc/search",
        {"keyword": name, "size": 20, "offset": 0, "docTypes": ["bitable"]},
        config,
    )

    tables = []
    for item in data.get("docList", []):
        if item.get("docType") != "bitable":
            continue
        creator_id = item.get("creatorId", "")
        if user_id and creator_id and creator_id != user_id:
            continue
        tables.append(item)

    print(f"  Found {len(tables)} multi-dimensional tables", file=sys.stderr)
    return tables


def fetch_bitable_content(base_id: str, config: dict) -> str:
    """Pull multi-dimensional table content"""
    # Get all sheets
    sheets_data = api_get(
        f"/v1.0/bitable/bases/{base_id}/sheets",
        {},
        config,
    )
    sheets = sheets_data.get("sheets", []) or sheets_data.get("result", {}).get("sheets", [])

    if not sheets:
        return "(Multi-dimensional table is empty or no permission)\n"

    lines = []
    for sheet in sheets:
        sheet_id = sheet.get("sheetId") or sheet.get("id")
        sheet_name = sheet.get("name", sheet_id)

        # Get fields
        fields_data = api_get(
            f"/v1.0/bitable/bases/{base_id}/sheets/{sheet_id}/fields",
            {"maxResults": 100},
            config,
        )
        fields = [f.get("name", "") for f in fields_data.get("fields", [])]

        # Get records
        records_data = api_get(
            f"/v1.0/bitable/bases/{base_id}/sheets/{sheet_id}/records",
            {"maxResults": 200},
            config,
        )
        records = records_data.get("records", []) or records_data.get("result", {}).get("records", [])

        lines.append(f"### Table: {sheet_name}")
        lines.append("")

        if fields:
            lines.append("| " + " | ".join(fields) + " |")
            lines.append("| " + " | ".join(["---"] * len(fields)) + " |")

        for rec in records:
            row_data = rec.get("fields", {})
            row = []
            for f in fields:
                val = row_data.get(f, "")
                if isinstance(val, list):
                    val = " ".join(
                        v.get("text", str(v)) if isinstance(v, dict) else str(v)
                        for v in val
                    )
                row.append(str(val).replace("|", "｜").replace("\n", " "))
            lines.append("| " + " | ".join(row) + " |")

        lines.append("")

    return "\n".join(lines)


def collect_bitables(user: dict, config: dict) -> str:
    """Collect multi-dimensional tables for the target user"""
    user_id = user.get("userId", "")
    name = user.get("name", "")

    tables = search_bitables(user_id, name, config)
    if not tables:
        return f"# Multi-dimensional Tables\n\nNo multi-dimensional tables found for {name}\n"

    lines = [
        "# Multi-dimensional Tables (DingTalk Auto-collected)",
        f"Target: {name}",
        f"Total: {len(tables)}",
        "",
    ]

    for t in tables:
        title = t.get("title", "Untitled")
        doc_id = t.get("docId", "")
        print(f"  Pulling multi-dimensional table: {title}...", file=sys.stderr)

        content = fetch_bitable_content(doc_id, config)
        lines += [
            "---",
            f"## \"{title}\"",
            "",
            content,
        ]

    return "\n".join(lines)


# ─── Message History (Browser approach) ──────────────────────────────────────

def get_default_chrome_profile() -> str:
    system = platform.system()
    if system == "Darwin":
        return str(Path.home() / "Library/Application Support/Google/Chrome/Default")
    elif system == "Linux":
        return str(Path.home() / ".config/google-chrome/Default")
    elif system == "Windows":
        import os
        return str(Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/User Data/Default")
    return str(Path.home() / ".config/google-chrome/Default")


def collect_messages_browser(
    name: str,
    msg_limit: int,
    chrome_profile: Optional[str],
    headless: bool,
) -> str:
    """Scrape DingTalk web message history via Playwright browser"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return (
            "# Message History\n\n"
            "⚠️  Playwright is not installed, cannot collect message history.\n"
            "Please run: pip3 install playwright && playwright install chromium\n"
        )

    import re

    profile = chrome_profile or get_default_chrome_profile()
    print(f"  Starting browser to scrape DingTalk messages ({'headless' if headless else 'with UI'})...", file=sys.stderr)

    messages = []

    with sync_playwright() as p:
        try:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=profile,
                headless=headless,
                args=["--disable-blink-features=AutomationControlled"],
                ignore_default_args=["--enable-automation"],
                viewport={"width": 1280, "height": 900},
            )
        except Exception as e:
            return f"# Message History\n\n⚠️  Cannot start browser: {e}\n"

        page = ctx.new_page()

        # Open DingTalk web version
        page.goto("https://im.dingtalk.com", wait_until="domcontentloaded", timeout=20000)
        time.sleep(3)

        # Check login status
        if "login" in page.url.lower() or page.query_selector(".login-wrap"):
            if headless:
                ctx.close()
                return (
                    "# Message History\n\n"
                    "⚠️  Not logged in detected. Please re-run with --show-browser to log in to DingTalk in the popup window.\n"
                )
            print("  Please log in to DingTalk in the browser, then press Enter to continue...", file=sys.stderr)
            input()

        # Search for the target contact's messages
        try:
            # Click the search box
            search_selectors = [
                '[placeholder*="Search"]',
                '.search-input',
                '[data-testid="search"]',
                '.im-search',
            ]
            for sel in search_selectors:
                el = page.query_selector(sel)
                if el:
                    el.click()
                    time.sleep(0.5)
                    page.keyboard.type(name)
                    time.sleep(2)
                    break

            # Click the first result
            result_selectors = [
                '.search-result-item',
                '.contact-item',
                '.result-item',
            ]
            for sel in result_selectors:
                result = page.query_selector(sel)
                if result:
                    result.click()
                    time.sleep(2)
                    break
        except Exception as e:
            print(f"  Auto navigation failed: {e}", file=sys.stderr)
            if not headless:
                print(f"  Please manually open the conversation with \"{name}\", then press Enter to continue...", file=sys.stderr)
                input()

        # Scroll up to load message history
        print("  Loading message history...", file=sys.stderr)
        for _ in range(15):
            page.keyboard.press("Control+Home")
            time.sleep(1)
            page.evaluate("window.scrollTo(0, 0)")
            time.sleep(0.8)

        time.sleep(2)

        # Extract messages
        raw_messages = page.evaluate(f"""
            () => {{
                const target = "{name}";
                const results = [];
                const selectors = [
                    '.message-item-content-container',
                    '.im-message-item',
                    '[data-message-id]',
                    '.msg-wrap',
                ];

                let items = [];
                for (const sel of selectors) {{
                    items = document.querySelectorAll(sel);
                    if (items.length > 0) break;
                }}

                items.forEach(item => {{
                    const senderEl = item.querySelector('.sender-name, .nick-name, .name');
                    const contentEl = item.querySelector(
                        '.message-text, .text-content, .msg-content, .im-richtext'
                    );
                    const timeEl = item.querySelector('.message-time, .time, .msg-time');

                    const sender = senderEl ? senderEl.innerText.trim() : '';
                    const content = contentEl ? contentEl.innerText.trim() : '';
                    const time = timeEl ? timeEl.innerText.trim() : '';

                    if (!content) return;
                    if (target && !sender.includes(target)) return;
                    if (['[Image]','[File]','[Emoji]','[Audio]'].includes(content)) return;

                    results.push({{ sender, content, time }});
                }});

                return results.slice(-{msg_limit});
            }}
        """)

        ctx.close()
        messages = raw_messages or []

    if not messages:
        return (
            "# Message History\n\n"
            f"⚠️  Could not automatically extract {name}'s messages.\n"
            "Possible reasons: DingTalk web DOM structure changed, or conversation not found.\n"
            "Suggestion: manually screenshot the chat history and upload it.\n"
        )

    long_msgs = [m for m in messages if len(m.get("content", "")) > 50]
    short_msgs = [m for m in messages if len(m.get("content", "")) <= 50]

    lines = [
        "# Message History (DingTalk Browser Collection)",
        f"Target: {name}",
        f"Total: {len(messages)} messages",
        "Note: DingTalk API does not support historical message retrieval; this content was collected via browser",
        "",
        "---",
        "",
        "## Long Messages (opinions/decisions/technical)",
        "",
    ]
    for m in long_msgs:
        lines.append(f"[{m.get('time', '')}] {m.get('content', '')}")
        lines.append("")

    lines += ["---", "", "## Everyday Messages (style reference)", ""]
    for m in short_msgs[:300]:
        lines.append(f"[{m.get('time', '')}] {m.get('content', '')}")

    return "\n".join(lines)


# ─── Main Flow ────────────────────────────────────────────────────────────────

def collect_all(
    name: str,
    output_dir: Path,
    msg_limit: int,
    doc_limit: int,
    skip_messages: bool,
    chrome_profile: Optional[str],
    headless: bool,
    config: dict,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    results = {}

    print(f"\n🔍 Starting collection (DingTalk): {name}\n", file=sys.stderr)

    # Step 1: Search for user
    user = find_user(name, config)
    if not user:
        print(f"❌ User not found: {name}", file=sys.stderr)
        sys.exit(1)

    print(f"  User ID: {user.get('userId', '')}  Department: {user.get('deptNameList', [''])[0] if isinstance(user.get('deptNameList'), list) and user.get('deptNameList') else ''}", file=sys.stderr)

    # Step 2: Documents
    print(f"\n📄 Collecting documents (limit: {doc_limit})...", file=sys.stderr)
    try:
        doc_content = collect_docs(user, doc_limit, config)
        doc_path = output_dir / "docs.txt"
        doc_path.write_text(doc_content, encoding="utf-8")
        results["docs"] = str(doc_path)
        print(f"  ✅ Documents → {doc_path}", file=sys.stderr)
    except Exception as e:
        print(f"  ⚠️  Document collection failed: {e}", file=sys.stderr)

    # Step 3: Multi-dimensional tables
    print(f"\n📊 Collecting multi-dimensional tables...", file=sys.stderr)
    try:
        bitable_content = collect_bitables(user, config)
        bt_path = output_dir / "bitables.txt"
        bt_path.write_text(bitable_content, encoding="utf-8")
        results["bitables"] = str(bt_path)
        print(f"  ✅ Multi-dimensional tables → {bt_path}", file=sys.stderr)
    except Exception as e:
        print(f"  ⚠️  Multi-dimensional table collection failed: {e}", file=sys.stderr)

    # Step 4: Message history (browser approach)
    if not skip_messages:
        print(f"\n📨 Collecting message history (browser approach, limit: {msg_limit})...", file=sys.stderr)
        print(f"  ℹ️  DingTalk API does not support historical message retrieval, automatically switching to browser approach", file=sys.stderr)
        try:
            msg_content = collect_messages_browser(name, msg_limit, chrome_profile, headless)
            msg_path = output_dir / "messages.txt"
            msg_path.write_text(msg_content, encoding="utf-8")
            results["messages"] = str(msg_path)
            print(f"  ✅ Message history → {msg_path}", file=sys.stderr)
        except Exception as e:
            print(f"  ⚠️  Message collection failed: {e}", file=sys.stderr)
    else:
        print(f"\n📨 Skipping message collection (--skip-messages)", file=sys.stderr)

    # Write summary
    summary = {
        "name": name,
        "user_id": user.get("userId", ""),
        "platform": "dingtalk",
        "department": user.get("deptNameList", []),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "files": results,
        "notes": "Message history collected via browser; DingTalk API does not support historical message retrieval",
    }
    (output_dir / "collection_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2)
    )

    print(f"\n✅ Collection complete → {output_dir}", file=sys.stderr)
    print(f"   Files: {', '.join(results.keys())}", file=sys.stderr)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="DingTalk Data Auto Collector")
    parser.add_argument("--setup", action="store_true", help="Initialize configuration")
    parser.add_argument("--name", help="Colleague name")
    parser.add_argument("--output-dir", default=None, help="Output directory")
    parser.add_argument("--msg-limit", type=int, default=500, help="Maximum messages to collect (default: 500)")
    parser.add_argument("--doc-limit", type=int, default=20, help="Maximum documents to collect (default: 20)")
    parser.add_argument("--skip-messages", action="store_true", help="Skip message history collection")
    parser.add_argument("--chrome-profile", default=None, help="Chrome Profile path")
    parser.add_argument("--show-browser", action="store_true", help="Show browser window (for debugging/first-time login)")

    args = parser.parse_args()

    if args.setup:
        setup_config()
        return

    if not args.name:
        parser.error("Please provide --name")

    config = load_config()
    output_dir = Path(args.output_dir) if args.output_dir else Path(f"./knowledge/{args.name}")

    collect_all(
        name=args.name,
        output_dir=output_dir,
        msg_limit=args.msg_limit,
        doc_limit=args.doc_limit,
        skip_messages=args.skip_messages,
        chrome_profile=args.chrome_profile,
        headless=not args.show_browser,
        config=config,
    )


if __name__ == "__main__":
    main()
