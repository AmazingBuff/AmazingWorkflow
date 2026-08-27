#!/usr/bin/env python3
"""Validate a context-efficient multi-agent orchestration plan.

The validator uses only the Python standard library. It checks structure,
source references, dependency cycles, token budgets, and accidental source
overlap. Token estimates are planning approximations, not billing truth.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

VALID_MODES = {"lean", "balanced", "independent-review", "high-assurance"}
VALID_CONFIDENCE = {"confirmed", "inferred", "unverified"}
VALID_EXPANSION_MODES = {"deny", "request", "bounded"}
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
REQUIRED_BUDGET_FIELDS = {
    "max_subagents",
    "max_input_tokens_per_task",
    "max_total_dispatched_tokens",
    "max_accidental_overlap_ratio",
    "max_shared_source_tokens_per_task",
}


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
        raise ValueError("plan root must be a JSON object")
    return data


def approximate_tokens(value: Any) -> int:
    """Conservatively approximate prompt tokens from UTF-8 text length."""
    if value is None:
        return 0
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if not value:
        return 0
    return max(1, math.ceil(len(value) / 4))


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


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    required_top_level = {
        "schema_version",
        "plan_id",
        "goal",
        "mode",
        "budget",
        "shared_context",
        "sources",
        "tasks",
        "merge",
    }
    missing = sorted(required_top_level - set(plan))
    if missing:
        errors.append(f"missing required top-level fields: {', '.join(missing)}")

    if not is_non_empty_string(plan.get("schema_version")):
        errors.append("schema_version must be a non-empty string")
    if not valid_id(plan.get("plan_id")):
        errors.append(
            "plan_id must start with an alphanumeric character and contain only letters, digits, '.', '_' or '-'"
        )
    if not is_non_empty_string(plan.get("goal")):
        errors.append("goal must be a non-empty string")
    mode = plan.get("mode")
    if mode not in VALID_MODES:
        errors.append(f"mode must be one of {sorted(VALID_MODES)}, got {mode!r}")

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

    shared_context = plan.get("shared_context")
    if not isinstance(shared_context, dict):
        errors.append("shared_context must be an object")
        shared_context = {}

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
            elif expansion_mode in {"request", "bounded"} and additional == 0:
                warnings.append(
                    f"task {task_id} permits expansion but has a zero expansion budget"
                )

    task_id_set = set(tasks)
    for task_id, dependencies in task_dependencies.items():
        for dependency in dependencies:
            if dependency not in task_id_set:
                errors.append(f"task {task_id} depends on unknown task id: {dependency}")
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

    merge = plan.get("merge")
    if not isinstance(merge, dict):
        errors.append("merge must be an object")
        merge = {}
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

    max_total = budget.get("max_total_dispatched_tokens")
    if isinstance(max_total, int) and total_estimated_input_tokens > max_total:
        errors.append(
            f"estimated total dispatched input {total_estimated_input_tokens} exceeds budget {max_total}"
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
        if task.get("intentional_overlap") is True:
            if not overlap_sources.intersection(task_source_ids.get(task_id, [])):
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
        "--json",
        action="store_true",
        help="print a machine-readable validation report",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        plan = load_plan(args.plan)
    except ValueError as exc:
        report = {"valid": False, "errors": [str(exc)], "warnings": [], "metrics": {}}
        if args.json:
            print(json.dumps(report, indent=2, ensure_ascii=False))
        else:
            print(f"Plan status: INVALID\n\nErrors:\n  - {exc}")
        return 2

    report = validate_plan(plan)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_human_report(report)
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
