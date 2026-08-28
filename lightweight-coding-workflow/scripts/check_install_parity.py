#!/usr/bin/env python3
"""Read-only source/install parity check for the workflow Skill and Agents."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

PROTOCOL_VERSION_PATTERN = re.compile(
    r"Protocol version:\s*`?([0-9]+\.[0-9]+)`?", re.IGNORECASE
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ValueError(f"unable to hash file: {path}: {exc}") from exc
    return digest.hexdigest()


def collect_files(
    root: Path, include: Callable[[Path], bool] | None = None
) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    files: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if "__pycache__" in relative.parts or path.suffix == ".pyc":
            continue
        if path.is_file() and (include is None or include(path)):
            files[relative.as_posix()] = path
    return files


def skill_file(path: Path) -> bool:
    return not (
        path.parent.name == "agents"
        and path.suffix == ".toml"
    )


def compare_files(
    source_root: Path,
    installed_root: Path,
    include: Callable[[Path], bool] | None = None,
) -> dict[str, list[str]]:
    source_files = collect_files(source_root, include)
    installed_files = collect_files(installed_root, include)
    source_names = set(source_files)
    installed_names = set(installed_files)
    missing = sorted(source_names - installed_names)
    extra = sorted(installed_names - source_names)
    changed = sorted(
        name
        for name in source_names.intersection(installed_names)
        if sha256_file(source_files[name]) != sha256_file(installed_files[name])
    )
    return {"missing": missing, "changed": changed, "extra": extra}


def compare_custom_agents(source_root: Path, installed_root: Path) -> dict[str, list[str]]:
    source_files = collect_files(source_root, lambda path: path.suffix == ".toml")
    installed_files = {
        path.name: path
        for path in sorted(installed_root.glob("*.toml"))
        if path.is_file()
    } if installed_root.is_dir() else {}
    source_names = {Path(name).name for name in source_files}
    installed_names = set(installed_files)
    missing = sorted(source_names - installed_names)
    changed = sorted(
        name
        for name in source_names.intersection(installed_names)
        if sha256_file(source_files[name]) != sha256_file(installed_files[name])
    )
    return {"missing": missing, "changed": changed, "extra": []}


def protocol_version(path: Path) -> str | None:
    skill_path = path / "SKILL.md"
    if not skill_path.is_file():
        return None
    try:
        content = skill_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    match = PROTOCOL_VERSION_PATTERN.search(content)
    return match.group(1) if match else None


def check_install_parity(
    source_skill: Path,
    installed_skill: Path,
    source_agents: Path,
    installed_agents: Path,
) -> dict[str, Any]:
    skill = compare_files(source_skill, installed_skill, skill_file)
    agents = compare_custom_agents(source_agents, installed_agents)
    source_protocol = protocol_version(source_skill)
    installed_protocol = protocol_version(installed_skill)
    protocol_drift = source_protocol != installed_protocol
    drift = any(skill.values()) or any(agents.values()) or protocol_drift
    return {
        "dry_run": True,
        "source_skill": str(source_skill),
        "installed_skill": str(installed_skill),
        "source_agents": str(source_agents),
        "installed_agents": str(installed_agents),
        "source_protocol_version": source_protocol,
        "installed_protocol_version": installed_protocol,
        "protocol_drift": protocol_drift,
        "skill": skill,
        "agents": agents,
        "drift": drift,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source_skill = Path(__file__).resolve().parents[1]
    parser.add_argument("--source-skill", type=Path, default=source_skill)
    parser.add_argument("--source-agents", type=Path, default=source_skill / "agents")
    parser.add_argument("--installed-skill", type=Path, required=True)
    parser.add_argument("--installed-agents", type=Path, required=True)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="assert the read-only mode explicitly (the checker never mutates files)",
    )
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = check_install_parity(
        args.source_skill.resolve(),
        args.installed_skill.resolve(),
        args.source_agents.resolve(),
        args.installed_agents.resolve(),
    )
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        status = "MATCH" if not report["drift"] else "DRIFT"
        print(f"Install parity (read-only dry run): {status}")
        print(
            "Protocol versions: "
            f"source={report['source_protocol_version'] or 'missing'}, "
            f"installed={report['installed_protocol_version'] or 'missing'}"
        )
        for label in ("skill", "agents"):
            result = report[label]
            for category in ("missing", "changed", "extra"):
                for item in result[category]:
                    print(f"  {label} {category}: {item}")
    return 1 if report["drift"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
