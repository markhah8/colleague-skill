#!/usr/bin/env python3
"""
name_card_generator.py — Generate a concise name card from colleague skill files.

Usage:
    python tools/name_card_generator.py <slug>
    python tools/name_card_generator.py example_zhangsan
    python tools/name_card_generator.py --all
"""

import json
import re
import sys
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent / "colleagues"

MBTI_LABELS = {
    "INTJ": "Architect — strategic, independent, high standards",
    "INFJ": "Advocate — principled, insightful, idealistic",
    "INTP": "Thinker — analytical, inventive, loves abstract ideas",
    "ISFJ": "Defender — caring, dependable, detail-oriented",
    "ENFP": "Campaigner — enthusiastic, creative, people-oriented",
    "ENFJ": "Protagonist — charismatic, empathetic, natural leader",
    "ENTJ": "Commander — decisive, strategic, results-driven",
    "ENTP": "Debater — innovative, clever, loves a good argument",
    "ESTJ": "Executive — organized, efficient, rule-follower",
    "ISTJ": "Logistician — reliable, fact-based, methodical",
    "INFP": "Mediator — empathetic, creative, values-driven",
    "ISFP": "Adventurer — flexible, artistic, spontaneous",
    "ESTP": "Entrepreneur — bold, practical, observant",
    "ESFP": "Entertainer — spontaneous, energetic, fun-loving",
    "ESFJ": "Consul — caring, social, tradition-valuing",
    "ISTP": "Virtuoso — hands-on, analytical, reserved",
}


def load_meta(skill_dir: Path) -> dict:
    path = skill_dir / "meta.json"
    return json.loads(path.read_text()) if path.exists() else {}


def extract_layer0(text: str) -> list:
    match = re.search(r"## Layer 0.*?\n(.*?)(?=\n---|\n## )", text, re.DOTALL)
    if not match:
        return []
    return re.findall(r"^- (.+)$", match.group(1), re.MULTILINE)[:4]


def extract_catchphrases(text: str) -> list:
    match = re.search(r"[Cc]atchphrases?[^:]*:\s*(.+?)(?:\n|$)", text)
    if not match:
        return []
    raw = match.group(1)
    phrases = re.findall(r'"([^"]+)"', raw)
    if not phrases:
        phrases = [p.strip().strip('"\'') for p in raw.split(',')]
    return [p for p in phrases if p and len(p) < 60][:4]


def extract_tech_stack(text: str) -> list:
    match = re.search(r"### Tech Stack\s*\n(.+?)(?=\n###|\n##|\Z)", text, re.DOTALL | re.IGNORECASE)
    if not match:
        return []
    raw = match.group(1).strip()
    items = re.split(r"[,，\n·]", raw)
    items = [i.strip().lstrip("+-").strip() for i in items]
    return [i for i in items if i and len(i) < 35][:8]


def extract_responsibilities(text: str) -> list:
    match = re.search(r"## Scope of Responsibilities.*?\n(.*?)(?=\n---|\n##)", text, re.DOTALL | re.IGNORECASE)
    if not match:
        return []
    return re.findall(r"^- (.+)$", match.group(1), re.MULTILINE)[:3]


def extract_dislikes(text: str) -> list:
    match = re.search(r"You dislike:?\n(.*?)(?=\nYou will|\nYou avoid|\n---|\Z)", text, re.DOTALL)
    if not match:
        return []
    return re.findall(r"^- (.+)$", match.group(1), re.MULTILINE)[:4]


