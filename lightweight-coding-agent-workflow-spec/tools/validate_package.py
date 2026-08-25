#!/usr/bin/env python3
"""Deterministically validate the Lightweight Coding Workflow source package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Sequence
from urllib.parse import unquote


CURRENT_VERSION = "0.5"

REQUIRED_CAPABILITIES = (
    "host_identification",
    "planner_binding",
    "model_validation",
    "worker_dispatch",
    "permission_inheritance",
    "lifecycle_control",
    "progress_reporting",
    "result_relay",
    "version_control_management",
)

CAPABILITY_OPERATIONS = {
    "host_identification": "identify_host",
    "planner_binding": "bind_planner",
    "model_validation": "validate_model",
    "worker_dispatch": "dispatch_worker",
    "permission_inheritance": "inherit_permissions",
    "lifecycle_control": "control_lifecycle",
    "progress_reporting": "report_progress",
    "result_relay": "relay_result",
    "version_control_management": "manage_version_control",
}

REQUIRED_PACKAGE_FILES = (
    "README.md",
    "DESIGN.md",
    "CHANGELOG.md",
    "agents/lightweight_implementer.toml",
    "docs/features/README.md",
    "docs/features/feature-documentation.md",
    "skills/lightweight-coding-workflow/SKILL.md",
    "skills/lightweight-coding-workflow/agents/openai.yaml",
    "skills/lightweight-coding-workflow/assets/feature-document.md",
    "skills/lightweight-coding-workflow/assets/implementation-contract.md",
    "skills/lightweight-coding-workflow/assets/coding-rules/manifest.json",
    "skills/lightweight-coding-workflow/references/protocol.md",
    "skills/lightweight-coding-workflow/references/adapter-contract.md",
    "skills/lightweight-coding-workflow/references/feature-documentation-convention.md",
    "skills/lightweight-coding-workflow/references/git-commit-convention.md",
    "skills/lightweight-coding-workflow/references/adapters/codex.md",
    "skills/lightweight-coding-workflow/references/adapters/dsh.md",
    "skills/lightweight-coding-workflow/references/adapters/template.md",
    "tests/test_validate_package.py",
    "tools/validate_package.py",
)

ADAPTER_PATHS = (
    "skills/lightweight-coding-workflow/references/adapters/codex.md",
    "skills/lightweight-coding-workflow/references/adapters/dsh.md",
    "skills/lightweight-coding-workflow/references/adapters/template.md",
)

TEMPLATE_PATHS = {
    "skills/lightweight-coding-workflow/assets/feature-document.md",
    "skills/lightweight-coding-workflow/assets/implementation-contract.md",
    "skills/lightweight-coding-workflow/references/adapters/template.md",
}

FEATURE_HEADINGS = (
    "Purpose",
    "Scope and non-goals",
    "Architecture",
    "Code map",
    "Interfaces",
    "Invariants",
    "Failure modes",
    "Dependencies",
    "Tests and verification",
    "Safe modification guidance",
    "Synchronized files",
    "Related history",
)

IGNORED_NAMES = {".DS_Store", "Thumbs.db"}
IGNORED_SUFFIXES = {".pyc", ".pyo"}
PLACEHOLDER_RE = re.compile(r"\{\{[^{}\r\n]+\}\}")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]\r\n]+\]\(([^)\r\n]+)\)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")


@dataclass(frozen=True, order=True)
class Issue:
    """One stable validation finding."""

    code: str
    path: str
    message: str

    def render(self) -> str:
        return f"ERROR [{self.code}] {self.path}: {self.message}"


def _normalized_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _is_ignored(path: Path) -> bool:
    return (
        "__pycache__" in path.parts
        or path.name in IGNORED_NAMES
        or path.suffix.lower() in IGNORED_SUFFIXES
    )


def _files_under(root: Path) -> dict[str, Path]:
    if not root.is_dir():
        return {}
    return {
        path.relative_to(root).as_posix(): path
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file() and not _is_ignored(path)
    }


def _read_text(path: Path, package_root: Path, issues: list[Issue]) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        issues.append(
            Issue(
                "TEXT_READ",
                _normalized_path(path, package_root),
                f"cannot read as UTF-8 ({exc.__class__.__name__})",
            )
        )
        return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_scalar(value: str) -> object:
    value = value.strip()
    if value == "":
        return ""
    if value in {"null", "~"}:
        return None
    if value == "true":
        return True
    if value == "false":
        return False
    if value.startswith('"') and value.endswith('"'):
        return json.loads(value)
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    return value


def parse_front_matter(text: str) -> tuple[dict[str, object], str]:
    """Parse the flat mapping/list YAML subset used by Skill and adapter metadata."""

    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing opening YAML front-matter delimiter")
    try:
        closing = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing closing YAML front-matter delimiter") from exc

    data: dict[str, object] = {}
    active_list: str | None = None
    for line_number, line in enumerate(lines[1:closing], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line:
            raise ValueError(f"line {line_number}: tabs are not valid indentation")
        list_match = re.fullmatch(r"  -\s+(.+)", line)
        if list_match:
            if active_list is None or not isinstance(data.get(active_list), list):
                raise ValueError(f"line {line_number}: list item has no list key")
            data[active_list].append(_parse_scalar(list_match.group(1)))  # type: ignore[union-attr]
            continue
        key_match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):(?:\s*(.*))?", line)
        if not key_match:
            raise ValueError(f"line {line_number}: unsupported front-matter syntax")
        key, raw_value = key_match.groups()
        if key in data:
            raise ValueError(f"line {line_number}: duplicate key {key!r}")
        if raw_value is None or raw_value == "":
            data[key] = []
            active_list = key
        else:
            data[key] = _parse_scalar(raw_value)
            active_list = None
    return data, "\n".join(lines[closing + 1 :])


def parse_ui_yaml(text: str) -> dict[str, dict[str, object]]:
    """Parse the two-level mapping subset used by agents/openai.yaml."""

    result: dict[str, dict[str, object]] = {}
    active_section: str | None = None
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "\t" in line:
            raise ValueError(f"line {line_number}: tabs are not valid indentation")
        section_match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_-]*):", line)
        if section_match:
            active_section = section_match.group(1)
            if active_section in result:
                raise ValueError(f"line {line_number}: duplicate section {active_section!r}")
            result[active_section] = {}
            continue
        value_match = re.fullmatch(
            r"  ([A-Za-z_][A-Za-z0-9_-]*):\s+(.+)", line
        )
        if not value_match or active_section is None:
            raise ValueError(f"line {line_number}: unsupported UI YAML syntax")
        key, raw_value = value_match.groups()
        if key in result[active_section]:
            raise ValueError(f"line {line_number}: duplicate key {key!r}")
        result[active_section][key] = _parse_scalar(raw_value)
    return result


def _strip_fenced_blocks(text: str) -> str:
    kept: list[str] = []
    active_fence: str | None = None
    for line in text.splitlines():
        match = FENCE_RE.match(line)
        if match:
            marker = match.group(1)
            if active_fence is None:
                active_fence = marker
            elif marker == active_fence:
                active_fence = None
            kept.append("")
        elif active_fence is None:
            kept.append(line)
        else:
            kept.append("")
    return "\n".join(kept)


def _heading_slugs(text: str) -> set[str]:
    slugs: set[str] = set()
    counts: dict[str, int] = {}
    for line in _strip_fenced_blocks(text).splitlines():
        match = HEADING_RE.match(line)
        if not match:
            continue
        heading = re.sub(r"[`*_~]", "", match.group(1)).strip().lower()
        slug = re.sub(r"[^\w\- ]", "", heading, flags=re.UNICODE)
        slug = re.sub(r"\s+", "-", slug)
        slug = re.sub(r"-+", "-", slug).strip("-")
        occurrence = counts.get(slug, 0)
        counts[slug] = occurrence + 1
        slugs.add(slug if occurrence == 0 else f"{slug}-{occurrence}")
    return slugs


def _extract_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        return target[1:-1]
    if " " in target:
        target = target.split(" ", 1)[0]
    return target


def _check_required_files(package_root: Path, issues: list[Issue]) -> None:
    for relative in REQUIRED_PACKAGE_FILES:
        if not (package_root / relative).is_file():
            issues.append(Issue("REQUIRED_FILE", relative, "required package file is missing"))


def _check_version_declarations(package_root: Path, issues: list[Issue]) -> None:
    declarations = (
        ("README.md", r"^# Lightweight Coding Agent Workflow v(?P<version>\d+\.\d+)$"),
        ("DESIGN.md", r"^版本：(?P<version>\d+\.\d+)$"),
        (
            "skills/lightweight-coding-workflow/SKILL.md",
            r"^Protocol version: `(?P<version>\d+\.\d+)`\.$",
        ),
        (
            "skills/lightweight-coding-workflow/references/protocol.md",
            r"^Protocol version: `(?P<version>\d+\.\d+)`\.$",
        ),
        (
            "skills/lightweight-coding-workflow/references/adapter-contract.md",
            r"^Contract version: `(?P<version>\d+\.\d+)`\.$",
        ),
        (
            "skills/lightweight-coding-workflow/references/feature-documentation-convention.md",
            r"^Policy version: `(?P<version>\d+\.\d+)`$",
        ),
        (
            "skills/lightweight-coding-workflow/assets/implementation-contract.md",
            r'^protocol_version: "(?P<version>\d+\.\d+)"$',
        ),
        (
            "docs/features/feature-documentation.md",
            r"^Last verified against: protocol `(?P<version>\d+\.\d+)`$",
        ),
    )
    for relative, pattern in declarations:
        path = package_root / relative
        if not path.is_file():
            continue
        text = _read_text(path, package_root, issues)
        if text is None:
            continue
        match = re.search(pattern, text, flags=re.MULTILINE)
        if match is None:
            issues.append(
                Issue("VERSION_DECLARATION", relative, "current-version declaration is missing")
            )
        elif match.group("version") != CURRENT_VERSION:
            issues.append(
                Issue(
                    "VERSION_DRIFT",
                    relative,
                    f"declares {match.group('version')}; expected {CURRENT_VERSION}",
                )
            )

    changelog = package_root / "CHANGELOG.md"
    if changelog.is_file():
        text = _read_text(changelog, package_root, issues)
        if text is not None and re.search(
            rf"^## \[{re.escape(CURRENT_VERSION)}\](?:\s+-\s+\d{{4}}-\d{{2}}-\d{{2}})?$",
            text,
            flags=re.MULTILINE,
        ) is None:
            issues.append(
                Issue(
                    "VERSION_DECLARATION",
                    "CHANGELOG.md",
                    f"release section [{CURRENT_VERSION}] is missing",
                )
            )


def _check_front_matter_and_adapters(package_root: Path, issues: list[Issue]) -> None:
    skill_path = package_root / "skills/lightweight-coding-workflow/SKILL.md"
    if skill_path.is_file():
        text = _read_text(skill_path, package_root, issues)
        if text is not None:
            try:
                metadata, _ = parse_front_matter(text)
            except (ValueError, json.JSONDecodeError) as exc:
                issues.append(Issue("YAML_FRONT_MATTER", _normalized_path(skill_path, package_root), str(exc)))
            else:
                for key in ("name", "description"):
                    if not isinstance(metadata.get(key), str) or not metadata[key]:
                        issues.append(
                            Issue(
                                "SKILL_METADATA",
                                _normalized_path(skill_path, package_root),
                                f"{key!r} must be a non-empty scalar",
                            )
                        )

    actual_states: dict[str, str] = {}
    for relative in ADAPTER_PATHS:
        path = package_root / relative
        if not path.is_file():
            continue
        text = _read_text(path, package_root, issues)
        if text is None:
            continue
        try:
            metadata, body = parse_front_matter(text)
        except (ValueError, json.JSONDecodeError) as exc:
            issues.append(Issue("ADAPTER_METADATA", relative, str(exc)))
            continue

        required_keys = {
            "host_adapter",
            "host_id",
            "display_name",
            "protocol_version",
            "adapter_version",
            "support_state",
            "supported_surfaces",
            "capabilities",
            "verified_on",
        }
        missing_keys = sorted(required_keys - set(metadata))
        if missing_keys:
            issues.append(
                Issue("ADAPTER_METADATA", relative, f"missing keys: {', '.join(missing_keys)}")
            )

        capabilities = metadata.get("capabilities")
        if not isinstance(capabilities, list):
            issues.append(Issue("ADAPTER_CAPABILITIES", relative, "capabilities must be a list"))
        elif tuple(capabilities) != REQUIRED_CAPABILITIES:
            issues.append(
                Issue(
                    "ADAPTER_CAPABILITIES",
                    relative,
                    "capabilities must contain the nine required ids exactly once in canonical order",
                )
            )

        surfaces = metadata.get("supported_surfaces")
        if not isinstance(surfaces, list) or not surfaces or any(
            not isinstance(item, str) or not item for item in surfaces
        ):
            issues.append(
                Issue("ADAPTER_METADATA", relative, "supported_surfaces must be a non-empty list")
            )

        support_state = metadata.get("support_state")
        if support_state not in {"VERIFIED", "EXPERIMENTAL", "AUTHORING_ONLY", "UNSUPPORTED"}:
            issues.append(Issue("ADAPTER_METADATA", relative, "support_state is invalid"))

        adapter_id = metadata.get("host_adapter")
        if relative.endswith("/codex.md"):
            expected = ("codex", "codex", "VERIFIED")
        elif relative.endswith("/dsh.md"):
            expected = ("dsh", "dsh", "EXPERIMENTAL")
        else:
            expected = ("{{HOST_ADAPTER_ID}}", "{{HOST_ID}}", "AUTHORING_ONLY")

        if (
            metadata.get("host_adapter"),
            metadata.get("host_id"),
            support_state,
        ) != expected:
            issues.append(
                Issue("ADAPTER_METADATA", relative, f"identity/state must be {expected!r}")
            )

        if metadata.get("protocol_version") != CURRENT_VERSION:
            issues.append(
                Issue(
                    "VERSION_DRIFT",
                    relative,
                    f"adapter protocol_version must be {CURRENT_VERSION}",
                )
            )
        if relative.endswith(("/codex.md", "/dsh.md")) and metadata.get(
            "adapter_version"
        ) != CURRENT_VERSION:
            issues.append(
                Issue(
                    "VERSION_DRIFT",
                    relative,
                    f"adapter_version must be {CURRENT_VERSION}",
                )
            )

        if support_state == "VERIFIED" and not metadata.get("verified_on"):
            issues.append(
                Issue("ADAPTER_METADATA", relative, "VERIFIED adapter requires verified_on")
            )
        if support_state != "VERIFIED" and metadata.get("verified_on") is not None:
            issues.append(
                Issue("ADAPTER_METADATA", relative, "non-VERIFIED adapter must use verified_on: null")
            )

        for operation in CAPABILITY_OPERATIONS.values():
            count = len(re.findall(rf"^## `{re.escape(operation)}`$", body, flags=re.MULTILINE))
            if count != 1:
                issues.append(
                    Issue(
                        "ADAPTER_OPERATIONS",
                        relative,
                        f"operation section {operation!r} occurs {count} times; expected once",
                    )
                )

        if isinstance(adapter_id, str) and relative != ADAPTER_PATHS[-1]:
            actual_states[adapter_id] = str(support_state)

    verified = sorted(key for key, state in actual_states.items() if state == "VERIFIED")
    if verified != ["codex"]:
        issues.append(
            Issue(
                "WRITE_GATE",
                "skills/lightweight-coding-workflow/references/adapters",
                f"exactly codex must be VERIFIED; observed {verified!r}",
            )
        )


def _check_write_gate_language(package_root: Path, issues: list[Issue]) -> None:
    required_markers = {
        "skills/lightweight-coding-workflow/SKILL.md": (
            "Require exactly one matching adapter with `support_state: VERIFIED`",
            "`EXPERIMENTAL`, `AUTHORING_ONLY`, and `UNSUPPORTED` adapters are not eligible for implementation",
        ),
        "skills/lightweight-coding-workflow/references/adapter-contract.md": (
            "Only `VERIFIED` adapters are eligible for implementation writes.",
        ),
        "skills/lightweight-coding-workflow/references/adapters/codex.md": (
            "Implementation dispatch eligibility: **yes**",
        ),
        "skills/lightweight-coding-workflow/references/adapters/dsh.md": (
            "Implementation dispatch eligibility: **no**",
            "MUST NOT call the candidate dispatch mechanism",
        ),
        "skills/lightweight-coding-workflow/references/adapters/template.md": (
            "Implementation dispatch eligibility: **no**",
        ),
    }
    for relative, markers in required_markers.items():
        path = package_root / relative
        if not path.is_file():
            continue
        text = _read_text(path, package_root, issues)
        if text is None:
            continue
        for marker in markers:
            if marker not in text:
                issues.append(
                    Issue("WRITE_GATE", relative, f"required gate statement is missing: {marker}")
                )

    stale_patterns = (
        r"explicit[- ]acknowledg(?:e)?ment selection",
        r"selectable only when the user",
        r"EXPERIMENTAL.{0,100}acknowledg",
        r"显式点名认可",
        r"需用户显式认可",
    )
    for path in _files_under(package_root).values():
        relative = _normalized_path(path, package_root)
        if path.suffix.lower() not in {".md", ".toml", ".yaml", ".json"}:
            continue
        text = _read_text(path, package_root, issues)
        if text is None:
            continue
        for pattern in stale_patterns:
            if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL):
                issues.append(
                    Issue(
                        "STALE_ELIGIBILITY",
                        relative,
                        f"obsolete non-VERIFIED selection language matches {pattern!r}",
                    )
                )


def _check_markdown_links(package_root: Path, issues: list[Issue]) -> None:
    root_resolved = package_root.resolve()
    heading_cache: dict[Path, set[str]] = {}
    for path in _files_under(package_root).values():
        if path.suffix.lower() != ".md":
            continue
        text = _read_text(path, package_root, issues)
        if text is None:
            continue
        searchable = _strip_fenced_blocks(text)
        for match in MARKDOWN_LINK_RE.finditer(searchable):
            target = _extract_link_target(match.group(1))
            if not target or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            decoded = unquote(target)
            target_path, separator, fragment = decoded.partition("#")
            target_path = target_path.split("?", 1)[0]
            if target_path:
                candidate = (
                    package_root / target_path.lstrip("/")
                    if target_path.startswith("/")
                    else path.parent / target_path
                )
            else:
                candidate = path
            try:
                candidate_resolved = candidate.resolve()
                candidate_resolved.relative_to(root_resolved)
            except (OSError, ValueError):
                issues.append(
                    Issue(
                        "LINK_OUTSIDE_PACKAGE",
                        _normalized_path(path, package_root),
                        f"relative link escapes the package: {target}",
                    )
                )
                continue
            if not candidate_resolved.is_file():
                issues.append(
                    Issue(
                        "BROKEN_LINK",
                        _normalized_path(path, package_root),
                        f"relative link target does not exist: {target}",
                    )
                )
                continue
            if separator and fragment:
                if candidate_resolved not in heading_cache:
                    destination_text = _read_text(candidate_resolved, package_root, issues)
                    heading_cache[candidate_resolved] = (
                        _heading_slugs(destination_text) if destination_text is not None else set()
                    )
                if fragment.lower() not in heading_cache[candidate_resolved]:
                    issues.append(
                        Issue(
                            "BROKEN_LINK_ANCHOR",
                            _normalized_path(path, package_root),
                            f"heading anchor does not exist: {target}",
                        )
                    )


def _check_placeholders_and_whitespace(package_root: Path, issues: list[Issue]) -> None:
    for relative, path in _files_under(package_root).items():
        if path.suffix.lower() not in {".md", ".toml", ".yaml", ".json"}:
            continue
        text = _read_text(path, package_root, issues)
        if text is None:
            continue
        if relative not in TEMPLATE_PATHS and PLACEHOLDER_RE.search(text):
            issues.append(
                Issue("UNRESOLVED_PLACEHOLDER", relative, "double-braced placeholder outside a template")
            )
        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.rstrip(" \t") != line:
                issues.append(
                    Issue("TRAILING_WHITESPACE", relative, f"line {line_number} has trailing whitespace")
                )


def _check_toml_and_ui_yaml(package_root: Path, issues: list[Issue]) -> None:
    agent_relative = "agents/lightweight_implementer.toml"
    agent_path = package_root / agent_relative
    if agent_path.is_file():
        text = _read_text(agent_path, package_root, issues)
        if text is not None:
            try:
                data = tomllib.loads(text)
            except tomllib.TOMLDecodeError as exc:
                issues.append(Issue("TOML_PARSE", agent_relative, str(exc)))
            else:
                for key in ("name", "description", "developer_instructions"):
                    if not isinstance(data.get(key), str) or not data[key]:
                        issues.append(
                            Issue("AGENT_METADATA", agent_relative, f"{key!r} must be non-empty")
                        )
                for key in ("model", "model_reasoning_effort", "sandbox_mode"):
                    if key in data:
                        issues.append(
                            Issue(
                                "AGENT_MODEL_NEUTRALITY",
                                agent_relative,
                                f"model-neutral custom Agent must omit {key!r}",
                            )
                        )

    yaml_relative = "skills/lightweight-coding-workflow/agents/openai.yaml"
    yaml_path = package_root / yaml_relative
    if yaml_path.is_file():
        text = _read_text(yaml_path, package_root, issues)
        if text is not None:
            try:
                data = parse_ui_yaml(text)
            except (ValueError, json.JSONDecodeError) as exc:
                issues.append(Issue("YAML_PARSE", yaml_relative, str(exc)))
            else:
                interface = data.get("interface", {})
                for key in ("display_name", "short_description", "default_prompt"):
                    if not isinstance(interface.get(key), str) or not interface[key]:
                        issues.append(
                            Issue("UI_METADATA", yaml_relative, f"interface.{key} must be non-empty")
                        )


def _check_feature_documentation(package_root: Path, issues: list[Issue]) -> None:
    required_markers = {
        "skills/lightweight-coding-workflow/SKILL.md": (
            "references/feature-documentation-convention.md",
            "Documentation Impact",
            "DOCUMENTATION",
        ),
        "skills/lightweight-coding-workflow/references/protocol.md": (
            "Documentation Impact",
            "## Implementation rules",
            "DOCUMENTATION:",
            "feature index",
        ),
        "skills/lightweight-coding-workflow/references/adapter-contract.md": (
            "`DOCUMENTATION` evidence",
            "nine required capabilities",
        ),
        "skills/lightweight-coding-workflow/references/adapters/codex.md": (
            "`DOCUMENTATION`",
        ),
        "skills/lightweight-coding-workflow/references/adapters/dsh.md": (
            "`DOCUMENTATION`",
        ),
        "skills/lightweight-coding-workflow/references/adapters/template.md": (
            "`DOCUMENTATION`",
        ),
        "skills/lightweight-coding-workflow/references/git-commit-convention.md": (
            "canonical feature document",
            "feature index",
        ),
        "skills/lightweight-coding-workflow/assets/implementation-contract.md": (
            "## Documentation",
            "Documentation impact",
            "Canonical feature document",
            "Feature index",
            "Code entry points",
            "Test entry points",
            "Required sections",
            "Validation obligations",
        ),
        "docs/features/README.md": (
            "[feature-documentation.md](feature-documentation.md)",
        ),
        "docs/features/feature-documentation.md": (
            "tools/validate_package.py",
            "tests/test_validate_package.py",
        ),
    }
    for relative, markers in required_markers.items():
        path = package_root / relative
        if not path.is_file():
            continue
        text = _read_text(path, package_root, issues)
        if text is None:
            continue
        for marker in markers:
            if marker not in text:
                issues.append(
                    Issue(
                        "FEATURE_DOCUMENTATION_INTEGRATION",
                        relative,
                        f"required integration marker is missing: {marker}",
                    )
                )

    for relative in (
        "skills/lightweight-coding-workflow/assets/feature-document.md",
        "docs/features/feature-documentation.md",
    ):
        path = package_root / relative
        if not path.is_file():
            continue
        text = _read_text(path, package_root, issues)
        if text is None:
            continue
        for heading in FEATURE_HEADINGS:
            if re.search(rf"^## {re.escape(heading)}$", text, flags=re.MULTILINE) is None:
                issues.append(
                    Issue(
                        "FEATURE_DOCUMENT_SECTIONS",
                        relative,
                        f"required section is missing: {heading}",
                    )
                )

    protocol_path = package_root / "skills/lightweight-coding-workflow/references/protocol.md"
    if protocol_path.is_file():
        text = _read_text(protocol_path, package_root, issues)
        if text is not None:
            if text.count("DOCUMENTATION:") != 3:
                issues.append(
                    Issue(
                        "FEATURE_DOCUMENTATION_INTEGRATION",
                        _normalized_path(protocol_path, package_root),
                        "DONE, BLOCKED, and FAILED must each contain DOCUMENTATION evidence",
                    )
                )
            for host_term in (".codex", "lightweight_implementer", "DeepSeek Harness"):
                if host_term in text:
                    issues.append(
                        Issue(
                            "CORE_HOST_NEUTRALITY",
                            _normalized_path(protocol_path, package_root),
                            f"host-specific term found in Core: {host_term}",
                        )
                    )


def _check_coding_rules_manifest(package_root: Path, issues: list[Issue]) -> None:
    bundle_relative = "skills/lightweight-coding-workflow/assets/coding-rules"
    bundle_root = package_root / bundle_relative
    manifest_path = bundle_root / "manifest.json"
    if not manifest_path.is_file():
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        issues.append(Issue("MANIFEST_PARSE", f"{bundle_relative}/manifest.json", str(exc)))
        return

    required_top = {
        "schema_version": 1,
        "protocol_version": CURRENT_VERSION,
        "hash_algorithm": "sha256",
        "bundle_root": bundle_relative,
        "manifest_excludes": ["manifest.json"],
    }
    for key, expected in required_top.items():
        if manifest.get(key) != expected:
            issues.append(
                Issue(
                    "MANIFEST_METADATA",
                    f"{bundle_relative}/manifest.json",
                    f"{key!r} must be {expected!r}",
                )
            )
    for key in ("source_spec", "source_baseline", "synchronization_policy"):
        if not isinstance(manifest.get(key), str) or not manifest[key].strip():
            issues.append(
                Issue(
                    "MANIFEST_METADATA",
                    f"{bundle_relative}/manifest.json",
                    f"{key!r} must be a non-empty string",
                )
            )

    entries = manifest.get("files")
    if not isinstance(entries, list):
        issues.append(
            Issue("MANIFEST_PARSE", f"{bundle_relative}/manifest.json", "files must be a list")
        )
        return

    declared: dict[str, dict[str, object]] = {}
    entry_paths: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            issues.append(
                Issue(
                    "MANIFEST_ENTRY",
                    f"{bundle_relative}/manifest.json",
                    f"files[{index}] must be an object",
                )
            )
            continue
        path_value = entry.get("path")
        if not isinstance(path_value, str):
            issues.append(
                Issue(
                    "MANIFEST_ENTRY",
                    f"{bundle_relative}/manifest.json",
                    f"files[{index}].path must be a string",
                )
            )
            continue
        pure = PurePosixPath(path_value)
        if (
            "\\" in path_value
            or pure.is_absolute()
            or path_value != pure.as_posix()
            or any(part in {"", ".", ".."} for part in pure.parts)
            or path_value == "manifest.json"
        ):
            issues.append(
                Issue(
                    "MANIFEST_PATH",
                    f"{bundle_relative}/manifest.json",
                    f"invalid normalized relative path: {path_value!r}",
                )
            )
        if path_value in declared:
            issues.append(
                Issue(
                    "MANIFEST_DUPLICATE",
                    f"{bundle_relative}/manifest.json",
                    f"duplicate path: {path_value}",
                )
            )
        declared[path_value] = entry
        entry_paths.append(path_value)
        digest = entry.get("sha256")
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            issues.append(
                Issue("MANIFEST_ENTRY", path_value, "sha256 must be 64 lowercase hex characters")
            )
        for field in ("provenance", "synchronization"):
            if not isinstance(entry.get(field), str) or not str(entry[field]).strip():
                issues.append(
                    Issue("MANIFEST_ENTRY", path_value, f"{field} must be a non-empty string")
                )

    if entry_paths != sorted(entry_paths):
        issues.append(
            Issue(
                "MANIFEST_ORDER",
                f"{bundle_relative}/manifest.json",
                "file entries must be sorted by normalized path",
            )
        )

    actual = _files_under(bundle_root)
    actual.pop("manifest.json", None)
    declared_set = set(declared)
    actual_set = set(actual)
    missing = sorted(declared_set - actual_set)
    extra = sorted(actual_set - declared_set)
    if missing:
        issues.append(
            Issue("MANIFEST_FILE_SET", bundle_relative, f"manifest paths missing on disk: {', '.join(missing)}")
        )
    if extra:
        issues.append(
            Issue("MANIFEST_FILE_SET", bundle_relative, f"unmanifested bundled files: {', '.join(extra)}")
        )
    for relative in sorted(actual_set & declared_set):
        expected_hash = declared[relative].get("sha256")
        if isinstance(expected_hash, str) and _sha256(actual[relative]) != expected_hash:
            issues.append(
                Issue(
                    "MANIFEST_HASH",
                    f"{bundle_relative}/{relative}",
                    "SHA-256 differs from manifest; update the file and manifest atomically",
                )
            )


def _compare_installed_tree(
    package_root: Path,
    installed_skill: Path,
    issues: list[Issue],
) -> None:
    source_skill = package_root / "skills/lightweight-coding-workflow"
    if not installed_skill.is_dir():
        issues.append(
            Issue("INSTALL_PATH", installed_skill.as_posix(), "installed Skill directory does not exist")
        )
        return
    source_files = _files_under(source_skill)
    installed_files = _files_under(installed_skill)
    source_set = set(source_files)
    installed_set = set(installed_files)
    missing = sorted(source_set - installed_set)
    extra = sorted(installed_set - source_set)
    if missing:
        issues.append(
            Issue("INSTALL_FILE_SET", installed_skill.as_posix(), f"installed Skill is missing: {', '.join(missing)}")
        )
    if extra:
        issues.append(
            Issue("INSTALL_FILE_SET", installed_skill.as_posix(), f"installed Skill has extra files: {', '.join(extra)}")
        )
    for relative in sorted(source_set & installed_set):
        if _sha256(source_files[relative]) != _sha256(installed_files[relative]):
            issues.append(
                Issue(
                    "INSTALL_CONTENT",
                    f"{installed_skill.as_posix()}/{relative}",
                    "installed file differs from the source package",
                )
            )


def _compare_installed_agent(
    package_root: Path,
    installed_agent: Path,
    issues: list[Issue],
) -> None:
    source_agent = package_root / "agents/lightweight_implementer.toml"
    if not installed_agent.is_file():
        issues.append(
            Issue("INSTALL_PATH", installed_agent.as_posix(), "installed Agent file does not exist")
        )
    elif _sha256(source_agent) != _sha256(installed_agent):
        issues.append(
            Issue(
                "INSTALL_CONTENT",
                installed_agent.as_posix(),
                "installed Agent differs from the source package",
            )
        )


def validate_package(
    package_root: Path | str,
    *,
    installed_skill: Path | str | None = None,
    installed_agent: Path | str | None = None,
) -> list[Issue]:
    """Return a stable, sorted list of package validation issues."""

    root = Path(package_root).resolve()
    issues: list[Issue] = []
    if not root.is_dir():
        return [Issue("PACKAGE_PATH", root.as_posix(), "package root does not exist")]

    _check_required_files(root, issues)
    _check_version_declarations(root, issues)
    _check_front_matter_and_adapters(root, issues)
    _check_write_gate_language(root, issues)
    _check_markdown_links(root, issues)
    _check_placeholders_and_whitespace(root, issues)
    _check_toml_and_ui_yaml(root, issues)
    _check_feature_documentation(root, issues)
    _check_coding_rules_manifest(root, issues)

    if installed_skill is not None:
        _compare_installed_tree(root, Path(installed_skill).resolve(), issues)
    if installed_agent is not None:
        _compare_installed_agent(root, Path(installed_agent).resolve(), issues)

    return sorted(set(issues))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate protocol, links, adapters, documentation, bundle integrity, and an optional installation."
    )
    parser.add_argument(
        "--package",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="package root (defaults to the parent of tools/)",
    )
    parser.add_argument(
        "--installed-skill",
        type=Path,
        help="optional installed lightweight-coding-workflow Skill directory",
    )
    parser.add_argument(
        "--installed-agent",
        type=Path,
        help="optional installed lightweight_implementer.toml path",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    issues = validate_package(
        args.package,
        installed_skill=args.installed_skill,
        installed_agent=args.installed_agent,
    )
    if issues:
        for issue in issues:
            print(issue.render())
        print(f"VALIDATION FAILED: {len(issues)} issue(s)")
        return 1
    file_count = len(_files_under(args.package.resolve()))
    print(f"VALIDATION PASSED: protocol {CURRENT_VERSION}; {file_count} package files checked")
    return 0


if __name__ == "__main__":
    sys.exit(main())
