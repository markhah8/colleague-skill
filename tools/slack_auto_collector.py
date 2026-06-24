#!/usr/bin/env python3
"""
Slack Auto Collector

Input a colleague's Slack name/username and automatically:
  1. Search for the Slack user and get user_id
  2. Find channels shared with the Bot and pull messages sent by that user
  3. Output in a unified format, ready for the create-colleague analysis pipeline

Prerequisites:
  python3 slack_auto_collector.py --setup   # Configure Bot Token (one-time)

Usage:
  python3 slack_auto_collector.py --name "Zhang San" --output-dir ./knowledge/zhangsan
  python3 slack_auto_collector.py --name "john" --msg-limit 500 --channel-limit 30

Required Bot Token Scopes (OAuth & Permissions):
  channels:history      Read public channel messages
  channels:read         List public channels
  groups:history        Read private channel messages
  groups:read           List private channels
  im:history            Read DM messages (optional)
  im:read               List DMs (optional)
  mpim:history          Read group DM messages (optional)
  mpim:read             List group DMs (optional)
  users:read            Search user list

Notes:
  - Free Workspace only retains messages from the past 90 days
  - Requires a Workspace admin to install the Bot App
"""

from __future__ import annotations

import json
import sys
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

# ─── Dependency Check ─────────────────────────────────────────────────────────

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
except ImportError:
    print(
        "Error: please install slack_sdk first: pip3 install slack-sdk",
        file=sys.stderr,
    )
    sys.exit(1)

# ─── Constants ────────────────────────────────────────────────────────────────

CONFIG_PATH = Path.home() / ".colleague-skill" / "slack_config.json"

# Slack channel types (collection scope)
CHANNEL_TYPES = "public_channel,private_channel,mpim,im"

# Rate limit retry configuration
MAX_RETRIES = 5
RETRY_BASE_WAIT = 1.0     # Minimum wait seconds
RETRY_MAX_WAIT = 60.0     # Maximum wait seconds

# Collection defaults
DEFAULT_MSG_LIMIT = 1000
DEFAULT_CHANNEL_LIMIT = 50  # Maximum channels to check


# ─── Error Types ──────────────────────────────────────────────────────────────

class SlackCollectorError(Exception):
    """Expected errors during collection, exit directly"""


class SlackScopeError(SlackCollectorError):
    """Bot Token missing required scope permission"""


class SlackAuthError(SlackCollectorError):
    """Token invalid or expired"""


