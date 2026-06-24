#!/usr/bin/env python3.11
"""
colleague-skill MCP Server
Exposes colleague skill operations as MCP tools for Claude Desktop.

Usage (stdio, managed by Claude Desktop):
    python3.11 tools/mcp_server.py
"""

import json
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

BASE_DIR = Path(__file__).parent.parent / "colleagues"
TOOLS_DIR = Path(__file__).parent

mcp = FastMCP("colleague-skill")


def _load_meta(slug: str) -> dict:
    path = BASE_DIR / slug / "meta.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _read_file(slug: str, filename: str) -> str:
    path = BASE_DIR / slug / filename
    if not path.exists():
        return f"(File {filename} not found for colleague '{slug}')"
    return path.read_text()


def _list_slugs() -> list:
    if not BASE_DIR.exists():
        return []
    return sorted(
        d.name for d in BASE_DIR.iterdir()
        if d.is_dir() and (d / "meta.json").exists()
    )


@mcp.tool()
def list_colleagues() -> str:
    """List all generated colleague Skills with their basic info."""
    slugs = _list_slugs()
    if not slugs:
        return "No colleagues found."
    lines = [f"Found {len(slugs)} colleague(s):\n"]
    for slug in slugs:
        meta = _load_meta(slug)
        profile = meta.get("profile", {})
        name = meta.get("name", slug)
        company = profile.get("company", "")
        role = profile.get("role", "")
        level = profile.get("level", "")
        version = meta.get("version", "v1")
        parts = [p for p in [company, level, role] if p and p != "None"]
        lines.append(f"  [{slug}]  {name}  —  {' · '.join(parts)}  ({version})")
    return "\n".join(lines)


@mcp.tool()
def get_colleague(slug: str) -> str:
    """Get full details for a colleague: meta, work skill, and persona.

    Args:
        slug: The colleague's slug identifier (e.g. 'example_zhangsan', 'card')
    """
    meta = _load_meta(slug)
    if not meta:
        available = ", ".join(_list_slugs()) or "none"
        return f"Colleague '{slug}' not found. Available: {available}"

    work = _read_file(slug, "work.md")
    persona = _read_file(slug, "persona.md")

    return f"""# {meta.get('name', slug)}

## Meta
{json.dumps(meta, indent=2, ensure_ascii=False)}

---

## Work Skill
{work}

---

## Persona
{persona}
"""


@mcp.tool()
def get_work_skill(slug: str) -> str:
    """Get the work skill (technical capabilities and workflows) for a colleague.

    Args:
        slug: The colleague's slug identifier
    """
    meta = _load_meta(slug)
    if not meta:
        return f"Colleague '{slug}' not found."
    return _read_file(slug, "work.md")


@mcp.tool()
def get_persona(slug: str) -> str:
    """Get the persona (personality profile, communication style) for a colleague.

    Args:
        slug: The colleague's slug identifier
    """
    meta = _load_meta(slug)
    if not meta:
        return f"Colleague '{slug}' not found."
    return _read_file(slug, "persona.md")


@mcp.tool()
def get_name_card(slug: str) -> str:
    """Get or generate a name card summary for a colleague.

    Args:
        slug: The colleague's slug identifier
    """
    card_path = BASE_DIR / "card" / slug / "name_card.md"
    if card_path.exists():
        return card_path.read_text()

    result = subprocess.run(
        [sys.executable, str(TOOLS_DIR / "name_card_generator.py"), slug],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return f"Error generating name card: {result.stderr}"

    if card_path.exists():
        return card_path.read_text()
    return result.stdout


@mcp.tool()
def update_colleague_meta(slug: str, field: str, value: str) -> str:
    """Update a field in a colleague's meta.json.

    Args:
        slug: The colleague's slug identifier
        field: Field path using dot notation (e.g. 'profile.company', 'impression', 'profile.mbti')
        value: New value to set
    """
    meta_path = BASE_DIR / slug / "meta.json"
    if not meta_path.exists():
        return f"Colleague '{slug}' not found."

    meta = json.loads(meta_path.read_text())
    keys = field.split(".")
    target = meta
    for key in keys[:-1]:
        if key not in target:
            target[key] = {}
        target = target[key]
    target[keys[-1]] = value

    from datetime import datetime, timezone
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    return f"Updated {slug}.{field} = {value!r}"


@mcp.tool()
def write_work_skill(slug: str, content: str) -> str:
    """Write or overwrite the work.md file for a colleague.

    Args:
        slug: The colleague's slug identifier
        content: Full markdown content for work.md
    """
    path = BASE_DIR / slug / "work.md"
    if not (BASE_DIR / slug / "meta.json").exists():
        return f"Colleague '{slug}' not found."
    path.write_text(content)
    return f"work.md updated for '{slug}' ({len(content)} chars)"


@mcp.tool()
def write_persona(slug: str, content: str) -> str:
    """Write or overwrite the persona.md file for a colleague.

    Args:
        slug: The colleague's slug identifier
        content: Full markdown content for persona.md
    """
    path = BASE_DIR / slug / "persona.md"
    if not (BASE_DIR / slug / "meta.json").exists():
        return f"Colleague '{slug}' not found."
    path.write_text(content)
    return f"persona.md updated for '{slug}' ({len(content)} chars)"


@mcp.tool()
def create_colleague(slug: str, name: str, company: str = "", role: str = "", level: str = "", gender: str = "", mbti: str = "") -> str:
    """Create a new colleague skeleton with empty work.md and persona.md templates.

    Args:
        slug: URL-friendly identifier (lowercase, underscores, e.g. 'john_doe')
        name: Display name
        company: Company name
        role: Job role/title
        level: Seniority level
        gender: Gender
        mbti: MBTI type (e.g. INTJ)
    """
    skill_dir = BASE_DIR / slug
    if skill_dir.exists():
        return f"Colleague '{slug}' already exists."

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    skill_dir.mkdir(parents=True)
    (skill_dir / "versions").mkdir()
    (skill_dir / "knowledge" / "docs").mkdir(parents=True)
    (skill_dir / "knowledge" / "messages").mkdir()
    (skill_dir / "knowledge" / "emails").mkdir()

    meta = {
        "name": name,
        "slug": slug,
        "created_at": now,
        "updated_at": now,
        "version": "v1",
        "profile": {
            "company": company,
            "level": level,
            "role": role,
            "gender": gender,
            "mbti": mbti,
        },
        "tags": {"personality": [], "culture": []},
        "impression": "",
        "knowledge_sources": [],
        "corrections_count": 0,
    }
    (skill_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    (skill_dir / "work.md").write_text(f"# {name} — Work Skill\n\n## Scope of Responsibilities\n\n- (fill in)\n\n## Tech Stack\n\n(fill in)\n\n## Workflows\n\n(fill in)\n\n## Knowledge Base\n\n- (fill in)\n")
    (skill_dir / "persona.md").write_text(f"# {name} — Persona\n\n## Layer 0: Core Personality\n\n- (fill in)\n\n## Layer 1: Identity\n\n{name}, {company}, {role}.\n\n## Layer 2: Communication Style\n\n(fill in)\n\n## Layer 3: Decision-Making\n\n(fill in)\n\n## Layer 4: Interpersonal Behavior\n\n(fill in)\n\n## Layer 5: Boundaries\n\n(fill in)\n\n## Correction Log\n\n(No entries yet)\n")

    return f"Created colleague '{slug}' at {skill_dir}/\nNext: use write_work_skill and write_persona to fill in the content."


if __name__ == "__main__":
    mcp.run(transport="stdio")