def generate_name_card(slug: str) -> str:
    skill_dir = BASE_DIR / slug
    if not skill_dir.exists():
        raise FileNotFoundError(f"Colleague '{slug}' not found in {BASE_DIR}")

    meta = load_meta(skill_dir)
    work_text = (skill_dir / "work.md").read_text() if (skill_dir / "work.md").exists() else ""
    persona_text = (skill_dir / "persona.md").read_text() if (skill_dir / "persona.md").exists() else ""

    profile = meta.get("profile", {})
    tags = meta.get("tags", {})

    name = meta.get("name", slug)
    company = profile.get("company", "")
    level = profile.get("level", "")
    role = profile.get("role", "")
    gender = profile.get("gender", "")
    department = profile.get("department", "")
    mbti = profile.get("mbti", "")
    impression = meta.get("impression", "")
    version = meta.get("version", "v1")
    created = meta.get("created_at", "")[:10]
    personality_tags = tags.get("personality", [])
    culture_tags = tags.get("culture", [])

    layer0 = extract_layer0(persona_text)
    catchphrases = extract_catchphrases(persona_text)
    tech_stack = extract_tech_stack(work_text)
    responsibilities = extract_responsibilities(work_text)
    dislikes = extract_dislikes(persona_text)

    dept_display = ""
    if department and department != company:
        dept_display = department.replace(company, "").lstrip(" ·").strip() or department
    identity_parts = [p for p in [
        company,
        dept_display,
        level if level and level != "None" else "",
        role,
        gender,
    ] if p]
    identity_line = " · ".join(identity_parts)

    lines = []

    # Header
    lines.append(f"# {name}")
    lines.append(f"**{identity_line}**")
    lines.append("")
    if impression:
        lines.append(f'> *"{impression}"*')
        lines.append("")
    lines.append("---")
    lines.append("")

    # Profile table
    table_rows = []
    if mbti:
        label = MBTI_LABELS.get(mbti.upper(), mbti)
        table_rows.append(f"| **MBTI** | `{mbti}` — {label} |")
    if personality_tags:
        table_rows.append(f"| **Personality** | {' · '.join(f'`{t}`' for t in personality_tags)} |")
    if culture_tags:
        table_rows.append(f"| **Culture** | {' · '.join(f'`{t}`' for t in culture_tags)} |")
    if table_rows:
        lines.append("| | |")
        lines.append("|---|---|")
        lines.extend(table_rows)
        lines.append("")

    # Tech stack
    if tech_stack:
        lines.append("## Tech Stack")
        lines.append(" ".join(f"`{t}`" for t in tech_stack))
        lines.append("")

    # Responsibilities
    if responsibilities:
        lines.append("## Responsibilities")
        for r in responsibilities:
            lines.append(f"- {r}")
        lines.append("")

    # Catchphrases
    if catchphrases:
        lines.append("## Catchphrases")
        lines.append(" · ".join(f'*"{p}"*' for p in catchphrases))
        lines.append("")

    # Core principles (Layer 0)
    if layer0:
        lines.append("## Core Principles")
        for rule in layer0:
            lines.append(f"- {rule}")
        lines.append("")

    # Avoid list
    if dislikes:
        lines.append("## Avoid Doing")
        lines.append("")
        lines.append("| |")
        lines.append("|---|")
        for d in dislikes:
            lines.append(f"| {d} |")
        lines.append("")

    lines.append("---")
    lines.append(f"*Skill {version} · Created {created} · colleague-skill*")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a name card for a colleague skill",
        epilog="Example: python tools/name_card_generator.py example_zhangsan",
    )
    parser.add_argument("slug", nargs="?", help="Colleague slug (e.g. example_zhangsan)")
    parser.add_argument("--all", action="store_true", help="Generate cards for all colleagues")
    parser.add_argument("--output", "-o", help="Output path (default: colleagues/<slug>/name_card.md)")
    args = parser.parse_args()

    card_dir = BASE_DIR / "card"
    card_dir.mkdir(exist_ok=True)

    if args.all:
        count = 0
        for skill_dir in sorted(BASE_DIR.iterdir()):
            if skill_dir.is_dir() and skill_dir.name != "card" and (skill_dir / "meta.json").exists():
                slug = skill_dir.name
                try:
                    card_content = generate_name_card(slug)
                    dest = card_dir / slug
                    dest.mkdir(exist_ok=True)
                    for f in ("meta.json", "work.md", "persona.md"):
                        src = skill_dir / f
                        if src.exists():
                            (dest / f).write_text(src.read_text())
                    (dest / "name_card.md").write_text(card_content)
                    print(f"  Generated: {dest}/")
                    count += 1
                except Exception as e:
                    print(f"  Error [{slug}]: {e}", file=sys.stderr)
        print(f"\nDone — {count} colleague card(s) in colleagues/card/")

    elif args.slug:
        try:
            card_content = generate_name_card(args.slug)
            if args.output:
                out = Path(args.output)
                out.write_text(card_content)
                print(f"Generated: {out}\n")
            else:
                dest = card_dir / args.slug
                dest.mkdir(exist_ok=True)
                src_dir = BASE_DIR / args.slug
                for f in ("meta.json", "work.md", "persona.md"):
                    src = src_dir / f
                    if src.exists():
                        (dest / f).write_text(src.read_text())
                (dest / "name_card.md").write_text(card_content)
                print(f"Generated: {dest}/\n")
            print(card_content)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        print("Available colleagues:\n")
        for skill_dir in sorted(BASE_DIR.iterdir()):
            if skill_dir.is_dir() and (skill_dir / "meta.json").exists():
                meta = json.loads((skill_dir / "meta.json").read_text())
                profile = meta.get("profile", {})
                role = profile.get("role", "")
                print(f"  {skill_dir.name:30} {meta.get('name', '')}  ({role})")
        print("\nUsage:")
        print("  python tools/name_card_generator.py <slug>")
        print("  python tools/name_card_generator.py --all")


if __name__ == "__main__":
    main()
