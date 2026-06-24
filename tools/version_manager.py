#!/usr/bin/env python3
"""
Version Manager

Responsible for versioning and rollback of Skill files.

Usage:
    python version_manager.py --action list --slug zhangsan --base-dir ~/.openclaw/...
    python version_manager.py --action backup --slug zhangsan --base-dir ~/.openclaw/...
    python version_manager.py --action rollback --slug zhangsan --version v2 --base-dir ~/.openclaw/...
"""

from __future__ import annotations

import json
import shutil
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone

MAX_VERSIONS = 10  # Maximum number of versions to retain


def list_versions(skill_dir: Path) -> list:
    """List all historical versions"""
    versions_dir = skill_dir / "versions"
    if not versions_dir.exists():
        return []

    versions = []
    for v_dir in sorted(versions_dir.iterdir()):
        if not v_dir.is_dir():
            continue

        # Parse version number from directory name
        version_name = v_dir.name

        # Get archive time (approximate using directory modification time)
        mtime = v_dir.stat().st_mtime
        archived_at = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

        # Count files
        files = [f.name for f in v_dir.iterdir() if f.is_file()]

        versions.append({
            "version": version_name,
            "archived_at": archived_at,
            "files": files,
            "path": str(v_dir),
        })

    return versions


def rollback(skill_dir: Path, target_version: str) -> bool:
    """Roll back to the specified version"""
    version_dir = skill_dir / "versions" / target_version

    if not version_dir.exists():
        print(f"Error: version {target_version} does not exist", file=sys.stderr)
        return False

    # Archive the current version first
    meta_path = skill_dir / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        current_version = meta.get("version", "v?")
        backup_dir = skill_dir / "versions" / f"{current_version}_before_rollback"
        backup_dir.mkdir(parents=True, exist_ok=True)
        for fname in ("SKILL.md", "work.md", "persona.md"):
            src = skill_dir / fname
            if src.exists():
                shutil.copy2(src, backup_dir / fname)

    # Restore files from target version
    restored_files = []
    for fname in ("SKILL.md", "work.md", "persona.md"):
        src = version_dir / fname
        if src.exists():
            shutil.copy2(src, skill_dir / fname)
            restored_files.append(fname)

    # Update meta
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["version"] = target_version + "_restored"
        meta["updated_at"] = datetime.now(timezone.utc).isoformat()
        meta["rollback_from"] = current_version
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Rolled back to {target_version}, restored files: {', '.join(restored_files)}")
    return True


def backup_current_version(skill_dir: Path) -> bool:
    """Archive the current version to the versions/ directory"""
    meta_path = skill_dir / "meta.json"
    if not meta_path.exists():
        print(f"Error: meta.json not found, cannot determine current version number", file=sys.stderr)
        return False

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    current_version = meta.get("version", "v1")

    version_dir = skill_dir / "versions" / current_version
    version_dir.mkdir(parents=True, exist_ok=True)

    backed_up = []
    for fname in ("SKILL.md", "work.md", "persona.md"):
        src = skill_dir / fname
        if src.exists():
            shutil.copy2(src, version_dir / fname)
            backed_up.append(fname)

    if backed_up:
        print(f"Archived version {current_version}, files: {', '.join(backed_up)}")
    else:
        print(f"Warning: no archivable files found for {current_version}")

    return True


def cleanup_old_versions(skill_dir: Path, max_versions: int = MAX_VERSIONS):
    """Clean up old versions that exceed the limit"""
    versions_dir = skill_dir / "versions"
    if not versions_dir.exists():
        return

    # Sort by version number, keep the most recent max_versions
    version_dirs = sorted(
        [d for d in versions_dir.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
    )

    to_delete = version_dirs[:-max_versions] if len(version_dirs) > max_versions else []

    for old_dir in to_delete:
        shutil.rmtree(old_dir)
        print(f"Cleaned up old version: {old_dir.name}")


def main():
    parser = argparse.ArgumentParser(description="Skill Version Manager")
    parser.add_argument("--action", required=True, choices=["list", "backup", "rollback", "cleanup"])
    parser.add_argument("--slug", required=True, help="Colleague slug")
    parser.add_argument("--version", help="Target version number (used with rollback)")
    parser.add_argument(
        "--base-dir",
        default="~/.openclaw/workspace/skills/colleagues",
        help="Colleague Skill root directory",
    )

    args = parser.parse_args()
    base_dir = Path(args.base_dir).expanduser()
    skill_dir = base_dir / args.slug

    if not skill_dir.exists():
        print(f"Error: cannot find Skill directory {skill_dir}", file=sys.stderr)
        sys.exit(1)

    if args.action == "list":
        versions = list_versions(skill_dir)
        if not versions:
            print(f"{args.slug} has no historical versions")
        else:
            print(f"Historical versions for {args.slug}:\n")
            for v in versions:
                print(f"  {v['version']}  Archived at: {v['archived_at']}  Files: {', '.join(v['files'])}")

    elif args.action == "backup":
        backup_current_version(skill_dir)

    elif args.action == "rollback":
        if not args.version:
            print("Error: rollback action requires --version", file=sys.stderr)
            sys.exit(1)
        rollback(skill_dir, args.version)

    elif args.action == "cleanup":
        cleanup_old_versions(skill_dir)
        print("Cleanup complete")


if __name__ == "__main__":
    main()
