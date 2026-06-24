#!/usr/bin/env python3
"""
Email Parser

Supported formats:
1. .eml files (standard email format)
2. .txt files (plain text email records)
3. .mbox files (multi-email collection)

Usage:
    python email_parser.py --file emails.eml --target "zhangsan@company.com" --output output.txt
    python email_parser.py --file inbox.mbox --target "Zhang San" --output output.txt
"""

import email
import email.policy
import mailbox
import re
import sys
import argparse
from pathlib import Path
from email.header import decode_header
from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):
    """Extract plain text from HTML email content"""

    def __init__(self):
        super().__init__()
        self.result = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self._skip = False
        if tag in ("p", "br", "div", "tr"):
            self.result.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self.result.append(data)

    def get_text(self):
        return re.sub(r"\n{3,}", "\n\n", "".join(self.result)).strip()


def decode_mime_str(s: str) -> str:
    """Decode MIME-encoded email header fields"""
    if not s:
        return ""
    parts = decode_header(s)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            charset = charset or "utf-8"
            try:
                result.append(part.decode(charset, errors="replace"))
            except Exception:
                result.append(part.decode("utf-8", errors="replace"))
        else:
            result.append(str(part))
    return "".join(result)


def extract_email_body(msg) -> str:
    """Extract body text from an email object"""
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))

            if "attachment" in disposition:
                continue

            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                try:
                    body = payload.decode(charset, errors="replace")
                    break
                except Exception:
                    body = payload.decode("utf-8", errors="replace")
                    break

            elif content_type == "text/html" and not body:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                try:
                    html = payload.decode(charset, errors="replace")
                except Exception:
                    html = payload.decode("utf-8", errors="replace")
                extractor = HTMLTextExtractor()
                extractor.feed(html)
                body = extractor.get_text()
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            try:
                body = payload.decode(charset, errors="replace")
            except Exception:
                body = payload.decode("utf-8", errors="replace")

    # Clean up quoted content (original email quotes in Re: threads)
    body = re.sub(r"\n>.*", "", body)
    body = re.sub(r"\n-{3,}.*?Original Message.*?\n", "\n", body, flags=re.DOTALL)
    body = re.sub(r"\n_{3,}\n.*", "", body, flags=re.DOTALL)

    return body.strip()


def is_from_target(from_field: str, target: str) -> bool:
    """Check whether an email is from the target person"""
    from_str = decode_mime_str(from_field).lower()
    target_lower = target.lower()
    return target_lower in from_str


def parse_eml_file(file_path: str, target: str) -> list[dict]:
    """Parse a single .eml file"""
    with open(file_path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=email.policy.default)

    from_field = str(msg.get("From", ""))
    if not is_from_target(from_field, target):
        return []

    subject = decode_mime_str(str(msg.get("Subject", "")))
    date = str(msg.get("Date", ""))
    body = extract_email_body(msg)

    if not body:
        return []

    return [{
        "from": decode_mime_str(from_field),
        "subject": subject,
        "date": date,
        "body": body,
    }]


def parse_mbox_file(file_path: str, target: str) -> list[dict]:
    """Parse a .mbox file (multi-email collection)"""
    results = []
    mbox = mailbox.mbox(file_path)

    for msg in mbox:
        from_field = str(msg.get("From", ""))
        if not is_from_target(from_field, target):
            continue

        subject = decode_mime_str(str(msg.get("Subject", "")))
        date = str(msg.get("Date", ""))
        body = extract_email_body(msg)

        if not body:
            continue

        results.append({
            "from": decode_mime_str(from_field),
            "subject": subject,
            "date": date,
            "body": body,
        })

    return results