# ─── Configuration Management ─────────────────────────────────────────────────

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        print(
            "Configuration not found. Please run: python3 slack_auto_collector.py --setup",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        return json.loads(CONFIG_PATH.read_text())
    except json.JSONDecodeError:
        print(f"Configuration file corrupted, please re-run --setup: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)


def save_config(config: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False))


def setup_config() -> None:
    print("=== Slack Auto Collector Configuration ===\n")
    print("Step 1: Go to https://api.slack.com/apps to create a new App")
    print("        Choose 'From scratch' → enter App Name → select target Workspace\n")
    print("Step 2: Go to OAuth & Permissions, add to Bot Token Scopes:")
    print()
    print("  Messaging (required):")
    print("    channels:history     Read public channel message history")
    print("    groups:history       Read private channel message history")
    print("    mpim:history         Read group DM message history")
    print("    im:history           Read DM message history (optional)")
    print()
    print("  Channel info (required):")
    print("    channels:read        List public channels")
    print("    groups:read          List private channels")
    print("    mpim:read            List group DMs")
    print("    im:read              List DMs (optional)")
    print()
    print("  User info (required):")
    print("    users:read           Search user list")
    print()
    print("Step 3: Install to Workspace → copy Bot User OAuth Token (xoxb-...)")
    print("Step 4: Add Bot to target channels (/invite @your-bot-name)\n")

    token = input("Bot User OAuth Token (xoxb-...): ").strip()
    if not token.startswith("xoxb-"):
        print("Warning: Token format is incorrect, should start with xoxb-", file=sys.stderr)

    # Verify token is valid
    print("\nVerifying Token...", end=" ", flush=True)
    try:
        client = WebClient(token=token)
        resp = client.auth_test()
        workspace = resp.get("team", "Unknown")
        bot_name = resp.get("user", "Unknown")
        print(f"OK\n  Workspace: {workspace}, Bot: {bot_name}")
    except SlackApiError as e:
        err = e.response.get("error", str(e))
        print(f"Failed\n  Error: {err}", file=sys.stderr)
        if err == "invalid_auth":
            print("  Token is invalid, please regenerate", file=sys.stderr)
        sys.exit(1)

    config = {"bot_token": token}
    save_config(config)
    print(f"\n✅ Configuration saved to {CONFIG_PATH}")
    print("   Please confirm the Bot has been added to target channels, otherwise messages cannot be read")


# ─── Slack Client Wrapper (with rate limit retry) ─────────────────────────────

class RateLimitedClient:
    """Wraps slack_sdk WebClient, automatically handles 429 rate limiting"""

    def __init__(self, token: str) -> None:
        self._client = WebClient(token=token)

    def call(self, method: str, **kwargs) -> dict:
        """Call any Slack API, automatically wait and retry on ratelimited"""
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                fn = getattr(self._client, method)
                resp = fn(**kwargs)
                return resp.data
            except SlackApiError as e:
                error = e.response.get("error", "")

                # Rate limiting: read Retry-After header and wait
                if error == "ratelimited":
                    wait = float(
                        e.response.headers.get("Retry-After", RETRY_BASE_WAIT * attempt)
                    )
                    wait = min(wait, RETRY_MAX_WAIT)
                    print(
                        f"  [Rate limit] Waiting {wait:.0f}s (attempt {attempt}/{MAX_RETRIES})...",
                        file=sys.stderr,
                    )
                    time.sleep(wait)
                    continue

                # Permission error: raise directly, no retry
                if error == "missing_scope":
                    missing = e.response.get("needed", "unknown")
                    raise SlackScopeError(
                        f"Bot Token missing scope: {missing}\n"
                        f"  Please go to https://api.slack.com/apps → OAuth & Permissions → Bot Token Scopes to add it"
                    ) from e

                if error in ("invalid_auth", "token_revoked", "account_inactive"):
                    raise SlackAuthError(
                        f"Token authentication failed ({error}), please re-run --setup to configure a new Token"
                    ) from e

                # Channel no permission (Bot not joined): let caller handle
                if error in ("not_in_channel", "channel_not_found"):
                    raise

                # Other errors: print warning, return empty data
                print(f"  [API Warning] {method} returned error: {error}", file=sys.stderr)
                return {}

        # Retries exhausted
        print(f"  [Error] {method} still failing after multiple retries, skipping", file=sys.stderr)
        return {}

    def paginate(self, method: str, result_key: str, **kwargs) -> list:
        """Auto-paginate and return merged list of all results"""
        items: list = []
        cursor = None

        while True:
            params = dict(kwargs)
            if cursor:
                params["cursor"] = cursor

            data = self.call(method, **params)
            if not data:
                break

            items.extend(data.get(result_key, []))

            meta = data.get("response_metadata", {})
            cursor = meta.get("next_cursor")
            if not cursor:
                break

        return items


# ─── User Search ──────────────────────────────────────────────────────────────

def find_user(name: str, client: RateLimitedClient) -> Optional[dict]:
    """
    Search for a Slack user by name (real_name / display_name / name).
    Supports Chinese names, English usernames, and fuzzy matching.
    """
    print(f"  Searching for user: {name}...", file=sys.stderr)

    try:
        members = client.paginate("users_list", "members", limit=200)
    except SlackScopeError as e:
        print(f"  ❌ {e}", file=sys.stderr)
        sys.exit(1)

    # Filter out bots and deactivated accounts
    members = [
        m for m in members
        if not m.get("is_bot") and not m.get("deleted") and m.get("id") != "USLACKBOT"
    ]

    name_lower = name.lower()

    def score(member: dict) -> int:
        profile = member.get("profile", {})
        real_name = (profile.get("real_name") or "").lower()
        display_name = (profile.get("display_name") or "").lower()
        username = (member.get("name") or "").lower()

        if name_lower in (real_name, display_name, username):
            return 3  # Exact match
        if (
            name_lower in real_name
            or name_lower in display_name
            or name_lower in username
        ):
            return 2  # Contains match
        # Character-by-character matching for Chinese names
        if all(ch in real_name or ch in display_name for ch in name_lower if ch.strip()):
            return 1
        return 0

    scored = [(score(m), m) for m in members]
    candidates = [(s, m) for s, m in scored if s > 0]

    if not candidates:
        print(f"  User not found: {name}", file=sys.stderr)
        print(
            "  Tip: please check the name spelling, or try using the English username (e.g. john.doe)",
            file=sys.stderr,
        )
        return None

    candidates.sort(key=lambda x: -x[0])

    if len(candidates) == 1:
        _, user = candidates[0]
        _print_user(user)
        return user

    # Multiple candidates, let user choose
    print(f"\n  Found {len(candidates)} matches, please choose:")
    for i, (_, m) in enumerate(candidates[:10]):
        profile = m.get("profile", {})
        real_name = profile.get("real_name", "")
        display_name = profile.get("display_name", "")
        username = m.get("name", "")
        title = profile.get("title", "")
        print(f"    [{i+1}] {real_name} (@{display_name or username})  {title}")

    choice = input("\n  Enter number (default 1): ").strip() or "1"
    try:
        idx = int(choice) - 1
        _, user = candidates[idx]
    except (ValueError, IndexError):
        _, user = candidates[0]

    _print_user(user)
    return user


def _print_user(user: dict) -> None:
    profile = user.get("profile", {})
    real_name = profile.get("real_name", user.get("name", ""))
    display_name = profile.get("display_name", "")
    title = profile.get("title", "")
    print(
        f"  Found user: {real_name} (@{display_name})  {title}",
        file=sys.stderr,
    )


# ─── Channel Discovery ────────────────────────────────────────────────────────

def get_channels_with_user(
    user_id: str,
    channel_limit: int,
    client: RateLimitedClient,
) -> list:
    """
    Return all channels that both the Bot has joined and the target user is in.
    Strategy: first list all Bot channels, then check member lists one by one.
    """
    print("  Getting channel list...", file=sys.stderr)

    try:
        channels = client.paginate(
            "conversations_list",
            "channels",
            types=CHANNEL_TYPES,
            exclude_archived=True,
            limit=200,
        )
    except SlackScopeError as e:
        print(f"  ❌ {e}", file=sys.stderr)
        return []

    # Only keep channels the Bot is a member of
    bot_channels = [c for c in channels if c.get("is_member")]
    print(f"  Bot has joined {len(bot_channels)} channels, checking members...", file=sys.stderr)

    if len(bot_channels) > channel_limit:
        print(
            f"  Channel count exceeds limit {channel_limit}, only checking first {channel_limit}",
            file=sys.stderr,
        )
        bot_channels = bot_channels[:channel_limit]

    result = []
    for ch in bot_channels:
        ch_id = ch.get("id", "")
        ch_name = ch.get("name", ch_id)

        try:
            members = client.paginate(
                "conversations_members",
                "members",
                channel=ch_id,
                limit=200,
            )
        except SlackApiError as e:
            err = e.response.get("error", "")
            if err in ("not_in_channel", "channel_not_found"):
                continue
            print(f"    Skipping channel {ch_name} ({err})", file=sys.stderr)
            continue
        except SlackScopeError as e:
            print(f"  ❌ {e}", file=sys.stderr)
            continue

        if user_id in members:
            result.append(ch)
            print(f"    ✓ #{ch_name}", file=sys.stderr)

    return result


# ─── Message Collection ───────────────────────────────────────────────────────

def fetch_messages_from_channel(
    channel_id: str,
    channel_name: str,
    user_id: str,
    limit: int,
    client: RateLimitedClient,
) -> list:
    """
    Pull messages sent by the target user from the specified channel.
    Pages in reverse chronological order until limit is reached or no more data.
    """
    messages = []
    cursor = None
    pages_fetched = 0
    MAX_PAGES = 50  # Prevent infinite pagination

    while len(messages) < limit and pages_fetched < MAX_PAGES:
        params: dict = {"channel": channel_id, "limit": 200}
        if cursor:
            params["cursor"] = cursor

        try:
            data = client.call("conversations_history", **params)
        except SlackApiError as e:
            err = e.response.get("error", "")
            if err == "not_in_channel":
                print(
                    f"    Bot is not in channel #{channel_name}, skipping (please /invite @bot)",
                    file=sys.stderr,
                )
            else:
                print(f"    Failed to pull #{channel_name} ({err})", file=sys.stderr)
            break

        if not data:
            break

        pages_fetched += 1
        raw_msgs = data.get("messages", [])

        for msg in raw_msgs:
            # Only messages from the target user, not system messages
            if msg.get("user") != user_id:
                continue
            if msg.get("subtype"):  # join/leave/bot_message and other system types
                continue

            text = msg.get("text", "").strip()
            if not text:
                continue

            # Filter pure emoji or pure attachment messages
            if _is_noise(text):
                continue

            ts_raw = msg.get("ts", "")
            time_str = _format_ts(ts_raw)

            # Has thread_reply_count means it's a thread-starting message, higher weight
            is_thread_starter = bool(msg.get("reply_count", 0))

            messages.append(
                {
                    "content": text,
                    "time": time_str,
                    "channel": channel_name,
                    "is_thread_starter": is_thread_starter,
                }
            )

        meta = data.get("response_metadata", {})
        cursor = meta.get("next_cursor")
        if not cursor:
            break

    return messages[:limit]


def _is_noise(text: str) -> bool:
    """Determine if a message is meaningless (pure emoji, @mention, URL)"""
    import re
    # Remove Slack special format, check if nearly empty
    cleaned = re.sub(r"<[^>]+>", "", text).strip()
    cleaned = re.sub(r":[a-z_]+:", "", cleaned).strip()
    return len(cleaned) < 2


def _format_ts(ts: str) -> str:
    """Convert Slack timestamp (Unix float string) to readable time"""
    try:
        return datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M")
    except (ValueError, OSError):
        return ts


# ─── Main Collection Flow ─────────────────────────────────────────────────────

def collect_messages(
    user: dict,
    channels: list,
    msg_limit: int,
    client: RateLimitedClient,
) -> str:
    """Collect target user messages from all channels, return formatted text"""
    user_id = user["id"]
    name = user.get("profile", {}).get("real_name") or user.get("name", user_id)

    if not channels:
        return (
            f"# Message History\n\n"
            f"No shared channels found with {name}.\n"
            f"Please confirm the Bot has been added to relevant channels (/invite @bot)\n"
        )

    all_messages: list = []
    per_channel_limit = max(100, msg_limit // len(channels))

    for ch in channels:
        ch_id = ch.get("id", "")
        ch_name = ch.get("name", ch_id)
        print(f"  Pulling messages from #{ch_name}...", file=sys.stderr)

        msgs = fetch_messages_from_channel(
            ch_id, ch_name, user_id, per_channel_limit, client
        )
        all_messages.extend(msgs)
        print(f"    Retrieved {len(msgs)} messages", file=sys.stderr)

    # Categorize by weight
    thread_msgs = [m for m in all_messages if m["is_thread_starter"]]
    long_msgs = [
        m for m in all_messages
        if not m["is_thread_starter"] and len(m["content"]) > 50
    ]
    short_msgs = [
        m for m in all_messages
        if not m["is_thread_starter"] and len(m["content"]) <= 50
    ]

    channel_names = ", ".join(f"#{c.get('name', c.get('id', ''))}" for c in channels)

    lines = [
        "# Slack Message History (Auto-collected)",
        f"Target: {name}",
        f"Source channels: {channel_names}",
        f"Total {len(all_messages)} messages",
        f"  Thread-starting messages: {len(thread_msgs)}",
        f"  Long messages (>50 chars): {len(long_msgs)}",
        f"  Short messages: {len(short_msgs)}",
        "",
        "---",
        "",
        "## Thread-starting Messages (highest weight: opinions/decisions/technical sharing)",
        "",
    ]
    for m in thread_msgs:
        lines.append(f"[{m['time']}][#{m['channel']}] {m['content']}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Long Messages (opinions/proposals/discussions)",
        "",
    ]
    for m in long_msgs:
        lines.append(f"[{m['time']}][#{m['channel']}] {m['content']}")
        lines.append("")

    lines += ["---", "", "## Everyday Messages (style reference)", ""]
    for m in short_msgs[:300]:
        lines.append(f"[{m['time']}] {m['content']}")

    return "\n".join(lines)


def collect_all(
    name: str,
    output_dir: Path,
    msg_limit: int,
    channel_limit: int,
    config: dict,
) -> dict:
    """Collect all Slack data for a colleague, output to output_dir"""
    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict = {}

    print(f"\n🔍 Starting collection: {name}\n", file=sys.stderr)

    # Initialize Client
    try:
        client = RateLimitedClient(config["bot_token"])
        # Quick verify token validity
        auth_data = client.call("auth_test")
        if not auth_data:
            raise SlackAuthError("auth_test no response, please check Token")
        print(
            f"  Workspace: {auth_data.get('team')}, Bot: {auth_data.get('user')}",
            file=sys.stderr,
        )
    except SlackAuthError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    # Step 1: Search for user
    user = find_user(name, client)
    if not user:
        print(f"❌ User {name} not found, please check the name/username is correct", file=sys.stderr)
        sys.exit(1)

    user_id = user["id"]
    profile = user.get("profile", {})
    real_name = profile.get("real_name") or user.get("name", user_id)

    # Step 2: Find shared channels
    print(f"\n📡 Finding channels shared with {real_name} (limit: {channel_limit})...", file=sys.stderr)
    channels = get_channels_with_user(user_id, channel_limit, client)
    print(f"  Shared channels: {len(channels)}", file=sys.stderr)

    # Step 3: Collect messages
    print(f"\n📨 Collecting message history (limit: {msg_limit})...", file=sys.stderr)
    try:
        msg_content = collect_messages(user, channels, msg_limit, client)
        msg_path = output_dir / "messages.txt"
        msg_path.write_text(msg_content, encoding="utf-8")
        results["messages"] = str(msg_path)
        print(f"  ✅ Message history → {msg_path}", file=sys.stderr)
    except SlackCollectorError as e:
        print(f"  ❌ {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"  ⚠️  Message collection failed: {e}", file=sys.stderr)

    # Write summary
    summary = {
        "name": real_name,
        "slack_user_id": user_id,
        "display_name": profile.get("display_name", ""),
        "title": profile.get("title", ""),
        "channels": [
            {"id": c.get("id"), "name": c.get("name")} for c in channels
        ],
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "files": results,
        "note": "Free Workspace only retains messages from the past 90 days",
    }
    summary_path = output_dir / "collection_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"  ✅ Collection summary → {summary_path}", file=sys.stderr)

    print(f"\n✅ Collection complete, output directory: {output_dir}", file=sys.stderr)
    return results


# ─── CLI Entry ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Slack Data Auto Collector",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # First-time configuration
  python3 slack_auto_collector.py --setup

  # Collect colleague data
  python3 slack_auto_collector.py --name "Zhang San"
  python3 slack_auto_collector.py --name "john.doe" --output-dir ./knowledge/john --msg-limit 500
        """,
    )
    parser.add_argument("--setup", action="store_true", help="Initialize configuration (Bot Token)")
    parser.add_argument("--name", help="Colleague name or Slack username")
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: ./knowledge/{name})",
    )
    parser.add_argument(
        "--msg-limit",
        type=int,
        default=DEFAULT_MSG_LIMIT,
        help=f"Maximum messages to collect (default: {DEFAULT_MSG_LIMIT})",
    )
    parser.add_argument(
        "--channel-limit",
        type=int,
        default=DEFAULT_CHANNEL_LIMIT,
        help=f"Maximum channels to check (default: {DEFAULT_CHANNEL_LIMIT})",
    )

    args = parser.parse_args()

    if args.setup:
        setup_config()
        return

    if not args.name:
        parser.print_help()
        parser.error("Please provide --name argument")

    config = load_config()
    output_dir = (
        Path(args.output_dir)
        if args.output_dir
        else Path(f"./knowledge/{args.name}")
    )

    try:
        collect_all(
            name=args.name,
            output_dir=output_dir,
            msg_limit=args.msg_limit,
            channel_limit=args.channel_limit,
            config=config,
        )
    except SlackCollectorError as e:
        print(f"\n❌ Collection failed: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nCancelled", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
