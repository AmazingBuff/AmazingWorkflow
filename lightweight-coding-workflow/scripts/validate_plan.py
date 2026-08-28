#!/usr/bin/env python3
"""Validate a context-routing scout orchestration plan.

The validator uses only the Python standard library. It checks the effective
configuration digest, explicit discovery authorization, structure, source
references, dependency cycles, token budgets, expansion policy, and accidental
source overlap. Token estimates are planning approximations, not billing
truth; the estimator weights CJK characters near one token per character and
other text near four characters per token.

The configuration digest is computed over the configuration content with line
endings normalized to LF, so the same configuration blob hashes identically
across CRLF (Windows autocrlf) and LF (Linux/macOS) checkouts.
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

SUPPORTED_SCHEMA_VERSION = "1.1"
DEFAULT_CONFIG_RELATIVE_PATH = Path("assets/context-routing/default-config.yaml")
VALID_MODES = {"lean", "balanced", "independent-review", "high-assurance"}
VALID_CONFIDENCE = {"confirmed", "inferred", "unverified"}
VALID_EXPANSION_MODES = {"deny", "request"}
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
    "schema_version",
    "plan_id",
    "goal",
    "mode",
    "configuration",
    "routing",
    "discovery_authorization",
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
        "routing_gate",
        "mode_profiles",
        "scout_policy",
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
    return config


def sha256_file(path: Path) -> str:
    """Return a stable SHA-256 digest for a UTF-8 or binary package file."""
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
    errors: list[str] = []
    warnings: list[str] = []

    missing = sorted(REQUIRED_TOP_LEVEL_FIELDS - set(plan))
    if missing:
        errors.append(f"missing required top-level fields: {', '.join(missing)}")

    if plan.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        errors.append(
            f"schema_version must be exactly {SUPPORTED_SCHEMA_VERSION!r}"
        )
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
    if routing_decision != "orchestrated":
        errors.append("routing.decision must be 'orchestrated' for a scout plan")
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
    routing_gate = effective_config.get("routing_gate", {})
    if isinstance(routing_gate, dict):
        max_files_direct = routing_gate.get("max_files_direct")
        max_tokens_direct = routing_gate.get("max_estimated_tokens_direct")
        if (
            isinstance(estimated_files, int)
            and isinstance(max_files_direct, int)
            and isinstance(estimated_tokens, int)
            and isinstance(max_tokens_direct, int)
        ):
            should_orchestrate = (
                estimated_files > max_files_direct
                or estimated_tokens > max_tokens_direct
                or routing.get("multiple_information_boundaries") is True
            )
            if not should_orchestrate:
                errors.append(
                    "routing.decision is orchestrated but the effective routing gate selects the fast lane"
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

        expansion = task.get("allowed_expansion")
        if not isinstance(expansion, dict):
            errors.append(f"{path}.allowed_expansion must be an object")
        else:
            expansion_mode = expansion.get("mode")
            if expansion_mode not in VALID_EXPANSION_MODES:
                errors.append(
                    f"{path}.allowed_expansion.mode must be one of {sorted(VALID_EXPANSION_MODES)}"
                )
            additional = expansion.get("max_additional_tokens")
            if (
                not isinstance(additional, int)
                or isinstance(additional, bool)
                or additional < 0
            ):
                errors.append(
                    f"{path}.allowed_expansion.max_additional_tokens must be an integer >= 0"
                )
            elif expansion_mode == "deny" and additional != 0:
                warnings.append(
                    f"task {task_id} uses expansion mode 'deny' but has a non-zero expansion budget"
                )
            elif expansion_mode == "request" and additional == 0:
                warnings.append(
                    f"task {task_id} permits expansion but has a zero expansion budget"
                )

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

    discovery_authorization = plan.get("discovery_authorization")
    if not isinstance(discovery_authorization, dict):
        errors.append("discovery_authorization must be an object")
        discovery_authorization = {}
    if discovery_authorization.get("authorized") is not True:
        errors.append("discovery_authorization.authorized must be true")
    scout_model = discovery_authorization.get("scout_model")
    if not is_non_empty_string(scout_model):
        errors.append("discovery_authorization.scout_model must be a non-empty string")
    packet_count = discovery_authorization.get("packet_count")
    if (
        not isinstance(packet_count, int)
        or isinstance(packet_count, bool)
        or packet_count < 1
    ):
        errors.append("discovery_authorization.packet_count must be an integer >= 1")
    elif packet_count != len(tasks_value):
        errors.append(
            "discovery_authorization.packet_count must equal the number of scout tasks"
        )
    token_ceiling = discovery_authorization.get("token_ceiling")
    if (
        not isinstance(token_ceiling, int)
        or isinstance(token_ceiling, bool)
        or token_ceiling < 1
    ):
        errors.append("discovery_authorization.token_ceiling must be an integer >= 1")
    elif isinstance(budget.get("max_total_dispatched_tokens"), int) and (
        token_ceiling > budget["max_total_dispatched_tokens"]
    ):
        errors.append(
            "discovery_authorization.token_ceiling must not exceed "
            "budget.max_total_dispatched_tokens"
        )

    scout_policy = effective_config.get("scout_policy", {})
    if isinstance(scout_policy, dict):
        configured_modes = scout_policy.get("allowed_expansion_modes")
        if configured_modes != sorted(VALID_EXPANSION_MODES):
            errors.append(
                "effective scout policy expansion modes do not match the validator"
            )
        if scout_policy.get("sandbox_mode") != "read-only":
            errors.append("effective scout policy must require a read-only sandbox")
        if scout_policy.get("planner_approval_required_for_request") is not True:
            errors.append(
                "effective scout policy must require Planner approval for request expansion"
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
        packet_text = {
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
            "discovery_authorization.token_ceiling is below the worst-case "
            "dispatched input including expansion allowances"
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
    for task_id, task_metrics in metrics["per_task"].items():
        print(
            f"  Task {task_id}: {task_metrics['estimated_input_tokens']} input tokens "
            f"({task_metrics['estimated_source_tokens']} source + "
            f"{task_metrics['estimated_packet_tokens']} packet)"
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="path to orchestration-plan.json")
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
