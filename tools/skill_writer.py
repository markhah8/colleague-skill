#!/usr/bin/env python3
"""
Skill File Writer

Responsible for writing the generated work.md and persona.md to the correct
directory structure, and generating meta.json and the complete SKILL.md.

Usage:
    python3 skill_writer.py --action create --slug zhangsan --meta meta.json \
        --work work_content.md --persona persona_content.md \
        --base-dir ./colleagues

    python3 skill_writer.py --action update --slug zhangsan \
        --work-patch work_patch.md --persona-patch persona_patch.md \
        --base-dir ./colleagues

    python3 skill_writer.py --action list --base-dir ./colleagues
"""

from __future__ import annotations

import json
import shutil
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional


SKILL_MD_TEMPLATE = """\
---
name: colleague_{slug}
description: {name}, {identity}
user-invocable: true
---

# {name}

{identity}

---

## PART A: Work Capabilities

{work_content}

---

## PART B: Personality Profile

{persona_content}

---

## Operating Rules

When receiving any task or question:

1. **PART B judges first**: Will you take on this task? With what attitude?
2. **PART A executes**: Use your technical skills and working methods to complete the task
3. **Maintain PART B's expression style in output**: Your speaking style, word choices, sentence patterns

**PART B's Layer 0 rules always take priority and must never be violated under any circumstances.**
"""


def slugify(name: str) -> str:
    """
    Convert a name to a slug.
    Prefers pypinyin (if installed), otherwise falls back to simple processing.
    """
    # Try converting to pinyin with pypinyin
    try:
        from pypinyin import lazy_pinyin
        parts = lazy_pinyin(name)
        slug = "_".join(parts)
    except ImportError:
        # fallback: keep ASCII alphanumerics, skip Chinese characters
        import unicodedata
        result = []
        for char in name.lower():
            cat = unicodedata.category(char)
            if char.isascii() and (char.isalnum() or char in ("-", "_")):
                result.append(char)
            elif char == " ":
                result.append("_")
            # Skip Chinese characters (cannot convert without pypinyin)
        slug = "".join(result)

    # Clean up: remove consecutive underscores, strip leading/trailing underscores
    import re
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug if slug else "colleague"


def build_identity_string(meta: dict) -> str:
    """Build an identity description string from meta"""
    profile = meta.get("profile", {})
    parts = []

    company = profile.get("company", "")
    level = profile.get("level", "")
    role = profile.get("role", "")

    if company:
        parts.append(company)
    if level:
        parts.append(level)
    if role:
        parts.append(role)

    identity = " ".join(parts) if parts else "Colleague"

    mbti = profile.get("mbti", "")
    if mbti:
        identity += f", MBTI {mbti}"

    return identity


