from __future__ import annotations

import re
import sys
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
EXPECTED = {
    "small-project-workflow",
    "small-project-agent-plan",
    "small-project-requirements",
    "small-project-planning",
    "small-project-implement",
    "small-project-review",
    "small-project-test-plan",
    "small-project-test-run",
    "small-project-acceptance",
    "small-project-feedback-analysis",
    "small-project-report",
    "small-project-code-contract",
    "small-project-python-rules",
    "small-project-cpp-rules",
}
SPEC_TERMS = {
    "G0 INTAKE_READY",
    "G8 DELIVERED",
    "I01-REQ-001",
    "I01-AC-001",
    "I01-TST-001",
    "AWAITING_UAT",
    "Python 向 C++ 迁移",
    "追踪矩阵",
}
FORBIDDEN_SKILL_TERMS = {"[TODO", "WebFetch", "AskUserQuestion", ".claude/"}
CPP_RESOURCES = {
    "references/project-architecture.md",
    "references/cpp-style.md",
    "references/cmake-style.md",
    "references/testing-and-validation.md",
    "references/decision-policy.md",
    "scripts/inspect_project.py",
}


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []
    found = {path.name for path in SKILLS.iterdir() if path.is_dir()}
    if found != EXPECTED:
        fail(f"skill set mismatch: missing={sorted(EXPECTED-found)} extra={sorted(found-EXPECTED)}", errors)

    names: set[str] = set()
    for directory in sorted(SKILLS.iterdir()):
        if not directory.is_dir():
            continue
        skill_path = directory / "SKILL.md"
        yaml_path = directory / "agents" / "openai.yaml"
        if not skill_path.is_file() or not yaml_path.is_file():
            fail(f"{directory.name}: missing SKILL.md or agents/openai.yaml", errors)
            continue

        text = skill_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) >= 500:
            fail(f"{directory.name}: SKILL.md has {len(lines)} lines", errors)
        if "TODO" in text:
            fail(f"{directory.name}: contains TODO", errors)
        for term in sorted(FORBIDDEN_SKILL_TERMS):
            if term in text:
                fail(f"{directory.name}: contains stale term {term}", errors)
        match = re.match(r"^---\nname: ([a-z0-9-]+)\ndescription: (.+)\n---\n", text)
        if not match:
            fail(f"{directory.name}: invalid or nonminimal frontmatter", errors)
            continue
        name, description = match.groups()
        if name != directory.name:
            fail(f"{directory.name}: frontmatter name is {name}", errors)
        if name in names:
            fail(f"duplicate name: {name}", errors)
        names.add(name)
        if not description.strip() or "[" in description:
            fail(f"{directory.name}: invalid description", errors)

        yaml = yaml_path.read_text(encoding="utf-8")
        prompt_match = re.search(r'^\s*default_prompt:\s*"([^"]+)"', yaml, re.MULTILINE)
        short_match = re.search(r'^\s*short_description:\s*"([^"]+)"', yaml, re.MULTILINE)
        policy_match = re.search(r"allow_implicit_invocation:\s*(true|false)", yaml)
        if not prompt_match or f"${name}" not in prompt_match.group(1):
            fail(f"{directory.name}: default_prompt must mention ${name}", errors)
        if not short_match or not 25 <= len(short_match.group(1)) <= 64:
            fail(f"{directory.name}: short_description outside 25-64 chars", errors)
        expected_policy = "true" if name == "small-project-workflow" else "false"
        if not policy_match or policy_match.group(1) != expected_policy:
            fail(f"{directory.name}: implicit invocation must be {expected_policy}", errors)

    spec_path = ROOT / "SPEC.md"
    spec = spec_path.read_text(encoding="utf-8") if spec_path.is_file() else ""
    if "TODO" in spec:
        fail("SPEC.md contains TODO", errors)
    suite_path = ROOT / "suite.json"
    try:
        suite = json.loads(suite_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"suite.json invalid: {exc}", errors)
        suite = {}
    if set(suite.get("skills", [])) != EXPECTED:
        fail("suite.json skill inventory differs from canonical skill set", errors)
    if set(suite.get("supported_harnesses", [])) != {"codex", "opencode", "pi"}:
        fail("suite.json must declare codex, opencode, and pi", errors)
    for term in sorted(SPEC_TERMS):
        if term not in spec:
            fail(f"SPEC.md missing invariant: {term}", errors)
    for name in sorted(EXPECTED):
        if f"`{name}`" not in spec:
            fail(f"SPEC.md does not list {name}", errors)

    cpp_root = SKILLS / "small-project-cpp-rules"
    for relative in sorted(CPP_RESOURCES):
        if not (cpp_root / relative).is_file():
            fail(f"small-project-cpp-rules missing embedded {relative}", errors)
    cpp_skill = (cpp_root / "SKILL.md").read_text(encoding="utf-8")
    if "依赖环境中的 `cpp-cmake-engineering-rules`" not in cpp_skill:
        fail("C++ skill does not explicitly prohibit external-rule dependency", errors)
    python_skill = (SKILLS / "small-project-python-rules" / "SKILL.md").read_text(encoding="utf-8")
    if "依赖环境中的其他 Python 规范 skill" not in python_skill:
        fail("Python skill is not explicitly self-contained", errors)

    for harness in ("opencode", "pi"):
        adapter = ROOT / "adapters" / harness
        try:
            config = json.loads((adapter / "harness.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            fail(f"{harness} adapter harness.json invalid: {exc}", errors)
            continue
        if config.get("adapter", {}).get("id") != harness:
            fail(f"{harness} adapter id mismatch", errors)
        templates = list((adapter / "agents").glob("*.md.tmpl"))
        expected_agents = 7 if harness == "opencode" else 6
        if len(templates) != expected_agents:
            fail(f"{harness} adapter expected {expected_agents} agent templates, found {len(templates)}", errors)
        for template in templates:
            template_text = template.read_text(encoding="utf-8")
            if not template_text.startswith("---\n") or "description:" not in template_text:
                fail(f"{harness} invalid agent template: {template.name}", errors)
        if harness == "opencode" and not (adapter / "commands" / "small-project.md").is_file():
            fail("opencode adapter missing small-project command", errors)
        if harness == "pi":
            if not (adapter / "prompts" / "small-project.md").is_file():
                fail("pi adapter missing small-project prompt", errors)
            for relative in ("agents.ts", "index.ts"):
                if not (adapter / "extensions" / "small-project-subagents" / relative).is_file():
                    fail(f"pi adapter missing extension {relative}", errors)

    if "$small-project" in "\n".join(
        path.read_text(encoding="utf-8") for path in SKILLS.glob("*/SKILL.md")
    ):
        fail("canonical skills still contain Codex-specific $small-project calls", errors)

    if errors:
        print("PACKAGE INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"PACKAGE VALID: {len(EXPECTED)} unique skills and required workflow invariants")
    return 0


if __name__ == "__main__":
    sys.exit(main())
