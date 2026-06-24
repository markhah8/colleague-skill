#!/usr/bin/env python3
"""
Feishu Message Export JSON Parser

Supported export formats:
1. Feishu official export (group chat records): typically a JSON array where each message
   contains sender, content, timestamp
2. Manually organized TXT format (one line per message: time sender: content)

Usage:
    python feishu_parser.py --file messages.json --target "Zhang San" --output output.txt
    python feishu_parser.py --file messages.txt --target "Zhang San" --output output.txt
"""

import json
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime


def parse_feishu_json(file_path: str, target_name: str) -> list[dict]:
    """Parse messages from Feishu's official JSON export format"""
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = []

    # Compatible with multiple JSON structures
    if isinstance(data, list):
        raw_messages = data
    elif isinstance(data, dict):
        # May be under data.messages, data.records, etc.
        raw_messages = (
            data.get("messages")
            or data.get("records")
            or data.get("data")
            or []
        )
    else:
        return []

    for msg in raw_messages:
        sender = (
            msg.get("sender_name")
            or msg.get("sender")
            or msg.get("from")
            or msg.get("user_name")
            or ""
        )
        content = (
            msg.get("content")
            or msg.get("text")
            or msg.get("message")
            or msg.get("body")
            or ""
        )
        timestamp = (
            msg.get("timestamp")
            or msg.get("create_time")
            or msg.get("time")
            or ""
        )

        # content may be a nested structure
        if isinstance(content, dict):
            content = content.get("text") or content.get("content") or str(content)
        if isinstance(content, list):
            content = " ".join(
                c.get("text", "") if isinstance(c, dict) else str(c)
                for c in content
            )

        # Filter: only keep messages sent by the target person
        if target_name and target_name not in str(sender):
            continue

        # Filter: skip system messages, stickers, retracted messages
        if not content or content.strip() in ["[Image]", "[File]", "[Message retracted]", "[Audio]"]:
            continue

        messages.append({
            "sender": str(sender),
            "content": str(content).strip(),
            "timestamp": str(timestamp),
        })

    return messages


def parse_feishu_txt(file_path: str, target_name: str) -> list[dict]:
    """Parse manually organized TXT format messages (format: time sender: content)"""
    messages = []

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Match format: 2024-01-01 10:00 Zhang San: message content
    pattern = re.compile(
        r"^(?P<time>\d{4}[-/]\d{1,2}[-/]\d{1,2}[\s\d:]*)\s+(?P<sender>.+?)[:：]\s*(?P<content>.+)$"
    )

    for line in lines:
        line = line.strip()
        if not line:
            continue

        m = pattern.match(line)
        if m:
            sender = m.group("sender").strip()
            content = m.group("content").strip()
            timestamp = m.group("time").strip()

            if target_name and target_name not in sender:
                continue
            if not content:
                continue

            messages.append({
                "sender": sender,
                "content": content,
                "timestamp": timestamp,
            })
        else:
            # No format match, check if line contains the target name
            if target_name and target_name in line:
                messages.append({
                    "sender": target_name,
                    "content": line,
                    "timestamp": "",
                })

    return messages


def extract_key_content(messages: list[dict]) -> dict:
    """
    Categorize and extract messages, distinguishing:
    - Long messages (>50 characters): may contain opinions, proposals, technical judgments
    - Decision-type replies: containing keywords like "agree", "disagree", "think", "suggest"
    - Everyday communication: other messages
    """
    long_messages = []
    decision_messages = []
    daily_messages = []

    decision_keywords = [
        "agree", "disagree", "think", "suggest", "should", "shouldn't", "can", "cannot",
        "proposal", "approach", "consider", "decide", "confirm", "reject", "proceed", "defer",
        "no problem", "problem", "risk", "evaluate", "judge"
    ]

    for msg in messages:
        content = msg["content"]

        if len(content) > 50:
            long_messages.append(msg)
        elif any(kw in content for kw in decision_keywords):
            decision_messages.append(msg)
        else:
            daily_messages.append(msg)

    return {
        "long_messages": long_messages,
        "decision_messages": decision_messages,
        "daily_messages": daily_messages,
        "total_count": len(messages),
    }


def format_output(target_name: str, extracted: dict) -> str:
    """Format output for AI analysis"""
    lines = [
        f"# Feishu Message Extraction Results",
        f"Target: {target_name}",
        f"Total messages: {extracted['total_count']}",
        "",
        "---",
        "",
        "## Long Messages (opinions/proposals, highest weight)",
        "",
    ]

    for msg in extracted["long_messages"]:
        ts = f"[{msg['timestamp']}] " if msg["timestamp"] else ""
        lines.append(f"{ts}{msg['content']}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Decision-type Replies",
        "",
    ]

    for msg in extracted["decision_messages"]:
        ts = f"[{msg['timestamp']}] " if msg["timestamp"] else ""
        lines.append(f"{ts}{msg['content']}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Everyday Communication (style reference)",
        "",
    ]

    # Only take first 100 everyday messages to avoid being too long
    for msg in extracted["daily_messages"][:100]:
        ts = f"[{msg['timestamp']}] " if msg["timestamp"] else ""
        lines.append(f"{ts}{msg['content']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Parse Feishu message export files")
    parser.add_argument("--file", required=True, help="Input file path (.json or .txt)")
    parser.add_argument("--target", required=True, help="Target person's name (only extract messages sent by this person)")
    parser.add_argument("--output", default=None, help="Output file path (default: print to stdout)")

    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: file not found {file_path}", file=sys.stderr)
        sys.exit(1)

    # Choose parser based on file type
    if file_path.suffix.lower() == ".json":
        messages = parse_feishu_json(str(file_path), args.target)
    else:
        messages = parse_feishu_txt(str(file_path), args.target)

    if not messages:
        print(f"Warning: no messages found from '{args.target}'", file=sys.stderr)
        print("Tip: please check whether the target name matches the sender names in the file", file=sys.stderr)

    extracted = extract_key_content(messages)
    output = format_output(args.target, extracted)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Output written to {args.output}, total {len(messages)} messages")
    else:
        print(output)


if __name__ == "__main__":
    main()
