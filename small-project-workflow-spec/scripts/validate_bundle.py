from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a generated small-project workflow bundle.")
    parser.add_argument("bundle", type=Path)
    args = parser.parse_args()
    root = args.bundle.resolve()
    errors: list[str] = []
    manifest_path = root / ".small-project-workflow-manifest.json"
    if not manifest_path.is_file():
        print("BUNDLE INVALID: missing manifest")
        return 1
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"BUNDLE INVALID: bad manifest: {exc}")
        return 1

    harness = manifest.get("harness")
    if harness not in {"opencode", "pi"}:
        fail(errors, f"unsupported harness: {harness}")
        config_root = root
    else:
        config_root = root / (".opencode" if harness == "opencode" else ".pi")
    capabilities = manifest.get("capabilities", {})
    for capability in ("isolated_subagents", "role_model_selection", "review_read_only"):
        if capabilities.get(capability) is not True:
            fail(errors, f"required capability not asserted: {capability}")
    skills_root = config_root / "skills"
    expected = set(manifest.get("skills", []))
    found = {path.name for path in skills_root.iterdir() if path.is_dir()} if skills_root.is_dir() else set()
    if found != expected:
        fail(errors, f"skill set mismatch: missing={sorted(expected-found)} extra={sorted(found-expected)}")

    names: set[str] = set()
    for directory in sorted(skills_root.iterdir()) if skills_root.is_dir() else []:
        skill_path = directory / "SKILL.md"
        if not skill_path.is_file():
            fail(errors, f"{directory.name}: missing SKILL.md")
            continue
        try:
            text = skill_path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            fail(errors, f"{directory.name}: invalid UTF-8: {exc}")
            continue
        match = re.match(r"^---\nname: ([a-z0-9-]+)\ndescription: (.+?)\n", text)
        if not match or match.group(1) != directory.name:
            fail(errors, f"{directory.name}: invalid name/frontmatter")
            continue
        if match.group(1) in names:
            fail(errors, f"duplicate skill name: {match.group(1)}")
        names.add(match.group(1))
        if harness == "pi":
            has_disable = "\ndisable-model-invocation: true\n" in text.split("---", 2)[1]
            if (directory.name != "small-project-workflow") != has_disable:
                fail(errors, f"{directory.name}: incorrect Pi implicit-invocation policy")
        if harness != "codex" and (directory / "agents" / "openai.yaml").exists():
            fail(errors, f"{directory.name}: leaked Codex metadata")

    embedded = skills_root / "small-project-workflow" / "references" / "SPEC.md"
    if not embedded.is_file():
        fail(errors, "workflow is missing embedded SPEC.md")
    elif sha256(embedded) != manifest.get("spec_sha256"):
        fail(errors, "embedded SPEC.md hash does not match manifest")

    declared_files = manifest.get("files", {})
    actual_files = {
        path.relative_to(root).as_posix(): sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and path != manifest_path
    }
    if actual_files != declared_files:
        fail(errors, "file inventory or hashes differ from manifest")

    for path in config_root.rglob("*") if config_root.is_dir() else []:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if re.search(r"{{(?:STRONG|EXECUTION)_[A-Z_]+}}", text):
            fail(errors, f"unresolved template token: {path.relative_to(root)}")

    agent_root = config_root / "agents"
    if harness == "opencode":
        required = {
            "small-project-orchestrator.md",
            "small-project-decision-planner.md",
            "small-project-implementer.md",
            "small-project-reviewer.md",
            "small-project-test-planner.md",
            "small-project-test-runner.md",
            "small-project-reporter.md",
        }
    else:
        required = {
            "small-project-decision.md",
            "small-project-implementer.md",
            "small-project-reviewer.md",
            "small-project-test-planner.md",
            "small-project-test-runner.md",
            "small-project-reporter.md",
        }
    actual_agents = {path.name for path in agent_root.glob("*.md")} if agent_root.is_dir() else set()
    if actual_agents != required:
        fail(errors, f"agent set mismatch: missing={sorted(required-actual_agents)} extra={sorted(actual_agents-required)}")

    if errors:
        print("BUNDLE INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"BUNDLE VALID: {harness}, {len(expected)} skills, {len(actual_agents)} agents")
    return 0


if __name__ == "__main__":
    sys.exit(main())
