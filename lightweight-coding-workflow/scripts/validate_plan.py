#!/usr/bin/env python3
"""Validate PLAN routing records and read-only task envelopes.

The validator uses only the Python standard library. It checks the effective
configuration digest, explicit PLAN-task authorization, structure, source
references, dependency cycles, token budgets, task capability, expansion
policy, conditional external-research decisions, source provenance, managed
search boundaries, and accidental source overlap. Token estimates are planning
approximations, not billing truth; the estimator weights CJK characters near
one token per character and other text near four characters per token.

Text-resource digests are computed from canonical UTF-8/LF content: UTF-8 text
is decoded, CRLF and lone CR line endings become LF, the text is re-encoded as
UTF-8, and SHA-256 is applied. This keeps configuration, protocol, and adapter
digests identical across CRLF (Windows autocrlf) and LF (Linux/macOS) checkouts;
binary and generated packet artifacts retain raw-byte hashing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import Any

SUPPORTED_SCHEMA_VERSION = "2.1"
SUPPORTED_CONFIG_REVISION = 3
DEFAULT_CONFIG_RELATIVE_PATH = Path("assets/context-routing/default-config.yaml")
VALID_MODES = {"lean", "balanced", "independent-review", "high-assurance"}
VALID_CONFIDENCE = {"confirmed", "inferred", "unverified"}
VALID_EXPANSION_MODES = {"deny", "request"}
VALID_ROUTING_DECISIONS = {"direct", "micro", "batch"}
VALID_EXTERNAL_RESEARCH_DECISIONS = {"required", "recommended", "not-required"}
VALID_EXTERNAL_RESEARCH_STATUSES = {
    "satisfied",
    "not-required",
    "pending",
    "unavailable",
    "disabled",
    "insufficient",
    "blocked",
}
VALID_EXTERNAL_RESEARCH_MODES = {
    "cached-indexed",
    "live",
    "direct-planner",
    "none",
}
VALID_EXTERNAL_RESEARCH_FALLBACKS = {
    "task-evidence",
    "direct-planner",
    "blocked",
    "uncertain",
    "not-applicable",
}
VALID_HOST_CAPABILITY_STATUSES = {
    "available",
    "unavailable",
    "disabled",
    "insufficient",
    "not-checked",
}
VALID_SOURCE_KINDS = {
    "local-code",
    "local-test",
    "local-documentation",
    "local-log",
    "local-other",
    "authoritative-upstream",
    "maintained-implementation",
    "upstream-issue",
    "community-secondary",
}
EXTERNAL_SOURCE_KINDS = {
    "authoritative-upstream",
    "maintained-implementation",
    "upstream-issue",
    "community-secondary",
}
VALID_SOURCE_REUSE_STATUSES = {
    "not-reused",
    "reviewed-permitted",
    "review-required",
    "prohibited",
    "unknown",
}
VALID_SOURCE_CONFIDENCE = {"low", "medium", "high"}
VALID_EVIDENCE_BARS = {
    "authoritative-plus-maintained",
    "authoritative-only-with-reason",
    "context-only",
    "not-applicable",
}
VALID_WEB_RESEARCH_TASK_KINDS = {"requirement-research", "dependency-check"}
VALID_WEB_RESEARCH_REQUEST_AVAILABILITY = {
    "available",
    "unavailable",
    "disabled",
    "insufficient",
}
EXTERNAL_URL_PATTERN = re.compile(r"^https?://[^\s]+$")
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
STALE_REVISION_VALUES = {"latest", "main", "master", "head", "trunk"}
FORBIDDEN_PLAN_AUTHORITY_FIELDS = {
    "write_authority",
    "can_write",
    "external_mutations",
    "read_only",
    "allow_writes",
    "allow_external_mutations",
    "can_mutate_external_systems",
    "scope_decision",
    "contract_authority",
    "can_author_contract",
    "spawn_agents",
    "can_spawn_agents",
    "user_interaction",
    "phase_owner",
    "network_access",
    "network",
    "internet_access",
    "shell_network",
    "shell_network_access",
    "allow_shell_network",
    "download",
    "download_remote_code",
    "execute",
    "execute_remote_code",
    "remote_code_execution",
    "authenticate",
    "authentication",
    "github_write",
    "github_mutation",
    "dependency_changes",
    "copy_third_party",
    "external_write",
    "web_mutation",
    "write",
    "mutate_external_systems",
}
READ_ONLY_TASK_KINDS = {
    "requirement-research",
    "repository-read",
    "dependency-check",
    "evidence-analysis",
}
IMPLEMENTATION_TASK_KIND = "implementation"
VALID_TASK_KINDS = {*READ_ONLY_TASK_KINDS, IMPLEMENTATION_TASK_KIND}
PLAN_TASK_MODEL = "gpt-5.6-luna"
PLAN_TASK_REASONING_EFFORT = "max"
PLAN_TASK_MAX_CONCURRENT = 2
PLAN_TASK_MAX_INPUT_TOKENS_PER_ROUND = 12000
REQUIRED_ECONOMICS_FIELDS = {
    "planner_context_savings",
    "delegated_input_tokens",
    "estimated_result_tokens",
    "coordination_overhead_tokens",
    "weighted_cost_savings",
    "weighted_cost_rationale",
    "independently_describable",
    "evidence_already_present",
    "continuous_planner_judgment",
}
REQUIRED_PLAN_TASK_POLICY_FIELDS = {
    "model",
    "reasoning_effort",
    "max_concurrent_tasks",
    "max_estimated_input_tokens_per_round",
    "pass_parent_transcript",
    "sandbox_mode",
    "allow_writes",
    "allow_external_mutations",
    "user_visible_dispatch_notice",
    "per_task_approval_required",
    "over_policy",
    "managed_web_research",
}
REQUIRED_PLAN_TASK_AUTHORIZATION_FIELDS = {
    "authorized",
    "model",
    "reasoning_effort",
    "task_count",
    "token_ceiling",
}
REQUIRED_MANAGED_WEB_RESEARCH_POLICY_FIELDS = {
    "capability",
    "allowed_task_kinds",
    "allowed_modes",
    "read_only",
    "shell_network",
    "external_mutations",
    "unavailable_fallback",
}
REQUIRED_EXTERNAL_RESEARCH_FIELDS = {
    "decision",
    "reason",
    "status",
    "mode",
    "decision_critical",
    "architecture_relevant",
    "evidence_bar",
    "target_applicability",
    "source_ids",
    "evidence",
    "limitations",
    "uncertainty",
    "risk",
    "stop_conditions",
    "conflicts",
    "conflict_resolution",
    "fallback",
    "host_capability",
}
REQUIRED_EXTERNAL_RESEARCH_POLICY_FIELDS = {
    "allowed_decisions",
    "required_triggers",
    "skip_conditions",
    "source_priority",
    "architecture_evidence_bar",
    "search_modes",
    "live_search_conditions",
    "stopping_rules",
    "security_boundary",
}
REQUIRED_HOST_CAPABILITY_FIELDS = {
    "capability",
    "status",
    "mode",
    "read_only",
    "shell_network",
    "external_mutations",
    "verified",
    "verification_method",
    "verification",
}
REQUIRED_RESEARCH_EVIDENCE_FIELDS = [
    "source_id",
    "locator",
    "note",
    "confidence",
]
REQUIRED_EXTERNAL_SOURCE_FIELDS = [
    "source_id",
    "source_kind",
    "uri",
    "repository",
    "project",
    "revision",
    "retrieved_at",
    "license",
    "reuse_status",
    "target_applicability",
    "locator",
    "confidence",
    "conflicts",
]
RESEARCH_RESULT_FIELDS = [
    "status",
    "mode",
    "limitations",
    "uncertainty",
    "conflicts",
    "conflict_resolution",
]
REQUIRED_MODEL_OVERRIDE_FIELDS = {"model", "reasoning_effort", "explicit"}
EVIDENCE_PACKET_EVIDENCE_FIELDS = ["source_id", "locator", "note"]
EVIDENCE_PACKET_FACT_FIELDS = ["id", "statement", "provenance", "confidence"]
EVIDENCE_PACKET_FINDING_SEVERITIES = {"low", "medium", "high", "critical"}
EVIDENCE_PACKET_FINDING_CONFIDENCE = {"low", "medium", "high"}
EVIDENCE_PACKET_FACT_CONFIDENCE = {"confirmed", "inferred", "unverified"}
EVIDENCE_PACKET_FINDING_SEVERITY_VALUES = ["low", "medium", "high", "critical"]
EVIDENCE_PACKET_FINDING_CONFIDENCE_VALUES = ["low", "medium", "high"]
EVIDENCE_PACKET_FACT_CONFIDENCE_VALUES = ["confirmed", "inferred", "unverified"]
VALID_SELECTOR_TYPES = {
    "lines",
    "pages",
    "symbol",
    "section",
    "object",
    "query",
    "whole",
}
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
CJK_PATTERN = re.compile(r"[\u2e80-\u9fff\u3040-\u30ff\uac00-\ud7af\uf900-\ufaff]")
REQUIRED_TASK_FIELDS = {
    "id",
    "task_kind",
    "agent_role",
    "objective",
    "dependencies",
    "source_ids",
    "questions",
    "deliverable",
    "evidence_required",
    "intentional_overlap",
    "allowed_expansion",
    "stop_conditions",
}
REQUIRED_SHARED_CONTEXT_FIELDS = {"facts", "constraints", "source_ids"}
REQUIRED_MERGE_FIELDS = {"strategy", "conflict_policy", "final_checks"}
REQUIRED_BUDGET_FIELDS = {
    "max_subagents",
    "max_input_tokens_per_task",
    "max_total_dispatched_tokens",
    "max_accidental_overlap_ratio",
    "max_shared_source_tokens_per_task",
}
REQUIRED_TOP_LEVEL_FIELDS = {
    "envelope_type",
    "schema_version",
    "plan_id",
    "goal",
    "mode",
    "configuration",
    "routing",
    "external_research",
    "plan_task_authorization",
    "plan_task_policy",
    "budget",
    "shared_context",
    "sources",
    "tasks",
    "merge",
}


def _strip_yaml_comment(value: str) -> str:
    """Remove an unquoted YAML comment from a scalar value."""
    quoted = False
    escaped = False
    for index, character in enumerate(value):
        if character == '"' and not escaped:
            quoted = not quoted
        if character == "#" and not quoted and (
            index == 0 or value[index - 1].isspace()
        ):
            return value[:index].rstrip()
        escaped = character == "\\" and not escaped
        if character != "\\":
            escaped = False
    return value.strip()


def _parse_yaml_scalar(value: str, path: Path, line_number: int) -> Any:
    value = _strip_yaml_comment(value)
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        if value.startswith("'") and value.endswith("'"):
            return value[1:-1].replace("''", "'")
        return value
    if isinstance(parsed, (dict, list, str, int, float, bool)) or parsed is None:
        return parsed
    raise ValueError(f"unsupported YAML scalar at {path}:{line_number}")


def load_yaml_mapping(path: Path) -> dict[str, Any]:
    """Load the package's small JSON-compatible YAML configuration subset.

    The default configuration intentionally uses mappings, scalar values, and
    inline JSON lists only. Keeping this parser local makes validation
    deterministic without introducing a runtime YAML dependency.
    """
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"unable to read configuration: {path}: {exc}") from exc

    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for line_number, raw_line in enumerate(lines, start=1):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if raw_line.startswith("\t"):
            raise ValueError(f"tabs are not supported in configuration at {path}:{line_number}")
        indentation = len(raw_line) - len(raw_line.lstrip(" "))
        content = raw_line.strip()
        if ":" not in content:
            raise ValueError(f"expected a mapping at {path}:{line_number}")
        key, raw_value = content.split(":", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"empty configuration key at {path}:{line_number}")

        while stack[-1][0] >= indentation:
            stack.pop()
        parent = stack[-1][1]
        if key in parent:
            raise ValueError(f"duplicate configuration key at {path}:{line_number}: {key}")
        value = _parse_yaml_scalar(raw_value, path, line_number)
        parent[key] = value
        if value == {} and not raw_value.strip():
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indentation, child))
    return root


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[1] / DEFAULT_CONFIG_RELATIVE_PATH


def load_effective_config(path: Path | None = None) -> dict[str, Any]:
    """Load the one effective routing and budget configuration source."""
    config_path = path or default_config_path()
    config = load_yaml_mapping(config_path)
    if not isinstance(config, dict):
        raise TypeError(f"configuration root must be an object: {config_path}")
    required = {
        "schema_version",
        "config_id",
        "config_revision",
        "routing_policy",
        "external_research_policy",
        "mode_profiles",
        "scout_policy",
        "plan_task_policy",
    }
    missing = sorted(required - set(config))
    if missing:
        raise ValueError(
            f"configuration is missing fields: {', '.join(missing)}: {config_path}"
        )
    if config.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        raise ValueError(
            f"configuration schema_version must be {SUPPORTED_SCHEMA_VERSION!r}: {config_path}"
        )
    if config.get("config_revision") != SUPPORTED_CONFIG_REVISION:
        raise ValueError(
            "configuration config_revision must be "
            f"{SUPPORTED_CONFIG_REVISION}: {config_path}"
        )
    policy_errors = validate_external_research_policy(
        config.get("external_research_policy")
    )
    if policy_errors:
        raise ValueError("invalid external research configuration: " + "; ".join(policy_errors))
    return config


def validate_external_research_policy(
    policy: Any, path: str = "external_research_policy"
) -> list[str]:
    """Validate the configuration policy mirrored into each PLAN proposal."""
    errors: list[str] = []
    if not isinstance(policy, dict):
        return [f"{path} must be an object"]
    missing = sorted(REQUIRED_EXTERNAL_RESEARCH_POLICY_FIELDS - set(policy))
    if missing:
        errors.append(f"{path} is missing fields: {', '.join(missing)}")
    if policy.get("allowed_decisions") != sorted(VALID_EXTERNAL_RESEARCH_DECISIONS):
        errors.append(
            f"{path}.allowed_decisions must equal {sorted(VALID_EXTERNAL_RESEARCH_DECISIONS)!r}"
        )
    if policy.get("source_priority") != [
        "authoritative-upstream",
        "maintained-implementation",
        "upstream-issue",
        "community-secondary",
    ]:
        errors.append(
            f"{path}.source_priority must list authoritative, maintained, issue, then community evidence"
        )
    for field in (
        "required_triggers",
        "skip_conditions",
        "source_priority",
        "search_modes",
        "live_search_conditions",
        "stopping_rules",
        "security_boundary",
    ):
        validate_string_list(policy.get(field), f"{path}.{field}", errors, allow_empty=False)
    if policy.get("architecture_evidence_bar") != "authoritative-plus-maintained-or-explained-single-source":
        errors.append(
            f"{path}.architecture_evidence_bar must state the authoritative-plus-maintained requirement"
        )
    if policy.get("search_modes") != ["cached-indexed", "live", "direct-planner", "none"]:
        errors.append(
            f"{path}.search_modes must equal ['cached-indexed', 'live', 'direct-planner', 'none']"
        )
    return errors


def sha256_file(path: Path) -> str:
    """Return a raw-byte SHA-256 digest for binary or generated artifacts."""
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ValueError(f"unable to hash file: {path}: {exc}") from exc
    return digest.hexdigest()


def sha256_text_normalized(path: Path) -> str:
    """Return a SHA-256 digest that is stable across CRLF and LF checkouts.

    Reads the file as bytes; when the content decodes as UTF-8 text, line
    endings are normalized to LF (``\\r\\n`` and lone ``\\r`` both become
    ``\\n``) before hashing. Binary content that cannot be decoded as UTF-8
    falls back to hashing the raw bytes.
    """
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ValueError(f"unable to hash file: {path}: {exc}") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return hashlib.sha256(raw).hexdigest()
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def load_plan(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"plan file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(data, dict):
        raise TypeError("plan root must be a JSON object")
    return data


def approximate_tokens(value: Any) -> int:
    """Approximate prompt tokens, weighting CJK characters higher.

    Latin text averages roughly four characters per token, while Han, kana,
    and hangul average closer to one token per character, so they are counted
    separately to keep CJK-heavy budgets honest.
    """
    if value is None:
        return 0
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if not value:
        return 0
    cjk = len(CJK_PATTERN.findall(value))
    return max(1, math.ceil(cjk + (len(value) - cjk) / 4))


def is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_id(value: Any) -> bool:
    return is_non_empty_string(value) and bool(ID_PATTERN.fullmatch(value))


def _validate_integer(
    value: Any, path: str, errors: list[str], *, minimum: int = 0
) -> bool:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        errors.append(f"{path} must be an integer >= {minimum}")
        return False
    return True


def _validate_boolean(value: Any, path: str, errors: list[str]) -> bool:
    if not isinstance(value, bool):
        errors.append(f"{path} must be a boolean")
        return False
    return True


def validate_economics(
    economics: Any,
    path: str,
    errors: list[str],
    *,
    require_benefit: bool,
) -> dict[str, Any]:
    """Validate the context-economics record used for routing decisions."""
    if not isinstance(economics, dict):
        errors.append(f"{path} must be an object")
        return {}

    missing = sorted(REQUIRED_ECONOMICS_FIELDS - set(economics))
    if missing:
        errors.append(f"{path} is missing fields: {', '.join(missing)}")

    for field in (
        "planner_context_savings",
        "delegated_input_tokens",
        "estimated_result_tokens",
        "coordination_overhead_tokens",
    ):
        _validate_integer(economics.get(field), f"{path}.{field}", errors)

    weighted_cost_savings = economics.get("weighted_cost_savings")
    if (
        not isinstance(weighted_cost_savings, (int, float))
        or isinstance(weighted_cost_savings, bool)
        or not math.isfinite(float(weighted_cost_savings))
    ):
        errors.append(f"{path}.weighted_cost_savings must be a finite number")

    if not is_non_empty_string(economics.get("weighted_cost_rationale")):
        errors.append(f"{path}.weighted_cost_rationale must be a non-empty string")

    for field in (
        "independently_describable",
        "evidence_already_present",
        "continuous_planner_judgment",
    ):
        _validate_boolean(economics.get(field), f"{path}.{field}", errors)

    if "total_token_savings" in economics or "total_tokens_saved" in economics:
        errors.append(
            f"{path} must not claim total-token savings; use measured evidence outside the routing estimate"
        )
    if "total_token_savings_claimed" in economics and economics.get(
        "total_token_savings_claimed"
    ) is not False:
        errors.append(
            f"{path}.total_token_savings_claimed must be false; total-token savings are not inferred"
        )

    if require_benefit and not delegation_is_beneficial(economics):
        errors.append(
            f"{path} must show Planner-context savings above coordination overhead "
            "or positive weighted-cost savings for delegation"
        )
    return economics


def delegation_is_beneficial(economics: dict[str, Any]) -> bool:
    """Return whether a bounded task clears the documented delegation gate."""
    context_savings = economics.get("planner_context_savings")
    coordination_overhead = economics.get("coordination_overhead_tokens")
    weighted_cost_savings = economics.get("weighted_cost_savings")
    return (
        isinstance(context_savings, int)
        and not isinstance(context_savings, bool)
        and isinstance(coordination_overhead, int)
        and not isinstance(coordination_overhead, bool)
        and context_savings > coordination_overhead
    ) or (
        isinstance(weighted_cost_savings, (int, float))
        and not isinstance(weighted_cost_savings, bool)
        and math.isfinite(float(weighted_cost_savings))
        and weighted_cost_savings > 0
    )


def choose_routing(
    economics: dict[str, Any], *, task_count: int = 1, multiple_information_boundaries: bool = False
) -> str:
    """Choose direct, micro, or batch PLAN handling from bounded economics."""
    if (
        economics.get("evidence_already_present") is True
        or economics.get("continuous_planner_judgment") is True
        or economics.get("independently_describable") is not True
        or not delegation_is_beneficial(economics)
    ):
        return "direct"
    if task_count > 1 or multiple_information_boundaries:
        return "batch"
    return "micro"


def _validate_expansion_policy(
    expansion: Any, path: str, errors: list[str]
) -> dict[str, Any]:
    if not isinstance(expansion, dict):
        errors.append(f"{path} must be an object")
        return {}
    mode = expansion.get("mode")
    if mode not in VALID_EXPANSION_MODES:
        errors.append(
            f"{path}.mode must be one of {sorted(VALID_EXPANSION_MODES)}"
        )
    additional = expansion.get("max_additional_tokens")
    _validate_integer(additional, f"{path}.max_additional_tokens", errors)
    if mode == "deny" and additional not in {0, None}:
        errors.append(
            f"{path}.max_additional_tokens must be 0 when expansion mode is deny"
        )
    if mode == "request" and additional == 0:
        errors.append(
            f"{path}.max_additional_tokens must be greater than 0 when expansion mode is request"
        )
    return expansion


def _reject_forbidden_plan_authority(
    value: Any, path: str, errors: list[str]
) -> None:
    """Reject network/mutation authority hidden in an otherwise open envelope."""
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in FORBIDDEN_PLAN_AUTHORITY_FIELDS:
                safe = (
                    (key == "write_authority" and child == "none")
                    or (
                        key == "external_mutations"
                        and (child is False or child == "forbidden")
                    )
                    or (
                        key
                        in {
                            "allow_writes",
                            "allow_external_mutations",
                            "shell_network",
                            "network_access",
                            "shell_network_access",
                            "allow_shell_network",
                            "user_interaction",
                        }
                        and child is False
                    )
                    or (key == "read_only" and child is True)
                )
                if not safe:
                    errors.append(
                        f"{child_path} carries forbidden write, network, or external authority"
                    )
            _reject_forbidden_plan_authority(child, child_path, errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_plan_authority(child, f"{path}[{index}]", errors)


def _validate_target_applicability(
    applicability: Any, path: str, errors: list[str]
) -> dict[str, Any]:
    if not isinstance(applicability, dict):
        errors.append(f"{path} must be an object")
        return {}
    for field in ("target_versions", "target_runtimes"):
        validate_string_list(
            applicability.get(field),
            f"{path}.{field}",
            errors,
            allow_empty=False,
        )
    if not is_non_empty_string(applicability.get("notes")):
        errors.append(f"{path}.notes must be a non-empty string")
    return applicability


def _validate_external_source_record(
    source: Any,
    path: str,
    errors: list[str],
    *,
    identifier_field: str,
) -> str | None:
    """Validate the provenance fields required for an external source."""
    if not isinstance(source, dict):
        errors.append(f"{path} must be an object")
        return None

    source_id = source.get(identifier_field)
    if not valid_id(source_id):
        errors.append(f"{path}.{identifier_field} has an invalid identifier")
        source_id = None
    source_kind = source.get("source_kind")
    if source_kind not in EXTERNAL_SOURCE_KINDS:
        errors.append(
            f"{path}.source_kind must be one of {sorted(EXTERNAL_SOURCE_KINDS)}"
        )

    uri = source.get("uri")
    if not is_non_empty_string(uri) or not EXTERNAL_URL_PATTERN.fullmatch(uri.strip()):
        errors.append(f"{path}.uri must be a direct http(s) URL for an external source")

    if not is_non_empty_string(source.get("repository")) and not is_non_empty_string(
        source.get("project")
    ):
        errors.append(f"{path} must identify a repository or project")
    revision = source.get("revision")
    if not is_non_empty_string(revision):
        errors.append(f"{path}.revision must record a commit, tag, version, or explicit unknown")
    elif revision.strip().lower() in STALE_REVISION_VALUES:
        errors.append(
            f"{path}.revision must pin a commit, tag, version, or explicit unknown; {revision!r} is stale"
        )
    retrieved_at = source.get("retrieved_at")
    if not isinstance(retrieved_at, str) or not DATE_PATTERN.fullmatch(retrieved_at):
        errors.append(f"{path}.retrieved_at must use YYYY-MM-DD format")
    if not is_non_empty_string(source.get("license")):
        errors.append(f"{path}.license must record a license or explicit unknown")
    if source.get("reuse_status") not in VALID_SOURCE_REUSE_STATUSES:
        errors.append(
            f"{path}.reuse_status must be one of {sorted(VALID_SOURCE_REUSE_STATUSES)}"
        )

    _validate_target_applicability(
        source.get("target_applicability"),
        f"{path}.target_applicability",
        errors,
    )

    if not is_non_empty_string(source.get("locator")):
        errors.append(f"{path}.locator must be a non-empty source locator")
    if source.get("confidence") not in VALID_SOURCE_CONFIDENCE:
        errors.append(
            f"{path}.confidence must be one of {sorted(VALID_SOURCE_CONFIDENCE)}"
        )
    validate_string_list(source.get("conflicts"), f"{path}.conflicts", errors)
    return source_id


def _validate_source_metadata(source: Any, path: str, errors: list[str]) -> None:
    if not isinstance(source, dict):
        return
    source_kind = source.get("source_kind")
    if source_kind not in VALID_SOURCE_KINDS:
        errors.append(f"{path}.source_kind must be one of {sorted(VALID_SOURCE_KINDS)}")
        return
    if source_kind in EXTERNAL_SOURCE_KINDS:
        _validate_external_source_record(
            source, path, errors, identifier_field="id"
        )


def _validate_host_capability(
    capability: Any, path: str, errors: list[str]
) -> dict[str, Any]:
    if not isinstance(capability, dict):
        errors.append(f"{path} must be an object")
        return {}
    missing = sorted(REQUIRED_HOST_CAPABILITY_FIELDS - set(capability))
    if missing:
        errors.append(f"{path} is missing fields: {', '.join(missing)}")
    if capability.get("capability") != "managed-web-research":
        errors.append(f"{path}.capability must be 'managed-web-research'")
    if capability.get("status") not in VALID_HOST_CAPABILITY_STATUSES:
        errors.append(
            f"{path}.status must be one of {sorted(VALID_HOST_CAPABILITY_STATUSES)}"
        )
    if capability.get("mode") not in VALID_EXTERNAL_RESEARCH_MODES:
        errors.append(
            f"{path}.mode must be one of {sorted(VALID_EXTERNAL_RESEARCH_MODES)}"
        )
    for field, expected in (
        ("read_only", True),
        ("shell_network", False),
        ("external_mutations", False),
    ):
        _validate_boolean(capability.get(field), f"{path}.{field}", errors)
        if capability.get(field) is not expected:
            errors.append(f"{path}.{field} must be exactly {expected!r}")
    if not isinstance(capability.get("verified"), bool):
        errors.append(f"{path}.verified must be a boolean")
    if not is_non_empty_string(capability.get("verification_method")):
        errors.append(f"{path}.verification_method must be a non-empty string")
    if not is_non_empty_string(capability.get("verification")):
        errors.append(f"{path}.verification must be a non-empty string")

    status = capability.get("status")
    if status == "available":
        if capability.get("verified") is not True:
            errors.append(
                f"{path}.verified must be true before managed web research is available"
            )
        if capability.get("verification_method") != "live-read-only-forward-test":
            errors.append(
                f"{path}.verification_method must be 'live-read-only-forward-test' for available capability"
            )
        verified_on = capability.get("verified_on")
        if not isinstance(verified_on, str) or not DATE_PATTERN.fullmatch(verified_on):
            errors.append(f"{path}.verified_on must use YYYY-MM-DD format for available capability")
    elif capability.get("verified") is True:
        errors.append(
            f"{path}.verified cannot be true while capability status is {status!r}"
        )
    return capability


def _validate_web_research_request(
    request: Any,
    path: str,
    errors: list[str],
    *,
    task_kind: Any,
) -> dict[str, Any]:
    if not isinstance(request, dict):
        errors.append(f"{path} must be an object")
        return {}
    required = {
        "requested",
        "mode",
        "capability",
        "availability",
        "fallback",
        "reason",
        "read_only",
        "shell_network",
        "external_mutations",
    }
    missing = sorted(required - set(request))
    if missing:
        errors.append(f"{path} is missing fields: {', '.join(missing)}")
    if not isinstance(request.get("requested"), bool):
        errors.append(f"{path}.requested must be a boolean")
    if request.get("capability") != "managed-web-research":
        errors.append(f"{path}.capability must be 'managed-web-research'")
    if request.get("mode") not in {"cached-indexed", "live", "none"}:
        errors.append(f"{path}.mode must be cached-indexed, live, or none")
    if request.get("availability") not in VALID_WEB_RESEARCH_REQUEST_AVAILABILITY:
        errors.append(
            f"{path}.availability must be one of {sorted(VALID_WEB_RESEARCH_REQUEST_AVAILABILITY)}"
        )
    if request.get("fallback") not in VALID_EXTERNAL_RESEARCH_FALLBACKS:
        errors.append(
            f"{path}.fallback must be one of {sorted(VALID_EXTERNAL_RESEARCH_FALLBACKS)}"
        )
    if not is_non_empty_string(request.get("reason")):
        errors.append(f"{path}.reason must be a non-empty string")
    for field, expected in (
        ("read_only", True),
        ("shell_network", False),
        ("external_mutations", False),
    ):
        _validate_boolean(request.get(field), f"{path}.{field}", errors)
        if request.get(field) is not expected:
            errors.append(f"{path}.{field} must be exactly {expected!r}")

    if request.get("requested") is True:
        if task_kind not in VALID_WEB_RESEARCH_TASK_KINDS:
            errors.append(
                f"{path} is allowed only for requirement-research or dependency-check tasks"
            )
        if request.get("mode") == "none":
            errors.append(f"{path}.mode cannot be none when requested is true")
        if request.get("availability") != "available" and request.get("fallback") == "none":
            errors.append(
                f"{path}.fallback must disclose uncertainty or blocking when managed search is unavailable"
            )
    elif request.get("mode") != "none":
        errors.append(f"{path}.mode must be none when requested is false")
    return request


def _managed_request_matches_gate(
    research: dict[str, Any], request: Any, task_kind: Any
) -> bool:
    """Return whether a task request can satisfy a pending or satisfied gate."""
    if isinstance(request, list):
        return any(
            _managed_request_matches_gate(research, item, kind)
            for item, kind in request
            if isinstance(item, dict)
        )
    capability = research.get("host_capability", {})
    return (
        task_kind in VALID_WEB_RESEARCH_TASK_KINDS
        and isinstance(request, dict)
        and request.get("requested") is True
        and request.get("capability") == "managed-web-research"
        and request.get("mode") == research.get("mode")
        and request.get("mode") in {"cached-indexed", "live"}
        and request.get("availability") == "available"
        and (
            research.get("status") != "pending"
            or request.get("fallback") == "task-evidence"
        )
        and (
            research.get("status") != "satisfied"
            or request.get("fallback") in {"task-evidence", "direct-planner"}
        )
        and request.get("read_only") is True
        and request.get("shell_network") is False
        and request.get("external_mutations") is False
        and capability.get("status") == "available"
        and capability.get("mode") == research.get("mode")
        and capability.get("verified") is True
        and capability.get("read_only") is True
        and capability.get("shell_network") is False
        and capability.get("external_mutations") is False
    )


def _validate_request_against_research_gate(
    research: dict[str, Any],
    request: Any,
    task_kind: Any,
    path: str,
    errors: list[str],
) -> None:
    if not isinstance(request, dict) or request.get("requested") is not True:
        return
    if research.get("status") not in {"pending", "satisfied"}:
        errors.append(
            f"{path} cannot request managed search when research gate status is {research.get('status')!r}"
        )
        return
    if not _managed_request_matches_gate(research, request, task_kind):
        errors.append(
            f"{path} mode, availability, capability, and read-only boundary must match the research gate"
        )


def _validate_research_evidence(
    evidence: Any,
    path: str,
    errors: list[str],
    source_ids: set[str],
) -> None:
    if not isinstance(evidence, list):
        errors.append(f"{path} must be an array")
        return
    for index, item in enumerate(evidence):
        item_path = f"{path}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_path} must be an object")
            continue
        for field in REQUIRED_RESEARCH_EVIDENCE_FIELDS:
            if field not in item:
                errors.append(f"{item_path} is missing required field: {field}")
        source_id = item.get("source_id")
        if not valid_id(source_id):
            errors.append(f"{item_path}.source_id has an invalid identifier")
        elif source_id not in source_ids:
            errors.append(
                f"{item_path}.source_id must reference an external research source: {source_id}"
            )
        for field in ("locator", "note"):
            if not is_non_empty_string(item.get(field)):
                errors.append(f"{item_path}.{field} must be a non-empty string")
        if item.get("confidence") not in VALID_SOURCE_CONFIDENCE:
            errors.append(
                f"{item_path}.confidence must be one of {sorted(VALID_SOURCE_CONFIDENCE)}"
            )
        validate_string_list(item.get("conflicts", []), f"{item_path}.conflicts", errors)


def validate_external_research(
    research: Any,
    path: str,
    errors: list[str],
    *,
    source_map: dict[str, dict[str, Any]] | None = None,
    direct: bool = False,
    pending_request: Any = None,
    pending_task_kind: Any = None,
) -> dict[str, Any]:
    """Validate the conditional research gate shared by PLAN envelopes."""
    if not isinstance(research, dict):
        errors.append(f"{path} must be an object")
        return {}
    missing = sorted(REQUIRED_EXTERNAL_RESEARCH_FIELDS - set(research))
    if missing:
        errors.append(f"{path} is missing fields: {', '.join(missing)}")

    decision = research.get("decision")
    if decision not in VALID_EXTERNAL_RESEARCH_DECISIONS:
        errors.append(
            f"{path}.decision must be one of {sorted(VALID_EXTERNAL_RESEARCH_DECISIONS)}"
        )
    status = research.get("status")
    if status not in VALID_EXTERNAL_RESEARCH_STATUSES:
        errors.append(
            f"{path}.status must be one of {sorted(VALID_EXTERNAL_RESEARCH_STATUSES)}"
        )
    mode = research.get("mode")
    if mode not in VALID_EXTERNAL_RESEARCH_MODES:
        errors.append(
            f"{path}.mode must be one of {sorted(VALID_EXTERNAL_RESEARCH_MODES)}"
        )
    if not is_non_empty_string(research.get("reason")):
        errors.append(f"{path}.reason must be a non-empty string")
    for field in ("decision_critical", "architecture_relevant"):
        _validate_boolean(research.get(field), f"{path}.{field}", errors)
    evidence_bar = research.get("evidence_bar")
    if evidence_bar not in VALID_EVIDENCE_BARS:
        errors.append(
            f"{path}.evidence_bar must be one of {sorted(VALID_EVIDENCE_BARS)}"
        )
    target_applicability = _validate_target_applicability(
        research.get("target_applicability"),
        f"{path}.target_applicability",
        errors,
    )
    source_ids_list = validate_string_list(
        research.get("source_ids"), f"{path}.source_ids", errors
    )
    if len(set(source_ids_list)) != len(source_ids_list):
        errors.append(f"{path}.source_ids contains duplicates")
    limitations = validate_string_list(
        research.get("limitations"), f"{path}.limitations", errors
    )
    conflicts = validate_string_list(
        research.get("conflicts"), f"{path}.conflicts", errors
    )
    validate_string_list(
        research.get("stop_conditions"), f"{path}.stop_conditions", errors, allow_empty=False
    )
    if not is_non_empty_string(research.get("uncertainty")):
        errors.append(f"{path}.uncertainty must be a non-empty string")
    if not is_non_empty_string(research.get("risk")):
        errors.append(f"{path}.risk must be a non-empty string")
    if not is_non_empty_string(research.get("conflict_resolution")):
        errors.append(f"{path}.conflict_resolution must be a non-empty string")
    fallback = research.get("fallback")
    if fallback not in VALID_EXTERNAL_RESEARCH_FALLBACKS:
        errors.append(
            f"{path}.fallback must be one of {sorted(VALID_EXTERNAL_RESEARCH_FALLBACKS)}"
        )
    capability = _validate_host_capability(
        research.get("host_capability"), f"{path}.host_capability", errors
    )

    external_source_ids = set(source_ids_list)
    direct_sources = research.get("sources", [])
    if source_map is not None:
        if direct_sources:
            errors.append(f"{path}.sources is only allowed on a direct routing record")
        for source_id in source_ids_list:
            source = source_map.get(source_id)
            if source is None:
                errors.append(f"{path}.source_ids references unknown source id: {source_id}")
            elif source.get("source_kind") not in EXTERNAL_SOURCE_KINDS:
                errors.append(
                    f"{path}.source_ids must reference external sources, got {source_id}"
                )
    elif direct:
        if not isinstance(direct_sources, list):
            errors.append(f"{path}.sources must be an array on a direct routing record")
            direct_sources = []
        direct_ids: set[str] = set()
        for index, source in enumerate(direct_sources):
            source_id = _validate_external_source_record(
                source,
                f"{path}.sources[{index}]",
                errors,
                identifier_field="source_id",
            )
            if source_id is not None:
                if source_id in direct_ids:
                    errors.append(f"duplicate external research source id: {source_id}")
                direct_ids.add(source_id)
        if set(source_ids_list) != direct_ids:
            errors.append(f"{path}.source_ids must exactly match direct {path}.sources ids")
        external_source_ids = direct_ids
    else:
        if direct_sources:
            errors.append(f"{path}.sources is only allowed on a direct routing record")

    _validate_research_evidence(
        research.get("evidence"), f"{path}.evidence", errors, external_source_ids
    )
    if source_map is not None:
        external_source_records = {
            source_id: source_map[source_id]
            for source_id in external_source_ids
            if source_id in source_map
        }
    else:
        external_source_records = {
            source.get("source_id"): source
            for source in direct_sources
            if isinstance(source, dict) and valid_id(source.get("source_id"))
        }
    source_kinds = {
        source.get("source_kind") for source in external_source_records.values()
    }
    if status == "satisfied" and isinstance(target_applicability, dict):
        for field in ("target_versions", "target_runtimes"):
            requested_values = set(target_applicability.get(field, []))
            if requested_values.intersection({"any", "all", "unknown", "not-applicable"}):
                continue
            for source_id, source in external_source_records.items():
                source_applicability = source.get("target_applicability", {})
                source_values = set(
                    source_applicability.get(field, [])
                    if isinstance(source_applicability, dict)
                    else []
                )
                if source_values.intersection({"any", "all", "unknown", "not-applicable"}):
                    continue
                if source_values and requested_values.isdisjoint(source_values):
                    errors.append(
                        f"{path}.target_applicability.{field} does not match source {source_id}"
                    )
    evidence_source_ids = {
        item.get("source_id")
        for item in research.get("evidence", [])
        if isinstance(item, dict)
    }
    if mode == "live" and not is_non_empty_string(research.get("live_reason")):
        errors.append(f"{path}.live_reason must explain why freshness requires live search")

    if decision == "not-required":
        if status != "not-required":
            errors.append(f"{path}.status must be 'not-required' when research is not required")
        if mode != "none":
            errors.append(f"{path}.mode must be 'none' when research is not required")
        if research.get("decision_critical") is not False:
            errors.append(f"{path}.decision_critical must be false when research is not required")
        if source_ids_list or research.get("evidence"):
            errors.append(f"{path} must not contain research sources or evidence when not required")
        if evidence_bar != "not-applicable":
            errors.append(f"{path}.evidence_bar must be 'not-applicable' when research is not required")
        if fallback != "not-applicable":
            errors.append(
                f"{path}.fallback must be 'not-applicable' when research is not required"
            )
    else:
        if status == "not-required":
            errors.append(f"{path}.status cannot be 'not-required' when research is selected")
        if status == "satisfied":
            if mode == "none":
                errors.append(f"{path}.mode cannot be 'none' for satisfied research")
            if not source_ids_list:
                errors.append(f"{path}.source_ids must contain evidence for satisfied research")
            if not isinstance(research.get("evidence"), list) or not research.get("evidence"):
                errors.append(f"{path}.evidence must be non-empty for satisfied research")
            if fallback not in {"task-evidence", "direct-planner"}:
                errors.append(f"{path}.fallback must route satisfied research to evidence or Planner search")
            if mode in {"cached-indexed", "live", "direct-planner"} and capability.get("status") != "available":
                errors.append(
                    f"{path}.host_capability.status must be 'available' for satisfied managed research"
                )
            if research.get("architecture_relevant") is True:
                if evidence_bar == "authoritative-plus-maintained":
                    if "authoritative-upstream" not in source_kinds or "maintained-implementation" not in source_kinds:
                        errors.append(
                            f"{path} requires one authoritative-upstream and one maintained-implementation source"
                        )
                    evidence_kinds = {
                        external_source_records[source_id].get("source_kind")
                        for source_id in evidence_source_ids
                        if source_id in external_source_records
                    }
                    if not {
                        "authoritative-upstream",
                        "maintained-implementation",
                    }.issubset(evidence_kinds):
                        errors.append(
                            f"{path}.evidence must cite both authoritative-upstream and maintained-implementation sources"
                        )
                elif evidence_bar == "authoritative-only-with-reason":
                    if not is_non_empty_string(research.get("only_one_source_reason")):
                        errors.append(
                            f"{path}.only_one_source_reason is required when only one authoritative source exists"
                        )
                    if "authoritative-upstream" not in source_kinds:
                        errors.append(f"{path} requires an authoritative-upstream source")
                    if not any(
                        external_source_records.get(source_id, {}).get("source_kind")
                        == "authoritative-upstream"
                        for source_id in evidence_source_ids
                    ):
                        errors.append(
                            f"{path}.evidence must cite the authoritative-upstream source"
                        )
                else:
                    errors.append(
                        f"{path}.evidence_bar must corroborate architecture with authoritative and maintained evidence"
                    )
            elif evidence_bar == "not-applicable":
                errors.append(
                    f"{path}.evidence_bar cannot be 'not-applicable' for selected research"
                )
            if capability.get("mode") != mode:
                errors.append(f"{path}.host_capability.mode must match the research mode")
        elif status == "pending":
            if fallback != "task-evidence":
                errors.append(f"{path}.fallback must be 'task-evidence' while research is pending")
            if mode not in {"cached-indexed", "live"}:
                errors.append(
                    f"{path}.mode must be cached-indexed or live while managed research is pending"
                )
            if not _managed_request_matches_gate(
                research, pending_request, pending_task_kind
            ):
                errors.append(
                    f"{path} pending status requires an eligible available verified managed-search task request"
                )
        elif status in {"unavailable", "disabled", "insufficient", "blocked"}:
            if not limitations:
                errors.append(
                    f"{path}.limitations must record why selected research is unavailable or insufficient"
                )
            if fallback not in {"direct-planner", "uncertain", "blocked"}:
                errors.append(
                    f"{path}.fallback must be direct-planner, uncertain, or blocked when research is unavailable"
                )
            elif fallback == "direct-planner" and mode != "direct-planner":
                errors.append(
                    f"{path}.mode must be direct-planner when the fallback is direct-planner"
                )
            elif fallback in {"uncertain", "blocked"} and mode != "none":
                errors.append(
                    f"{path}.mode must be none when the fallback is {fallback!r}"
                )
            if status in {"unavailable", "disabled", "blocked"} and capability.get(
                "status"
            ) == "available":
                errors.append(
                    f"{path}.host_capability.status cannot be available for {status!r} research"
                )
            if research.get("decision_critical") is True:
                errors.append(
                    f"{path} is decision-critical and cannot be approved with status {status!r}"
                )
        else:
            errors.append(f"{path}.status {status!r} is not a usable research result")

    if conflicts and research.get("conflict_resolution") == "No material conflict identified.":
        errors.append(f"{path}.conflict_resolution must address the recorded conflicts")
    if status in {"unavailable", "disabled", "insufficient", "blocked"} and not limitations:
        errors.append(f"{path}.limitations must not be empty for status {status!r}")
    return research


def _validate_plan_task_policy(
    policy: Any, path: str, errors: list[str]
) -> dict[str, Any]:
    if not isinstance(policy, dict):
        errors.append(f"{path} must be an object")
        return {}
    missing = sorted(REQUIRED_PLAN_TASK_POLICY_FIELDS - set(policy))
    if missing:
        errors.append(f"{path} is missing fields: {', '.join(missing)}")

    expected_strings = {
        "model": PLAN_TASK_MODEL,
        "reasoning_effort": PLAN_TASK_REASONING_EFFORT,
        "sandbox_mode": "read-only",
        "over_policy": "user-approval-or-direct-fallback",
    }
    for field, expected in expected_strings.items():
        if policy.get(field) != expected:
            errors.append(
                f"{path}.{field} must be exactly {expected!r} for the pre-authorized Codex PLAN-task policy"
            )

    for field, expected in {
        "max_concurrent_tasks": PLAN_TASK_MAX_CONCURRENT,
        "max_estimated_input_tokens_per_round": PLAN_TASK_MAX_INPUT_TOKENS_PER_ROUND,
    }.items():
        if policy.get(field) != expected:
            errors.append(f"{path}.{field} must be exactly {expected}")

    for field in (
        "pass_parent_transcript",
        "allow_writes",
        "allow_external_mutations",
        "user_visible_dispatch_notice",
        "per_task_approval_required",
    ):
        _validate_boolean(policy.get(field), f"{path}.{field}", errors)

    if policy.get("pass_parent_transcript") is not False:
        errors.append(f"{path}.pass_parent_transcript must be false")
    for field in ("allow_writes", "allow_external_mutations"):
        if policy.get(field) is not False:
            errors.append(f"{path}.{field} must be false")
    if policy.get("user_visible_dispatch_notice") is not True:
        errors.append(f"{path}.user_visible_dispatch_notice must be true")
    if policy.get("per_task_approval_required") is not False:
        errors.append(f"{path}.per_task_approval_required must be false within policy")
    web_policy = policy.get("managed_web_research")
    if not isinstance(web_policy, dict):
        errors.append(f"{path}.managed_web_research must be an object")
    else:
        missing_web = sorted(
            REQUIRED_MANAGED_WEB_RESEARCH_POLICY_FIELDS - set(web_policy)
        )
        if missing_web:
            errors.append(
                f"{path}.managed_web_research is missing fields: {', '.join(missing_web)}"
            )
        if web_policy.get("capability") != "managed-web-research":
            errors.append(
                f"{path}.managed_web_research.capability must be 'managed-web-research'"
            )
        if web_policy.get("allowed_task_kinds") != sorted(VALID_WEB_RESEARCH_TASK_KINDS):
            errors.append(
                f"{path}.managed_web_research.allowed_task_kinds must equal the eligible research task kinds"
            )
        if web_policy.get("allowed_modes") != ["cached-indexed", "live"]:
            errors.append(
                f"{path}.managed_web_research.allowed_modes must be ['cached-indexed', 'live']"
            )
        for field, expected in (
            ("read_only", True),
            ("shell_network", False),
            ("external_mutations", False),
        ):
            _validate_boolean(
                web_policy.get(field),
                f"{path}.managed_web_research.{field}",
                errors,
            )
            if web_policy.get(field) is not expected:
                errors.append(
                    f"{path}.managed_web_research.{field} must be exactly {expected!r}"
                )
        if web_policy.get("unavailable_fallback") != "direct-planner-or-blocked":
            errors.append(
                f"{path}.managed_web_research.unavailable_fallback must be 'direct-planner-or-blocked'"
            )
    return policy


def _validate_plan_task_authorization(
    authorization: Any,
    path: str,
    errors: list[str],
    *,
    expected_task_count: int,
    policy: dict[str, Any],
    token_ceiling: int | None = None,
) -> dict[str, Any]:
    if not isinstance(authorization, dict):
        errors.append(f"{path} must be an object")
        return {}
    missing = sorted(REQUIRED_PLAN_TASK_AUTHORIZATION_FIELDS - set(authorization))
    if missing:
        errors.append(f"{path} is missing fields: {', '.join(missing)}")
    if authorization.get("authorized") is not True:
        errors.append(f"{path}.authorized must be true")
    if authorization.get("model") != PLAN_TASK_MODEL:
        errors.append(f"{path}.model must be exactly {PLAN_TASK_MODEL!r}")
    if authorization.get("reasoning_effort") != PLAN_TASK_REASONING_EFFORT:
        errors.append(
            f"{path}.reasoning_effort must be exactly {PLAN_TASK_REASONING_EFFORT!r}"
        )
    if authorization.get("task_count") != expected_task_count:
        errors.append(
            f"{path}.task_count must equal the number of dispatched PLAN tasks ({expected_task_count})"
        )
    if not _validate_integer(authorization.get("token_ceiling"), f"{path}.token_ceiling", errors, minimum=1):
        return authorization
    ceiling = authorization["token_ceiling"]
    maximum = policy.get("max_estimated_input_tokens_per_round")
    if isinstance(maximum, int) and ceiling > maximum:
        errors.append(
            f"{path}.token_ceiling must not exceed the PLAN-task policy ceiling {maximum}"
        )
    if token_ceiling is not None and ceiling > token_ceiling:
        errors.append(f"{path}.token_ceiling must not exceed {token_ceiling}")
    return authorization


def _validate_model_override(
    model_override: Any, path: str, errors: list[str]
) -> dict[str, Any]:
    if not isinstance(model_override, dict):
        errors.append(f"{path} must be an object")
        return {}
    missing = sorted(REQUIRED_MODEL_OVERRIDE_FIELDS - set(model_override))
    if missing:
        errors.append(f"{path} is missing fields: {', '.join(missing)}")
    if model_override.get("model") != PLAN_TASK_MODEL:
        errors.append(f"{path}.model must be exactly {PLAN_TASK_MODEL!r}")
    if model_override.get("reasoning_effort") != PLAN_TASK_REASONING_EFFORT:
        errors.append(
            f"{path}.reasoning_effort must be exactly {PLAN_TASK_REASONING_EFFORT!r}"
        )
    if model_override.get("explicit") is not True:
        errors.append(f"{path}.explicit must be true for each PLAN task")
    return model_override


def _validate_source_descriptors(
    sources_value: Any,
    path: str,
    errors: list[str],
    *,
    require_one: bool,
) -> dict[str, dict[str, Any]]:
    if not isinstance(sources_value, list):
        errors.append(f"{path} must be an array")
        return {}
    if require_one and not sources_value:
        errors.append(f"{path} must contain at least one source descriptor")
    sources: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(sources_value):
        source_path = f"{path}[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{source_path} must be an object")
            continue
        source_id = source.get("id")
        if not valid_id(source_id):
            errors.append(f"{source_path}.id has an invalid identifier")
            continue
        if source_id in sources:
            errors.append(f"duplicate source id: {source_id}")
            continue
        if not is_non_empty_string(source.get("uri")):
            errors.append(f"{source_path}.uri must be a non-empty string")
        validate_selector(source.get("selector"), f"{source_path}.selector", errors)
        _validate_integer(
            source.get("estimated_tokens"),
            f"{source_path}.estimated_tokens",
            errors,
            minimum=1,
        )
        if not is_non_empty_string(source.get("purpose")):
            errors.append(f"{source_path}.purpose must be a non-empty string")
        _validate_source_metadata(source, source_path, errors)
        sources[source_id] = source
    return sources


def _validate_response_contract(
    response_contract: Any, path: str, errors: list[str]
) -> None:
    if not isinstance(response_contract, dict):
        errors.append(f"{path} must be an object")
        return
    expected = {
        "schema_version": SUPPORTED_SCHEMA_VERSION,
        "packet_type": "subagent-result",
        "schema_ref": "assets/context-routing/evidence-packet.schema.json",
        "validation_authority": "scripts/validate_evidence_packet.py",
    }
    for field, value in expected.items():
        if response_contract.get(field) != value:
            errors.append(f"{path}.{field} must be exactly {value!r}")
    if response_contract.get("task_kinds") != sorted(READ_ONLY_TASK_KINDS):
        errors.append(
            f"{path}.task_kinds must equal the supported read-only task kinds"
        )
    contract_values = {
        "finding_severity_values": EVIDENCE_PACKET_FINDING_SEVERITY_VALUES,
        "finding_confidence_values": EVIDENCE_PACKET_FINDING_CONFIDENCE_VALUES,
        "evidence_fields": EVIDENCE_PACKET_EVIDENCE_FIELDS,
        "fact_fields": EVIDENCE_PACKET_FACT_FIELDS,
        "fact_confidence_values": EVIDENCE_PACKET_FACT_CONFIDENCE_VALUES,
        "external_source_fields": REQUIRED_EXTERNAL_SOURCE_FIELDS,
        "research_result_fields": RESEARCH_RESULT_FIELDS,
    }
    for field, value in contract_values.items():
        if response_contract.get(field) != value:
            errors.append(f"{path}.{field} must be exactly {value!r}")


def _validate_task_kind(value: Any, path: str, errors: list[str]) -> None:
    if value not in VALID_TASK_KINDS:
        errors.append(f"{path} must be one of {sorted(VALID_TASK_KINDS)}")
    elif value == IMPLEMENTATION_TASK_KIND:
        errors.append(
            f"{path} cannot be {IMPLEMENTATION_TASK_KIND!r} in a read-only PLAN task"
        )


def _validate_task_execution_rules(
    execution_rules: Any, path: str, errors: list[str]
) -> None:
    if not isinstance(execution_rules, dict):
        errors.append(f"{path} must be an object")
        return
    expected = {
        "read_only": True,
        "write_authority": "none",
        "external_mutations": "forbidden",
        "pass_parent_transcript": False,
        "may_make_decisions": False,
        "may_author_contract": False,
        "may_spawn_agents": False,
    }
    for field, value in expected.items():
        if execution_rules.get(field) != value:
            errors.append(f"{path}.{field} must be exactly {value!r}")


def validate_direct_routing(
    record: dict[str, Any], config_path: Path | None = None
) -> dict[str, Any]:
    """Validate a minimal direct-handling routing record."""
    errors: list[str] = []
    warnings: list[str] = []
    _reject_forbidden_plan_authority(record, "plan", errors)
    if record.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        errors.append(f"schema_version must be exactly {SUPPORTED_SCHEMA_VERSION!r}")
    if record.get("envelope_type") != "routing-decision":
        errors.append("envelope_type must be 'routing-decision' for direct handling")
    if not valid_id(record.get("plan_id")):
        errors.append("plan_id has an invalid identifier")
    if not is_non_empty_string(record.get("goal")):
        errors.append("goal must be a non-empty string")
    routing = record.get("routing")
    if not isinstance(routing, dict):
        errors.append("routing must be an object")
        routing = {}
    if routing.get("decision") != "direct":
        errors.append("routing.decision must be 'direct'")
    _validate_integer(routing.get("estimated_files"), "routing.estimated_files", errors)
    _validate_integer(routing.get("estimated_tokens"), "routing.estimated_tokens", errors)
    _validate_boolean(
        routing.get("multiple_information_boundaries"),
        "routing.multiple_information_boundaries",
        errors,
    )
    if not is_non_empty_string(routing.get("basis")):
        errors.append("routing.basis must be a non-empty string")
    economics = validate_economics(
        routing.get("economics"), "routing.economics", errors, require_benefit=False
    )
    research = validate_external_research(
        record.get("external_research"),
        "external_research",
        errors,
        direct=True,
    )
    if choose_routing(economics) != "direct":
        warnings.append("direct routing was selected despite positive delegation economics")
    if "tasks" in record or "sources" in record:
        errors.append("direct routing records must not contain task or source packet data")
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "routing_decision": "direct",
            "external_research_decision": research.get("decision"),
            "external_research_status": research.get("status"),
        },
    }


def validate_micro_task(
    envelope: dict[str, Any], config_path: Path | None = None
) -> dict[str, Any]:
    """Validate the minimal one-task PLAN envelope without a batch plan."""
    errors: list[str] = []
    warnings: list[str] = []
    _reject_forbidden_plan_authority(envelope, "plan", errors)
    required = {
        "schema_version",
        "envelope_type",
        "plan_id",
        "task_id",
        "task_kind",
        "goal",
        "objective",
        "query",
        "sources",
        "deliverable",
        "stop_conditions",
        "evidence_required",
        "allowed_expansion",
        "budget",
        "economics",
        "plan_task_policy",
        "plan_task_authorization",
        "model_override",
        "external_research",
        "response_contract",
        "execution_rules",
    }
    missing = sorted(required - set(envelope))
    if missing:
        errors.append(f"micro-task envelope is missing fields: {', '.join(missing)}")
    if envelope.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        errors.append(f"schema_version must be exactly {SUPPORTED_SCHEMA_VERSION!r}")
    if envelope.get("envelope_type") != "micro-task":
        errors.append("envelope_type must be 'micro-task'")
    for field in ("plan_id", "task_id"):
        if not valid_id(envelope.get(field)):
            errors.append(f"{field} has an invalid identifier")
    _validate_task_kind(envelope.get("task_kind"), "task_kind", errors)
    for field in ("goal", "objective", "query", "deliverable"):
        if not is_non_empty_string(envelope.get(field)):
            errors.append(f"{field} must be a non-empty string")
    validate_string_list(
        envelope.get("stop_conditions", []), "stop_conditions", errors, allow_empty=False
    )
    if envelope.get("evidence_required") is not True:
        errors.append("evidence_required must be true for an Evidence Task")
    web_research = None
    if "web_research" in envelope:
        web_research = _validate_web_research_request(
            envelope.get("web_research"),
            "web_research",
            errors,
            task_kind=envelope.get("task_kind"),
        )
    sources = _validate_source_descriptors(
        envelope.get("sources"),
        "sources",
        errors,
        require_one=not (
            isinstance(web_research, dict)
            and web_research.get("requested") is True
        ),
    )
    research = validate_external_research(
        envelope.get("external_research"),
        "external_research",
        errors,
        source_map=sources,
        pending_request=web_research,
        pending_task_kind=envelope.get("task_kind"),
    )
    economics = validate_economics(
        envelope.get("economics"), "economics", errors, require_benefit=True
    )
    policy = _validate_plan_task_policy(
        envelope.get("plan_task_policy"), "plan_task_policy", errors
    )
    _validate_plan_task_authorization(
        envelope.get("plan_task_authorization"),
        "plan_task_authorization",
        errors,
        expected_task_count=1,
        policy=policy,
    )
    _validate_model_override(
        envelope.get("model_override"), "model_override", errors
    )
    _validate_expansion_policy(envelope.get("allowed_expansion"), "allowed_expansion", errors)
    budget = envelope.get("budget")
    if not isinstance(budget, dict):
        errors.append("budget must be an object")
        budget = {}
    for field in ("estimated_input_tokens", "max_input_tokens", "max_result_tokens"):
        _validate_integer(budget.get(field), f"budget.{field}", errors, minimum=1)
    estimated_input = budget.get("estimated_input_tokens")
    max_input = budget.get("max_input_tokens")
    if isinstance(estimated_input, int) and isinstance(max_input, int):
        if estimated_input > max_input:
            errors.append("budget.estimated_input_tokens must not exceed budget.max_input_tokens")
        if estimated_input > PLAN_TASK_MAX_INPUT_TOKENS_PER_ROUND:
            errors.append(
                "budget.estimated_input_tokens must not exceed the PLAN-task policy ceiling"
            )
    source_tokens = sum(
        source.get("estimated_tokens", 0)
        for source in sources.values()
        if isinstance(source.get("estimated_tokens"), int)
    )
    if isinstance(estimated_input, int) and estimated_input < source_tokens:
        errors.append("budget.estimated_input_tokens must cover assigned source estimates")
    if isinstance(economics.get("delegated_input_tokens"), int) and isinstance(
        estimated_input, int
    ) and economics["delegated_input_tokens"] != estimated_input:
        errors.append("economics.delegated_input_tokens must equal budget.estimated_input_tokens")
    if (
        isinstance(estimated_input, int)
        and isinstance(envelope.get("allowed_expansion"), dict)
        and isinstance(envelope["allowed_expansion"].get("max_additional_tokens"), int)
        and estimated_input + envelope["allowed_expansion"]["max_additional_tokens"]
        > PLAN_TASK_MAX_INPUT_TOKENS_PER_ROUND
    ):
        errors.append("micro-task worst-case input exceeds the PLAN-task policy ceiling")
    _validate_response_contract(envelope.get("response_contract"), "response_contract", errors)
    _validate_task_execution_rules(
        envelope.get("execution_rules"), "execution_rules", errors
    )
    try:
        effective_config = load_effective_config(config_path)
    except (TypeError, ValueError) as exc:
        errors.append(str(exc))
    else:
        configured_policy = effective_config.get("plan_task_policy")
        if isinstance(configured_policy, dict) and policy != configured_policy:
            errors.append(
                "plan_task_policy must exactly match the effective configuration policy"
            )
        configured_research_policy = effective_config.get("external_research_policy")
        errors.extend(
            validate_external_research_policy(
                configured_research_policy, "effective external_research_policy"
            )
        )
    if (
        research.get("status") == "satisfied"
        and research.get("mode") in {"cached-indexed", "live"}
        and (not isinstance(web_research, dict) or web_research.get("requested") is not True)
    ):
        errors.append(
            "satisfied managed research must be routed through an explicit web_research request"
        )
    if isinstance(web_research, dict) and web_research.get("requested") is True:
        _validate_request_against_research_gate(
            research,
            web_research,
            envelope.get("task_kind"),
            "web_research",
            errors,
        )
        requested_sources = set(research.get("source_ids", []))
        assigned_sources = set(sources)
        if research.get("status") == "satisfied" and not requested_sources.intersection(
            assigned_sources
        ):
            errors.append(
                "web_research task must receive at least one declared research source"
            )
    if choose_routing(economics) != "micro":
        errors.append("micro-task economics and task count do not justify micro delegation")
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": {
            "routing_decision": "micro",
            "task_count": 1,
            "source_count": len(sources),
            "estimated_input_tokens": budget.get("estimated_input_tokens"),
            "estimated_result_tokens": economics.get("estimated_result_tokens"),
            "external_research_decision": research.get("decision"),
            "external_research_status": research.get("status"),
        },
    }


def validate_string_list(
    value: Any,
    path: str,
    errors: list[str],
    *,
    allow_empty: bool = True,
) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{path} must be an array of strings")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not is_non_empty_string(item):
            errors.append(f"{path}[{index}] must be a non-empty string")
        else:
            result.append(item)
    if not allow_empty and not result:
        errors.append(f"{path} must contain at least one item")
    return result


def validate_selector(selector: Any, path: str, errors: list[str]) -> None:
    if not isinstance(selector, dict):
        errors.append(f"{path} must be an object")
        return
    selector_type = selector.get("type")
    if selector_type not in VALID_SELECTOR_TYPES:
        errors.append(
            f"{path}.type must be one of {sorted(VALID_SELECTOR_TYPES)}, got {selector_type!r}"
        )
        return

    if selector_type in {"lines", "pages"}:
        start = selector.get("start")
        end = selector.get("end")
        if not isinstance(start, int) or isinstance(start, bool) or start < 1:
            errors.append(f"{path}.start must be an integer >= 1")
        if not isinstance(end, int) or isinstance(end, bool) or end < 1:
            errors.append(f"{path}.end must be an integer >= 1")
        if isinstance(start, int) and isinstance(end, int) and end < start:
            errors.append(f"{path}.end must be >= {path}.start")
    elif selector_type == "symbol" and not is_non_empty_string(selector.get("name")):
        errors.append(f"{path}.name must be a non-empty string")
    elif selector_type == "section" and not is_non_empty_string(selector.get("heading")):
        errors.append(f"{path}.heading must be a non-empty string")
    elif selector_type == "object" and not is_non_empty_string(selector.get("key")):
        errors.append(f"{path}.key must be a non-empty string")
    elif selector_type == "query":
        if not is_non_empty_string(selector.get("query")):
            errors.append(f"{path}.query must be a non-empty string")
        top_k = selector.get("top_k")
        if top_k is not None and (
            not isinstance(top_k, int) or isinstance(top_k, bool) or top_k < 1
        ):
            errors.append(f"{path}.top_k must be an integer >= 1 when present")


def detect_dependency_cycle(task_dependencies: dict[str, list[str]]) -> list[str] | None:
    state: dict[str, int] = {task_id: 0 for task_id in task_dependencies}
    stack: list[str] = []

    def visit(task_id: str) -> list[str] | None:
        state[task_id] = 1
        stack.append(task_id)
        for dependency in task_dependencies.get(task_id, []):
            if dependency not in state:
                continue
            if state[dependency] == 0:
                cycle = visit(dependency)
                if cycle:
                    return cycle
            elif state[dependency] == 1:
                start = stack.index(dependency)
                return stack[start:] + [dependency]
        stack.pop()
        state[task_id] = 2
        return None

    for task_id in task_dependencies:
        if state[task_id] == 0:
            cycle = visit(task_id)
            if cycle:
                return cycle
    return None


def facts_for_sources(facts: Iterable[dict[str, Any]], source_ids: set[str]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for fact in facts:
        provenance = fact.get("provenance", [])
        if fact.get("always_share") is True or not provenance or source_ids.intersection(provenance):
            selected.append(fact)
    return selected


def validate_plan(
    plan: dict[str, Any], config_path: Path | None = None
) -> dict[str, Any]:
    """Validate a direct record, micro-task envelope, or batch PLAN.

    Mode-profile budget values are maximum limits, so a plan may select lower
    values. The PLAN-task authorization token ceiling is the actual approved
    ceiling and must cover the computed worst-case dispatch without exceeding
    either the selected budget or the pre-authorized per-round policy.
    """
    envelope_type = plan.get("envelope_type")
    routing_value = plan.get("routing")
    routing_decision = (
        routing_value.get("decision") if isinstance(routing_value, dict) else None
    )
    if envelope_type == "routing-decision" or routing_decision == "direct":
        return validate_direct_routing(plan, config_path)
    if envelope_type == "micro-task" or routing_decision == "micro":
        return validate_micro_task(plan, config_path)

    errors: list[str] = []
    warnings: list[str] = []
    _reject_forbidden_plan_authority(plan, "plan", errors)

    missing = sorted(REQUIRED_TOP_LEVEL_FIELDS - set(plan))
    if missing:
        errors.append(f"missing required top-level fields: {', '.join(missing)}")

    if plan.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        errors.append(
            f"schema_version must be exactly {SUPPORTED_SCHEMA_VERSION!r}"
        )
    if plan.get("envelope_type") != "batch-plan":
        errors.append("envelope_type must be 'batch-plan' for a batch PLAN")
    if not valid_id(plan.get("plan_id")):
        errors.append(
            "plan_id must start with an alphanumeric character and contain only letters, digits, '.', '_' or '-'"
        )
    if not is_non_empty_string(plan.get("goal")):
        errors.append("goal must be a non-empty string")
    mode = plan.get("mode")
    if mode not in VALID_MODES:
        errors.append(f"mode must be one of {sorted(VALID_MODES)}, got {mode!r}")

    effective_config: dict[str, Any] = {}
    resolved_config_path = config_path or default_config_path()
    try:
        effective_config = load_effective_config(resolved_config_path)
    except ValueError as exc:
        errors.append(str(exc))

    configuration = plan.get("configuration")
    if not isinstance(configuration, dict):
        errors.append("configuration must be an object")
        configuration = {}
    configuration_source = configuration.get("source")
    if not is_non_empty_string(configuration_source):
        errors.append("configuration.source must be a non-empty string")
    elif config_path is None and configuration_source.replace("\\", "/") != DEFAULT_CONFIG_RELATIVE_PATH.as_posix():
        errors.append(
            "configuration.source must identify assets/context-routing/default-config.yaml"
        )
    configuration_id = configuration.get("id")
    if not valid_id(configuration_id):
        errors.append("configuration.id has an invalid identifier")
    configuration_revision = configuration.get("revision")
    if (
        not isinstance(configuration_revision, int)
        or isinstance(configuration_revision, bool)
        or configuration_revision < 1
    ):
        errors.append("configuration.revision must be an integer >= 1")
    configuration_digest = configuration.get("digest")
    if not is_non_empty_string(configuration_digest):
        errors.append("configuration.digest must be a non-empty string")
    elif not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", configuration_digest):
        errors.append("configuration.digest must use the sha256:<64-hex-digits> format")
    elif resolved_config_path.is_file():
        try:
            expected_digest = f"sha256:{sha256_text_normalized(resolved_config_path)}"
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if configuration_digest != expected_digest:
                errors.append(
                    "configuration.digest does not match the effective configuration source"
                )

    if effective_config:
        if configuration.get("revision") != effective_config.get("config_revision"):
            errors.append(
                "configuration.revision does not match the effective configuration source"
            )
        if not valid_id(effective_config.get("config_id")):
            errors.append("effective configuration config_id is invalid")
        elif configuration.get("id") != effective_config.get("config_id"):
            errors.append(
                "configuration.id does not match the effective configuration source"
            )

    routing = plan.get("routing")
    if not isinstance(routing, dict):
        errors.append("routing must be an object")
        routing = {}
    routing_decision = routing.get("decision")
    if routing_decision != "batch":
        errors.append("routing.decision must be 'batch' for a batch PLAN task set")
    estimated_files = routing.get("estimated_files")
    if (
        not isinstance(estimated_files, int)
        or isinstance(estimated_files, bool)
        or estimated_files < 0
    ):
        errors.append("routing.estimated_files must be an integer >= 0")
    estimated_tokens = routing.get("estimated_tokens")
    if (
        not isinstance(estimated_tokens, int)
        or isinstance(estimated_tokens, bool)
        or estimated_tokens < 0
    ):
        errors.append("routing.estimated_tokens must be an integer >= 0")
    if not isinstance(routing.get("multiple_information_boundaries"), bool):
        errors.append("routing.multiple_information_boundaries must be a boolean")
    if not is_non_empty_string(routing.get("basis")):
        errors.append("routing.basis must be a non-empty string")
    economics = validate_economics(
        routing.get("economics"), "routing.economics", errors, require_benefit=True
    )

    assumptions = plan.get("assumptions", [])
    assumptions_list = validate_string_list(assumptions, "assumptions", errors)

    budget = plan.get("budget")
    if not isinstance(budget, dict):
        errors.append("budget must be an object")
        budget = {}
    else:
        missing_budget = sorted(REQUIRED_BUDGET_FIELDS - set(budget))
        if missing_budget:
            errors.append(f"budget is missing fields: {', '.join(missing_budget)}")

    positive_integer_fields = {
        "max_subagents",
        "max_input_tokens_per_task",
        "max_total_dispatched_tokens",
    }
    for field in positive_integer_fields:
        value = budget.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            errors.append(f"budget.{field} must be an integer >= 1")

    shared_limit = budget.get("max_shared_source_tokens_per_task")
    if not isinstance(shared_limit, int) or isinstance(shared_limit, bool) or shared_limit < 0:
        errors.append("budget.max_shared_source_tokens_per_task must be an integer >= 0")

    overlap_limit = budget.get("max_accidental_overlap_ratio")
    if not isinstance(overlap_limit, (int, float)) or isinstance(overlap_limit, bool):
        errors.append("budget.max_accidental_overlap_ratio must be a number from 0 to 1")
    elif not 0 <= float(overlap_limit) <= 1:
        errors.append("budget.max_accidental_overlap_ratio must be between 0 and 1")

    mode_profiles = effective_config.get("mode_profiles", {})
    effective_profile = (
        mode_profiles.get(mode) if isinstance(mode_profiles, dict) else None
    )
    if isinstance(effective_profile, dict) and mode in VALID_MODES:
        for field in REQUIRED_BUDGET_FIELDS:
            plan_value = budget.get(field)
            profile_value = effective_profile.get(field)
            if plan_value is None:
                continue
            if not isinstance(plan_value, (int, float)) or isinstance(plan_value, bool):
                continue
            if not isinstance(profile_value, (int, float)) or isinstance(
                profile_value, bool
            ):
                continue
            if float(plan_value) > float(profile_value):
                errors.append(
                    f"budget.{field} value {plan_value} exceeds the effective "
                    f"{mode!r} configuration profile limit ({profile_value})"
                )

    shared_context = plan.get("shared_context")
    if not isinstance(shared_context, dict):
        errors.append("shared_context must be an object")
        shared_context = {}
    else:
        missing_shared = sorted(REQUIRED_SHARED_CONTEXT_FIELDS - set(shared_context))
        if missing_shared:
            errors.append(
                f"shared_context is missing fields: {', '.join(missing_shared)}"
            )

    constraints = validate_string_list(
        shared_context.get("constraints", []), "shared_context.constraints", errors
    )
    shared_source_ids = validate_string_list(
        shared_context.get("source_ids", []), "shared_context.source_ids", errors
    )
    if len(set(shared_source_ids)) != len(shared_source_ids):
        errors.append("shared_context.source_ids contains duplicates")

    facts_value = shared_context.get("facts", [])
    if not isinstance(facts_value, list):
        errors.append("shared_context.facts must be an array")
        facts_value = []
    facts: list[dict[str, Any]] = []
    fact_ids: set[str] = set()
    for index, fact in enumerate(facts_value):
        path = f"shared_context.facts[{index}]"
        if not isinstance(fact, dict):
            errors.append(f"{path} must be an object")
            continue
        fact_id = fact.get("id")
        if not valid_id(fact_id):
            errors.append(f"{path}.id has an invalid identifier")
        elif fact_id in fact_ids:
            errors.append(f"duplicate fact id: {fact_id}")
        else:
            fact_ids.add(fact_id)
        if not is_non_empty_string(fact.get("statement")):
            errors.append(f"{path}.statement must be a non-empty string")
        validate_string_list(fact.get("provenance", []), f"{path}.provenance", errors)
        confidence = fact.get("confidence")
        if confidence not in VALID_CONFIDENCE:
            errors.append(
                f"{path}.confidence must be one of {sorted(VALID_CONFIDENCE)}"
            )
        if "always_share" in fact and not isinstance(fact["always_share"], bool):
            errors.append(f"{path}.always_share must be a boolean when present")
        facts.append(fact)

    sources_value = plan.get("sources")
    if not isinstance(sources_value, list):
        errors.append("sources must be an array")
        sources_value = []
    sources: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(sources_value):
        path = f"sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{path} must be an object")
            continue
        source_id = source.get("id")
        if not valid_id(source_id):
            errors.append(f"{path}.id has an invalid identifier")
            continue
        if source_id in sources:
            errors.append(f"duplicate source id: {source_id}")
            continue
        if not is_non_empty_string(source.get("uri")):
            errors.append(f"{path}.uri must be a non-empty string")
        validate_selector(source.get("selector"), f"{path}.selector", errors)
        estimated_tokens = source.get("estimated_tokens")
        if (
            not isinstance(estimated_tokens, int)
            or isinstance(estimated_tokens, bool)
            or estimated_tokens < 1
        ):
            errors.append(f"{path}.estimated_tokens must be an integer >= 1")
        if not is_non_empty_string(source.get("purpose")):
            errors.append(f"{path}.purpose must be a non-empty string")
        _validate_source_metadata(source, path, errors)
        selector_value = source.get("selector")
        selector_type = (
            selector_value.get("type") if isinstance(selector_value, dict) else None
        )
        if selector_type == "whole" and isinstance(
            estimated_tokens, int
        ) and not isinstance(estimated_tokens, bool) and estimated_tokens > 4000:
            warnings.append(
                f"source {source_id} selects a whole source estimated at {estimated_tokens} tokens; consider a narrower selector"
            )
        sources[source_id] = source

    source_id_set = set(sources)
    for source_id in shared_source_ids:
        if source_id not in source_id_set:
            errors.append(f"shared_context references unknown source id: {source_id}")

    for index, fact in enumerate(facts):
        for source_id in fact.get("provenance", []):
            if source_id not in source_id_set:
                errors.append(
                    f"shared_context.facts[{index}] references unknown provenance source: {source_id}"
                )

    tasks_value = plan.get("tasks")
    if not isinstance(tasks_value, list):
        errors.append("tasks must be an array")
        tasks_value = []
    if not tasks_value:
        errors.append("tasks must contain at least one task")

    tasks: dict[str, dict[str, Any]] = {}
    task_dependencies: dict[str, list[str]] = {}
    task_source_ids: dict[str, list[str]] = {}
    for index, task in enumerate(tasks_value):
        path = f"tasks[{index}]"
        if not isinstance(task, dict):
            errors.append(f"{path} must be an object")
            continue
        task_id = task.get("id")
        if not valid_id(task_id):
            errors.append(f"{path}.id has an invalid identifier")
            continue
        if task_id in tasks:
            errors.append(f"duplicate task id: {task_id}")
            continue
        tasks[task_id] = task

        missing_task_fields = sorted(
            REQUIRED_TASK_FIELDS - set(task)
            - {"capabilities", "inherit_shared_sources"}
        )
        if missing_task_fields:
            errors.append(
                f"{path} is missing required fields: {', '.join(missing_task_fields)}"
            )

        _validate_task_kind(task.get("task_kind"), f"{path}.task_kind", errors)
        if "web_research" in task:
            _validate_web_research_request(
                task.get("web_research"),
                f"{path}.web_research",
                errors,
                task_kind=task.get("task_kind"),
            )
        if not is_non_empty_string(task.get("agent_role")):
            errors.append(f"{path}.agent_role must be a non-empty string")
        if not is_non_empty_string(task.get("objective")):
            errors.append(f"{path}.objective must be a non-empty string")
        dependencies = validate_string_list(
            task.get("dependencies", []), f"{path}.dependencies", errors
        )
        if len(set(dependencies)) != len(dependencies):
            errors.append(f"{path}.dependencies contains duplicates")
        if task_id in dependencies:
            errors.append(f"{path} cannot depend on itself")
        task_dependencies[task_id] = dependencies

        scoped_sources = validate_string_list(
            task.get("source_ids", []), f"{path}.source_ids", errors
        )
        if len(set(scoped_sources)) != len(scoped_sources):
            errors.append(f"{path}.source_ids contains duplicates")
        task_source_ids[task_id] = scoped_sources

        validate_string_list(task.get("questions", []), f"{path}.questions", errors)
        if not is_non_empty_string(task.get("deliverable")):
            errors.append(f"{path}.deliverable must be a non-empty string")
        if not isinstance(task.get("evidence_required"), bool):
            errors.append(f"{path}.evidence_required must be a boolean")
        if not isinstance(task.get("intentional_overlap"), bool):
            errors.append(f"{path}.intentional_overlap must be a boolean")
        if "inherit_shared_sources" in task and not isinstance(
            task.get("inherit_shared_sources"), bool
        ):
            errors.append(f"{path}.inherit_shared_sources must be a boolean when present")
        validate_string_list(
            task.get("capabilities", []), f"{path}.capabilities", errors
        )
        validate_string_list(
            task.get("stop_conditions", []), f"{path}.stop_conditions", errors
        )

        _validate_expansion_policy(task.get("allowed_expansion"), f"{path}.allowed_expansion", errors)

    task_id_set = set(tasks)
    for task_id, dependencies in task_dependencies.items():
        for dependency in dependencies:
            if dependency not in task_id_set:
                errors.append(f"task {task_id} depends on unknown task id: {dependency}")
    for task_id, task in tasks.items():
        if task.get("inherit_shared_sources") is False and not shared_source_ids:
            warnings.append(
                f"task {task_id} sets inherit_shared_sources=false but the plan has no shared sources"
            )
    for task_id, scoped_sources in task_source_ids.items():
        for source_id in scoped_sources:
            if source_id not in source_id_set:
                errors.append(f"task {task_id} references unknown source id: {source_id}")
        if not scoped_sources and not shared_source_ids and not task_dependencies.get(task_id):
            warnings.append(
                f"task {task_id} has no source scope and no dependencies; verify that it is self-contained"
            )

    cycle = detect_dependency_cycle(task_dependencies)
    if cycle:
        errors.append(f"task dependency cycle detected: {' -> '.join(cycle)}")

    pending_requests = [
        (task.get("web_research"), task.get("task_kind"))
        for task in tasks.values()
        if isinstance(task.get("web_research"), dict)
        and task["web_research"].get("requested") is True
    ]
    research = validate_external_research(
        plan.get("external_research"),
        "external_research",
        errors,
        source_map=sources,
        pending_request=pending_requests,
    )

    web_research_tasks = [
        task
        for task in tasks.values()
        if isinstance(task.get("web_research"), dict)
        and task["web_research"].get("requested") is True
    ]
    if (
        research.get("status") == "satisfied"
        and research.get("mode") in {"cached-indexed", "live"}
        and not web_research_tasks
    ):
        errors.append(
            "satisfied managed research must be routed through a requirement-research or dependency-check task"
        )
    for task in web_research_tasks:
        if task.get("task_kind") not in VALID_WEB_RESEARCH_TASK_KINDS:
            errors.append(
                f"task {task.get('id')} cannot receive managed web research; use requirement-research or dependency-check"
            )
        request = task.get("web_research", {})
        _validate_request_against_research_gate(
            research,
            request,
            task.get("task_kind"),
            f"tasks[{task.get('id')}].web_research",
            errors,
        )

    if choose_routing(
        economics,
        task_count=len(tasks),
        multiple_information_boundaries=routing.get("multiple_information_boundaries")
        is True,
    ) != "batch":
        errors.append(
            "batch routing requires independently describable tasks with positive "
            "delegation economics and multiple tasks or information boundaries"
        )

    policy = _validate_plan_task_policy(
        plan.get("plan_task_policy"), "plan_task_policy", errors
    )
    authorization = _validate_plan_task_authorization(
        plan.get("plan_task_authorization"),
        "plan_task_authorization",
        errors,
        expected_task_count=len(tasks_value),
        policy=policy,
    )
    token_ceiling = authorization.get("token_ceiling")

    configured_policy = effective_config.get("plan_task_policy", {})
    if isinstance(configured_policy, dict):
        _validate_plan_task_policy(
            configured_policy, "effective plan_task_policy", errors
        )
        if policy and policy != configured_policy:
            errors.append(
                "plan_task_policy must exactly match the effective configuration policy"
            )
    configured_routing = effective_config.get("routing_policy", {})
    if not isinstance(configured_routing, dict):
        errors.append("effective routing_policy must be an object")
    else:
        configured_decisions = configured_routing.get("allowed_decisions")
        if (
            not isinstance(configured_decisions, list)
            or any(not isinstance(item, str) for item in configured_decisions)
            or set(configured_decisions) != VALID_ROUTING_DECISIONS
        ):
            errors.append("effective routing policy decisions do not match the validator")
        if configured_routing.get("decision_basis") != "context-economics":
            errors.append("effective routing policy must use context-economics")
        _validate_integer(
            configured_routing.get("coordination_overhead_tokens"),
            "effective routing_policy.coordination_overhead_tokens",
            errors,
        )
    scout_policy = effective_config.get("scout_policy", {})
    if isinstance(scout_policy, dict):
        if scout_policy.get("allowed_expansion_modes") != sorted(VALID_EXPANSION_MODES):
            errors.append(
                "effective scout policy expansion modes do not match the validator"
            )
        if scout_policy.get("sandbox_mode") != "read-only":
            errors.append("effective scout policy must require a read-only sandbox")
        if scout_policy.get("planner_approval_required_for_request") is not True:
            errors.append(
                "effective scout policy must require Planner approval for request expansion"
            )
        if scout_policy.get("response_schema_version") != SUPPORTED_SCHEMA_VERSION:
            errors.append(
                "effective scout policy response schema must match the PLAN schema version"
            )
        configured_task_kinds = scout_policy.get("task_kinds")
        if (
            not isinstance(configured_task_kinds, list)
            or any(not isinstance(item, str) for item in configured_task_kinds)
            or set(configured_task_kinds) != READ_ONLY_TASK_KINDS
        ):
            errors.append(
                "effective scout policy task kinds do not match the read-only task kinds"
            )

    merge = plan.get("merge")
    if not isinstance(merge, dict):
        errors.append("merge must be an object")
        merge = {}
    else:
        missing_merge = sorted(REQUIRED_MERGE_FIELDS - set(merge))
        if missing_merge:
            errors.append(f"merge is missing fields: {', '.join(missing_merge)}")
    if not is_non_empty_string(merge.get("strategy")):
        errors.append("merge.strategy must be a non-empty string")
    if not is_non_empty_string(merge.get("conflict_policy")):
        errors.append("merge.conflict_policy must be a non-empty string")
    validate_string_list(merge.get("final_checks", []), "merge.final_checks", errors)

    source_tokens = {
        source_id: source.get("estimated_tokens", 0)
        for source_id, source in sources.items()
        if isinstance(source.get("estimated_tokens"), int)
    }
    shared_source_set = set(shared_source_ids)
    shared_source_tokens = sum(source_tokens.get(source_id, 0) for source_id in shared_source_set)

    task_metrics: dict[str, dict[str, Any]] = {}
    reader_counts: Counter[str] = Counter()
    non_intentional_reader_counts: Counter[str] = Counter()
    worst_case_expansion: dict[str, int] = {}
    total_dispatched_source_tokens = 0
    total_estimated_input_tokens = 0

    shared_base_context = {
        "goal": plan.get("goal", ""),
        "assumptions": assumptions_list,
        "constraints": constraints,
    }

    for task_id, task in tasks.items():
        inherited_shared_source_ids = (
            shared_source_set if task.get("inherit_shared_sources", True) else set()
        )
        assigned_source_ids = inherited_shared_source_ids.union(
            task_source_ids.get(task_id, [])
        )
        assigned_source_tokens = sum(
            source_tokens.get(source_id, 0) for source_id in assigned_source_ids
        )
        total_dispatched_source_tokens += assigned_source_tokens

        for source_id in assigned_source_ids:
            reader_counts[source_id] += 1
            if (
                source_id not in inherited_shared_source_ids
                and task.get("intentional_overlap") is not True
            ):
                non_intentional_reader_counts[source_id] += 1

        relevant_facts = facts_for_sources(facts, assigned_source_ids)
        packet_text: dict[str, Any] = {
            "shared": shared_base_context,
            "facts": relevant_facts,
            "agent_role": task.get("agent_role", ""),
            "objective": task.get("objective", ""),
            "dependencies": task_dependencies.get(task_id, []),
            "questions": task.get("questions", []),
            "deliverable": task.get("deliverable", ""),
            "capabilities": task.get("capabilities", []),
            "stop_conditions": task.get("stop_conditions", []),
            "allowed_expansion": task.get("allowed_expansion", {}),
        }
        consumes_external_evidence = any(
            sources[source_id].get("source_kind") in EXTERNAL_SOURCE_KINDS
            for source_id in assigned_source_ids
        )
        task_research = task.get("web_research")
        if (
            isinstance(task_research, dict)
            and task_research.get("requested") is True
        ) or consumes_external_evidence:
            packet_text["external_research"] = research
        if "web_research" in task:
            packet_text["web_research"] = task_research
        estimated_packet_tokens = 180 + approximate_tokens(packet_text)
        estimated_input_tokens = assigned_source_tokens + estimated_packet_tokens
        total_estimated_input_tokens += estimated_input_tokens

        expansion = task.get("allowed_expansion") or {}
        expansion_tokens = expansion.get("max_additional_tokens")
        if isinstance(expansion_tokens, int) and not isinstance(expansion_tokens, bool):
            worst_case_expansion[task_id] = expansion_tokens

        task_metrics[task_id] = {
            "assigned_source_ids": sorted(assigned_source_ids),
            "estimated_source_tokens": assigned_source_tokens,
            "estimated_packet_tokens": estimated_packet_tokens,
            "estimated_input_tokens": estimated_input_tokens,
        }

    raw_duplicate_source_tokens = sum(
        source_tokens.get(source_id, 0) * max(0, readers - 1)
        for source_id, readers in reader_counts.items()
    )
    accidental_duplicate_source_tokens = sum(
        source_tokens.get(source_id, 0) * max(0, readers - 1)
        for source_id, readers in non_intentional_reader_counts.items()
    )
    raw_overlap_ratio = (
        raw_duplicate_source_tokens / total_dispatched_source_tokens
        if total_dispatched_source_tokens
        else 0.0
    )
    accidental_overlap_ratio = (
        accidental_duplicate_source_tokens / total_dispatched_source_tokens
        if total_dispatched_source_tokens
        else 0.0
    )
    total_expansion_allowance = sum(worst_case_expansion.values())
    worst_case_total_input_tokens = (
        total_estimated_input_tokens + total_expansion_allowance
    )

    if (
        isinstance(economics.get("delegated_input_tokens"), int)
        and economics.get("delegated_input_tokens") != total_estimated_input_tokens
    ):
        errors.append(
            "routing.economics.delegated_input_tokens must equal the computed batch input estimate"
        )
    if economics.get("estimated_result_tokens", 0) <= 0:
        errors.append(
            "routing.economics.estimated_result_tokens must be greater than 0 for batch delegation"
        )

    if isinstance(budget.get("max_subagents"), int) and len(tasks) > budget["max_subagents"]:
        errors.append(
            f"task count {len(tasks)} exceeds budget.max_subagents={budget['max_subagents']}"
        )

    max_input = budget.get("max_input_tokens_per_task")
    if isinstance(max_input, int):
        for task_id, metrics in task_metrics.items():
            if metrics["estimated_input_tokens"] > max_input:
                errors.append(
                    f"task {task_id} estimated input {metrics['estimated_input_tokens']} exceeds per-task budget {max_input}"
                )
            worst_case = metrics["estimated_input_tokens"] + worst_case_expansion.get(
                task_id, 0
            )
            if worst_case > max_input:
                warnings.append(
                    f"task {task_id} worst-case input {worst_case} "
                    f"(including expansion allowance) exceeds per-task budget {max_input}"
                )

    max_total = budget.get("max_total_dispatched_tokens")
    if isinstance(max_total, int) and worst_case_total_input_tokens > max_total:
        errors.append(
            f"worst-case total dispatched input {worst_case_total_input_tokens} "
            f"(including expansion allowances) exceeds budget {max_total}"
        )
    if (
        isinstance(token_ceiling, int)
        and not isinstance(token_ceiling, bool)
        and worst_case_total_input_tokens > token_ceiling
    ):
        errors.append(
            "plan_task_authorization.token_ceiling is below the worst-case "
            "dispatched input including expansion allowances"
        )

    policy_ceiling = policy.get("max_estimated_input_tokens_per_round")
    if (
        isinstance(policy_ceiling, int)
        and worst_case_total_input_tokens > policy_ceiling
    ):
        errors.append(
            "worst-case PLAN input exceeds the pre-authorized per-round policy "
            f"ceiling {policy_ceiling}"
        )

    max_concurrent = policy.get("max_concurrent_tasks")
    dispatch_layers: list[list[str]] = []
    remaining = set(tasks)
    completed: set[str] = set()
    while remaining:
        ready = sorted(
            task_id
            for task_id in remaining
            if set(task_dependencies.get(task_id, [])).issubset(completed)
        )
        if not ready:
            break
        dispatch_layers.append(ready)
        completed.update(ready)
        remaining.difference_update(ready)
    if isinstance(max_concurrent, int) and any(
        len(layer) > max_concurrent for layer in dispatch_layers
    ):
        errors.append(
            "a PLAN dispatch layer exceeds the pre-authorized maximum concurrency "
            f"of {max_concurrent}"
        )

    if isinstance(shared_limit, int) and shared_source_tokens > shared_limit:
        errors.append(
            f"shared source tokens {shared_source_tokens} exceed per-task shared-source budget {shared_limit}"
        )

    if isinstance(overlap_limit, (int, float)) and accidental_overlap_ratio > float(
        overlap_limit
    ) + 1e-12:
        errors.append(
            "accidental overlap ratio "
            f"{accidental_overlap_ratio:.3f} exceeds budget {float(overlap_limit):.3f}"
        )

    if raw_overlap_ratio > 0.5:
        warnings.append(
            f"raw source overlap is high at {raw_overlap_ratio:.3f}; confirm that duplicated review is intentional"
        )

    overlap_sources = {
        source_id
        for source_id, readers in reader_counts.items()
        if readers > 1 and source_id not in shared_source_set
    }
    for task_id, task in tasks.items():
        if task.get("intentional_overlap") is True and not overlap_sources.intersection(
            task_source_ids.get(task_id, [])
        ):
            warnings.append(
                f"task {task_id} is marked intentional_overlap but shares no non-shared source with another task"
            )

    metrics = {
        "task_count": len(tasks),
        "source_count": len(sources),
        "shared_source_tokens_per_task": shared_source_tokens,
        "total_dispatched_source_tokens": total_dispatched_source_tokens,
        "raw_duplicate_source_tokens": raw_duplicate_source_tokens,
        "raw_overlap_ratio": round(raw_overlap_ratio, 6),
        "accidental_duplicate_source_tokens": accidental_duplicate_source_tokens,
        "accidental_overlap_ratio": round(accidental_overlap_ratio, 6),
        "estimated_total_input_tokens": total_estimated_input_tokens,
        "total_expansion_allowance": total_expansion_allowance,
        "worst_case_total_input_tokens": worst_case_total_input_tokens,
        "max_dispatch_concurrency": max((len(layer) for layer in dispatch_layers), default=0),
        "dispatch_layers": dispatch_layers,
        "per_task": task_metrics,
    }

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "metrics": metrics,
    }


def print_human_report(report: dict[str, Any]) -> None:
    status = "VALID" if report["valid"] else "INVALID"
    print(f"Plan status: {status}")

    if report["errors"]:
        print("\nErrors:")
        for item in report["errors"]:
            print(f"  - {item}")

    if report["warnings"]:
        print("\nWarnings:")
        for item in report["warnings"]:
            print(f"  - {item}")

    metrics = report["metrics"]
    if "routing_decision" in metrics:
        print(f"Routing decision: {metrics['routing_decision']}")
    if "estimated_total_input_tokens" not in metrics:
        if "estimated_input_tokens" in metrics:
            print(f"\nEstimated input tokens: {metrics['estimated_input_tokens']}")
        if "estimated_result_tokens" in metrics:
            print(f"Estimated result tokens: {metrics['estimated_result_tokens']}")
        return
    print("\nMetrics:")
    print(f"  Tasks: {metrics['task_count']}")
    print(f"  Sources: {metrics['source_count']}")
    print(
        "  Estimated total input tokens: "
        f"{metrics['estimated_total_input_tokens']}"
    )
    print(
        "  Worst-case total input tokens: "
        f"{metrics['worst_case_total_input_tokens']} "
        f"({metrics['total_expansion_allowance']} expansion allowance)"
    )
    print(
        "  Raw overlap ratio: "
        f"{metrics['raw_overlap_ratio']:.3f} "
        f"({metrics['raw_duplicate_source_tokens']} duplicate source tokens)"
    )
    print(
        "  Accidental overlap ratio: "
        f"{metrics['accidental_overlap_ratio']:.3f} "
        f"({metrics['accidental_duplicate_source_tokens']} duplicate source tokens)"
    )
    if "max_dispatch_concurrency" in metrics:
        print(f"  Maximum concurrent PLAN tasks: {metrics['max_dispatch_concurrency']}")
    for task_id, task_metrics in metrics["per_task"].items():
        print(
            f"  Task {task_id}: {task_metrics['estimated_input_tokens']} input tokens "
            f"({task_metrics['estimated_source_tokens']} source + "
            f"{task_metrics['estimated_packet_tokens']} packet)"
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "plan", type=Path, help="path to a direct, micro-task, or batch PLAN envelope"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="effective routing configuration (default: package default-config.yaml)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print a machine-readable validation report",
    )
    return parser.parse_args(argv)


def configure_output_streams() -> None:
    """Keep Unicode report output alive on cp936-style Windows consoles."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    configure_output_streams()
    try:
        plan = load_plan(args.plan)
    except (TypeError, ValueError) as exc:
        report = {"valid": False, "errors": [str(exc)], "warnings": [], "metrics": {}}
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"Plan status: INVALID\n\nErrors:\n  - {exc}")
        return 2

    report = validate_plan(plan, args.config)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_human_report(report)
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