def parse_txt_file(file_path: str, target: str) -> list[dict]:
    """
    Parse plain text format email records.
    Supports simple delimited format:
    From: xxx
    Subject: xxx
    Date: xxx
    ---
    Body content
    ===
    """
    results = []

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Try splitting multiple emails by delimiter
    emails_raw = re.split(r"\n={3,}\n|\n-{3,}\n(?=From:)", content)

    for raw in emails_raw:
        from_match = re.search(r"^From:\s*(.+)$", raw, re.MULTILINE)
        subject_match = re.search(r"^Subject:\s*(.+)$", raw, re.MULTILINE)
        date_match = re.search(r"^Date:\s*(.+)$", raw, re.MULTILINE)

        from_field = from_match.group(1).strip() if from_match else ""
        if not is_from_target(from_field, target):
            continue

        # Extract body (content after removing header fields)
        body = re.sub(r"^(From|To|Subject|Date|CC|BCC):.*\n?", "", raw, flags=re.MULTILINE)
        body = body.strip()

        if not body:
            continue

        results.append({
            "from": from_field,
            "subject": subject_match.group(1).strip() if subject_match else "",
            "date": date_match.group(1).strip() if date_match else "",
            "body": body,
        })

    return results


def classify_emails(emails: list[dict]) -> dict:
    """
    Classify emails by content:
    - Long emails (body > 200 characters): technical proposals, opinion statements
    - Decision-type: emails containing clear judgments
    - Everyday communication: short emails
    """
    long_emails = []
    decision_emails = []
    daily_emails = []

    decision_keywords = [
        "agree", "disagree", "suggest", "proposal", "think", "should", "decide", "confirm",
        "approve", "reject", "lgtm", "suggest", "recommend", "think",
        "my opinion", "I think", "I feel", "need", "must", "don't need"
    ]

    for e in emails:
        body = e["body"]

        if len(body) > 200:
            long_emails.append(e)
        elif any(kw in body.lower() for kw in decision_keywords):
            decision_emails.append(e)
        else:
            daily_emails.append(e)

    return {
        "long_emails": long_emails,
        "decision_emails": decision_emails,
        "daily_emails": daily_emails,
        "total_count": len(emails),
    }


def format_output(target: str, classified: dict) -> str:
    """Format output for AI analysis"""
    lines = [
        f"# Email Extraction Results",
        f"Target: {target}",
        f"Total emails: {classified['total_count']}",
        "",
        "---",
        "",
        "## Long Emails (technical proposals/opinions, highest weight)",
        "",
    ]

    for e in classified["long_emails"]:
        lines.append(f"**Subject: {e['subject']}** [{e['date']}]")
        lines.append(e["body"])
        lines.append("")
        lines.append("---")
        lines.append("")

    lines += [
        "## Decision-type Emails",
        "",
    ]

    for e in classified["decision_emails"]:
        lines.append(f"**Subject: {e['subject']}** [{e['date']}]")
        lines.append(e["body"])
        lines.append("")

    lines += [
        "---",
        "",
        "## Everyday Communication (style reference)",
        "",
    ]

    for e in classified["daily_emails"][:30]:
        lines.append(f"**{e['subject']}**: {e['body'][:200]}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Parse email files and extract emails sent by the target person")
    parser.add_argument("--file", required=True, help="Input file path (.eml / .mbox / .txt)")
    parser.add_argument("--target", required=True, help="Target person (email address or name)")
    parser.add_argument("--output", default=None, help="Output file path (default: print to stdout)")

    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: file not found {file_path}", file=sys.stderr)
        sys.exit(1)

    suffix = file_path.suffix.lower()

    if suffix == ".eml":
        emails = parse_eml_file(str(file_path), args.target)
    elif suffix == ".mbox":
        emails = parse_mbox_file(str(file_path), args.target)
    else:
        emails = parse_txt_file(str(file_path), args.target)

    if not emails:
        print(f"Warning: no emails found from '{args.target}'", file=sys.stderr)
        print("Tip: please check whether the target name/email matches the From field in the file", file=sys.stderr)

    classified = classify_emails(emails)
    output = format_output(args.target, classified)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Output written to {args.output}, total {len(emails)} emails")
    else:
        print(output)


if __name__ == "__main__":
    main()