def create_skill(
    base_dir: Path,
    slug: str,
    meta: dict,
    work_content: str,
    persona_content: str,
) -> Path:
    """Create a new colleague Skill directory structure"""

    skill_dir = base_dir / slug
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Create subdirectories
    (skill_dir / "versions").mkdir(exist_ok=True)
    (skill_dir / "knowledge" / "docs").mkdir(parents=True, exist_ok=True)
    (skill_dir / "knowledge" / "messages").mkdir(parents=True, exist_ok=True)
    (skill_dir / "knowledge" / "emails").mkdir(parents=True, exist_ok=True)

    # Write work.md
    (skill_dir / "work.md").write_text(work_content, encoding="utf-8")

    # Write persona.md
    (skill_dir / "persona.md").write_text(persona_content, encoding="utf-8")

    # Generate and write SKILL.md
    name = meta.get("name", slug)
    identity = build_identity_string(meta)

    skill_md = SKILL_MD_TEMPLATE.format(
        slug=slug,
        name=name,
        identity=identity,
        work_content=work_content,
        persona_content=persona_content,
    )
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # Write work-only skill
    work_only = (
        f"---\nname: colleague_{slug}_work\n"
        f"description: {name}'s work capabilities (Work only, no Persona)\n"
        f"user-invocable: true\n---\n\n{work_content}\n"
    )
    (skill_dir / "work_skill.md").write_text(work_only, encoding="utf-8")

    # Write persona-only skill
    persona_only = (
        f"---\nname: colleague_{slug}_persona\n"
        f"description: {name}'s personality profile (Persona only, no work capabilities)\n"
        f"user-invocable: true\n---\n\n{persona_content}\n"
    )
    (skill_dir / "persona_skill.md").write_text(persona_only, encoding="utf-8")

    # Write meta.json
    now = datetime.now(timezone.utc).isoformat()
    meta["slug"] = slug
    meta.setdefault("created_at", now)
    meta["updated_at"] = now
    meta["version"] = "v1"
    meta.setdefault("corrections_count", 0)

    (skill_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return skill_dir


def update_skill(
    skill_dir: Path,
    work_patch: Optional[str] = None,
    persona_patch: Optional[str] = None,
    correction: Optional[dict] = None,
) -> str:
    """Update an existing Skill: archive the current version first, then write the update"""

    meta_path = skill_dir / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    current_version = meta.get("version", "v1")
    try:
        version_num = int(current_version.lstrip("v").split("_")[0]) + 1
    except ValueError:
        version_num = 2
    new_version = f"v{version_num}"

    # Archive current version
    version_dir = skill_dir / "versions" / current_version
    version_dir.mkdir(parents=True, exist_ok=True)
    for fname in ("SKILL.md", "work.md", "persona.md"):
        src = skill_dir / fname
        if src.exists():
            shutil.copy2(src, version_dir / fname)

    # Apply work patch
    if work_patch:
        current_work = (skill_dir / "work.md").read_text(encoding="utf-8")
        new_work = current_work + "\n\n" + work_patch
        (skill_dir / "work.md").write_text(new_work, encoding="utf-8")

    # Apply persona patch or correction
    if persona_patch or correction:
        current_persona = (skill_dir / "persona.md").read_text(encoding="utf-8")

        if correction:
            correction_line = (
                f"\n- [{correction.get('scene', 'General')}] "
                f"Should not {correction['wrong']}, should instead {correction['correct']}"
            )
            target = "## Correction Records"
            if target in current_persona:
                insert_pos = current_persona.index(target) + len(target)
                # Skip immediately following blank lines and "(no records)" placeholder
                rest = current_persona[insert_pos:]
                skip = "\n\n(No records)"
                if rest.startswith(skip):
                    rest = rest[len(skip):]
                new_persona = current_persona[:insert_pos] + correction_line + rest
            else:
                new_persona = (
                    current_persona
                    + f"\n\n## Correction Records\n{correction_line}\n"
                )
            meta["corrections_count"] = meta.get("corrections_count", 0) + 1
        else:
            new_persona = current_persona + "\n\n" + persona_patch

        (skill_dir / "persona.md").write_text(new_persona, encoding="utf-8")

    # Regenerate SKILL.md
    work_content = (skill_dir / "work.md").read_text(encoding="utf-8")
    persona_content = (skill_dir / "persona.md").read_text(encoding="utf-8")
    name = meta.get("name", skill_dir.name)
    identity = build_identity_string(meta)

    skill_md = SKILL_MD_TEMPLATE.format(
        slug=skill_dir.name,
        name=name,
        identity=identity,
        work_content=work_content,
        persona_content=persona_content,
    )
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

    # Update meta
    meta["version"] = new_version
    meta["updated_at"] = datetime.now(timezone.utc).isoformat()
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return new_version


def list_colleagues(base_dir: Path) -> list:
    """List all created colleague Skills"""
    colleagues = []

    if not base_dir.exists():
        return colleagues

    for skill_dir in sorted(base_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        meta_path = skill_dir / "meta.json"
        if not meta_path.exists():
            continue

        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        colleagues.append({
            "slug": meta.get("slug", skill_dir.name),
            "name": meta.get("name", skill_dir.name),
            "identity": build_identity_string(meta),
            "version": meta.get("version", "v1"),
            "updated_at": meta.get("updated_at", ""),
            "corrections_count": meta.get("corrections_count", 0),
        })

    return colleagues


def main() -> None:
    parser = argparse.ArgumentParser(description="Skill File Writer")
    parser.add_argument("--action", required=True, choices=["create", "update", "list"])
    parser.add_argument("--slug", help="Colleague slug (used as directory name)")
    parser.add_argument("--name", help="Colleague name")
    parser.add_argument("--meta", help="Path to meta.json file")
    parser.add_argument("--work", help="Path to work.md content file")
    parser.add_argument("--persona", help="Path to persona.md content file")
    parser.add_argument("--work-patch", help="Path to work.md incremental update content file")
    parser.add_argument("--persona-patch", help="Path to persona.md incremental update content file")
    parser.add_argument(
        "--base-dir",
        default="./colleagues",
        help="Colleague Skill root directory (default: ./colleagues)",
    )

    args = parser.parse_args()
    base_dir = Path(args.base_dir).expanduser()

    if args.action == "list":
        colleagues = list_colleagues(base_dir)
        if not colleagues:
            print("No colleague Skills have been created yet")
        else:
            print(f"{len(colleagues)} colleague Skill(s) created:\n")
            for c in colleagues:
                updated = c["updated_at"][:10] if c["updated_at"] else "unknown"
                print(f"  [{c['slug']}]  {c['name']} — {c['identity']}")
                print(f"    Version: {c['version']}  Corrections: {c['corrections_count']}  Updated: {updated}")
                print()

    elif args.action == "create":
        if not args.slug and not args.name:
            print("Error: create action requires --slug or --name", file=sys.stderr)
            sys.exit(1)

        meta: dict = {}
        if args.meta:
            meta = json.loads(Path(args.meta).read_text(encoding="utf-8"))
        if args.name:
            meta["name"] = args.name

        slug = args.slug or slugify(meta.get("name", "colleague"))

        work_content = ""
        if args.work:
            work_content = Path(args.work).read_text(encoding="utf-8")

        persona_content = ""
        if args.persona:
            persona_content = Path(args.persona).read_text(encoding="utf-8")

        skill_dir = create_skill(base_dir, slug, meta, work_content, persona_content)
        print(f"✅ Skill created: {skill_dir}")
        print(f"   Trigger: /{slug}")

    elif args.action == "update":
        if not args.slug:
            print("Error: update action requires --slug", file=sys.stderr)
            sys.exit(1)

        skill_dir = base_dir / args.slug
        if not skill_dir.exists():
            print(f"Error: cannot find Skill directory {skill_dir}", file=sys.stderr)
            sys.exit(1)

        work_patch = Path(args.work_patch).read_text(encoding="utf-8") if args.work_patch else None
        persona_patch = Path(args.persona_patch).read_text(encoding="utf-8") if args.persona_patch else None

        new_version = update_skill(skill_dir, work_patch, persona_patch)
        print(f"✅ Skill updated to {new_version}: {skill_dir}")


if __name__ == "__main__":
    main()
