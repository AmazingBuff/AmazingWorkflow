#!/usr/bin/env python3
"""Validate a read-only scout Evidence Packet deterministically."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from validate_plan import (
    SUPPORTED_SCHEMA_VERSION,
    VALID_EXPANSION_MODES,
    is_non_empty_string,
    load_plan,
    valid_id,
    validate_selector,
)

EVIDENCE_PACKET_REQUIRED_FIELDS = [
    "schema_version",
    "packet_type",
    "plan_id",
    "task_id",
    "status",
    "summary",
    "findings",
    "facts_for_parent",
    "assumptions",
    "unknowns",
    "expansion_requests",
    "expansions_used",
]
EVIDENCE_PACKET_TOP_LEVEL_OPTIONAL_FIELDS = ["metrics"]
EVIDENCE_PACKET_FINDING_FIELDS = [
    "id",
    "claim",
    "severity",
    "confidence",
    "evidence",
    "recommendation",
]
EVIDENCE_PACKET_STATUSES = {"complete", "partial", "blocked"}
FINDING_SEVERITIES = {"low", "medium", "high", "critical"}
FINDING_CONFIDENCE = {"low", "medium", "high"}
FACT_CONFIDENCE = {"confirmed", "inferred", "unverified"}


def load_packet(path: Path) -> dict[str, Any]:
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"packet file not found: {path}") from exc
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"unable to read packet: {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(packet, dict):
        raise TypeError("packet root must be a JSON object")
    return packet


def _validate_string_array(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{path} must be an array of strings")
        return
    for index, item in enumerate(value):
        if not is_non_empty_string(item):
            errors.append(f"{path}[{index}] must be a non-empty string")


def _validate_positive_integer(value: Any, path: str, errors: list[str]) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        errors.append(f"{path} must be an integer >= 1")


def _validate_evidence(
    evidence: Any,
    path: str,
    errors: list[str],
    source_ids: set[str] | None,
) -> None:
    if not isinstance(evidence, list) or not evidence:
        errors.append(f"{path} must be a non-empty array")
        return
    for index, item in enumerate(evidence):
        item_path = f"{path}[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_path} must be an object")
            continue
        for field in ("source_id", "locator", "note"):
            if not is_non_empty_string(item.get(field)):
                errors.append(f"{item_path}.{field} must be a non-empty string")
        source_id = item.get("source_id")
        if isinstance(source_id, str) and source_ids is not None and source_id not in source_ids:
            errors.append(f"{item_path}.source_id references an unknown source id: {source_id}")


def _validate_findings(
    findings: Any,
    errors: list[str],
    source_ids: set[str] | None,
) -> set[str]:
    finding_ids: set[str] = set()
    if not isinstance(findings, list):
        errors.append("findings must be an array")
        return finding_ids
    for index, finding in enumerate(findings):
        path = f"findings[{index}]"
        if not isinstance(finding, dict):
            errors.append(f"{path} must be an object")
            continue
        for field in EVIDENCE_PACKET_FINDING_FIELDS:
            if field not in finding:
                errors.append(f"{path} is missing required field: {field}")
        finding_id = finding.get("id")
        if not valid_id(finding_id):
            errors.append(f"{path}.id has an invalid identifier")
        elif finding_id in finding_ids:
            errors.append(f"duplicate finding id: {finding_id}")
        else:
            finding_ids.add(finding_id)
        if not is_non_empty_string(finding.get("claim")):
            errors.append(f"{path}.claim must be a non-empty string")
        if finding.get("severity") not in FINDING_SEVERITIES:
            errors.append(f"{path}.severity must be one of {sorted(FINDING_SEVERITIES)}")
        if finding.get("confidence") not in FINDING_CONFIDENCE:
            errors.append(
                f"{path}.confidence must be one of {sorted(FINDING_CONFIDENCE)}"
            )
        if not is_non_empty_string(finding.get("recommendation")):
            errors.append(f"{path}.recommendation must be a non-empty string")
        _validate_evidence(finding.get("evidence"), f"{path}.evidence", errors, source_ids)
    return finding_ids


def _validate_facts(
    facts: Any,
    errors: list[str],
    source_ids: set[str] | None,
) -> set[str]:
    fact_ids: set[str] = set()
    if not isinstance(facts, list):
        errors.append("facts_for_parent must be an array")
        return fact_ids
    for index, fact in enumerate(facts):
        path = f"facts_for_parent[{index}]"
        if not isinstance(fact, dict):
            errors.append(f"{path} must be an object")
            continue
        for field in ("id", "statement", "provenance", "confidence"):
            if field not in fact:
                errors.append(f"{path} is missing required field: {field}")
        fact_id = fact.get("id")
        if not valid_id(fact_id):
            errors.append(f"{path}.id has an invalid identifier")
        elif fact_id in fact_ids:
            errors.append(f"duplicate fact id: {fact_id}")
        else:
            fact_ids.add(fact_id)
        if not is_non_empty_string(fact.get("statement")):
            errors.append(f"{path}.statement must be a non-empty string")
        provenance = fact.get("provenance")
        _validate_string_array(provenance, f"{path}.provenance", errors)
        if isinstance(provenance, list) and source_ids is not None:
            for source_id in provenance:
                if isinstance(source_id, str) and source_id not in source_ids:
                    errors.append(
                        f"{path}.provenance references an unknown source id: {source_id}"
                    )
        if fact.get("confidence") not in FACT_CONFIDENCE:
            errors.append(f"{path}.confidence must be one of {sorted(FACT_CONFIDENCE)}")
    return fact_ids


def _validate_expansions(
    packet: dict[str, Any],
    errors: list[str],
    source_ids: set[str] | None,
    plan_task: dict[str, Any] | None,
) -> None:
    requests = packet.get("expansion_requests")
    used = packet.get("expansions_used")
    if not isinstance(requests, list):
        errors.append("expansion_requests must be an array")
        requests = []
    if not isinstance(used, list):
        errors.append("expansions_used must be an array")
        used = []

    request_ids: set[str] = set()
    for index, request in enumerate(requests):
        path = f"expansion_requests[{index}]"
        if not isinstance(request, dict):
            errors.append(f"{path} must be an object")
            continue
        required = (
            "request_id",
            "task_id",
            "missing_information",
            "requested_source",
            "reason",
            "estimated_tokens",
        )
        for field in required:
            if field not in request:
                errors.append(f"{path} is missing required field: {field}")
        request_id = request.get("request_id")
        if not valid_id(request_id):
            errors.append(f"{path}.request_id has an invalid identifier")
        elif request_id in request_ids:
            errors.append(f"duplicate expansion request id: {request_id}")
        else:
            request_ids.add(request_id)
        if request.get("task_id") != packet.get("task_id"):
            errors.append(f"{path}.task_id must equal packet.task_id")
        for field in ("missing_information", "reason"):
            if not is_non_empty_string(request.get(field)):
                errors.append(f"{path}.{field} must be a non-empty string")
        _validate_positive_integer(request.get("estimated_tokens"), f"{path}.estimated_tokens", errors)
        requested_source = request.get("requested_source")
        if not isinstance(requested_source, dict):
            errors.append(f"{path}.requested_source must be an object")
        else:
            if not is_non_empty_string(requested_source.get("uri")):
                errors.append(f"{path}.requested_source.uri must be a non-empty string")
            validate_selector(
                requested_source.get("selector"),
                f"{path}.requested_source.selector",
                errors,
            )

    used_tokens = 0
    used_request_ids: set[str] = set()
    for index, expansion in enumerate(used):
        path = f"expansions_used[{index}]"
        if not isinstance(expansion, dict):
            errors.append(f"{path} must be an object")
            continue
        required = (
            "request_id",
            "source_id",
            "locator",
            "estimated_tokens",
            "planner_approved",
        )
        for field in required:
            if field not in expansion:
                errors.append(f"{path} is missing required field: {field}")
        request_id = expansion.get("request_id")
        if not valid_id(request_id):
            errors.append(f"{path}.request_id has an invalid identifier")
        elif request_id in used_request_ids:
            errors.append(f"duplicate used expansion request id: {request_id}")
        else:
            used_request_ids.add(request_id)
            if request_id not in request_ids:
                errors.append(f"{path}.request_id does not reference an expansion request")
        source_id = expansion.get("source_id")
        if not valid_id(source_id):
            errors.append(f"{path}.source_id has an invalid identifier")
        elif source_ids is not None and source_id not in source_ids:
            errors.append(f"{path}.source_id references an unknown source id: {source_id}")
        if not is_non_empty_string(expansion.get("locator")):
            errors.append(f"{path}.locator must be a non-empty string")
        estimated_tokens = expansion.get("estimated_tokens")
        _validate_positive_integer(estimated_tokens, f"{path}.estimated_tokens", errors)
        if isinstance(estimated_tokens, int) and not isinstance(estimated_tokens, bool):
            used_tokens += estimated_tokens
        if expansion.get("planner_approved") is not True:
            errors.append(f"{path}.planner_approved must be true")

    if plan_task is not None:
        policy = plan_task.get("allowed_expansion")
        mode = policy.get("mode") if isinstance(policy, dict) else None
        if mode not in VALID_EXPANSION_MODES:
            errors.append("plan task expansion mode is not an allowed deny-or-request mode")
        if mode == "deny" and (requests or used):
            errors.append("expansions are forbidden when the task expansion mode is deny")
        allowance = policy.get("max_additional_tokens") if isinstance(policy, dict) else None
        if isinstance(allowance, int) and not isinstance(allowance, bool) and used_tokens > allowance:
            errors.append(
                f"used expansion tokens {used_tokens} exceed the Planner allowance {allowance}"
            )


def _reject_forbidden_expansion_values(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in {"mode", "expansion_mode"} and child == "bounded":
                errors.append(f"{child_path} uses forbidden expansion mode 'bounded'")
            if key == "allowed_expansion":
                if not isinstance(child, dict):
                    errors.append(f"{child_path} must be an object")
                elif child.get("mode") not in VALID_EXPANSION_MODES:
                    errors.append(
                        f"{child_path}.mode must be one of {sorted(VALID_EXPANSION_MODES)}"
                    )
            _reject_forbidden_expansion_values(child, child_path, errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_expansion_values(child, f"{path}[{index}]", errors)


def validate_evidence_packet(
    packet: dict[str, Any], plan: dict[str, Any] | None = None
) -> dict[str, Any]:
    errors: list[str] = []
    missing = [field for field in EVIDENCE_PACKET_REQUIRED_FIELDS if field not in packet]
    if missing:
        errors.append(f"packet is missing required fields: {', '.join(missing)}")

    if packet.get("schema_version") != SUPPORTED_SCHEMA_VERSION:
        errors.append(
            f"schema_version must be exactly {SUPPORTED_SCHEMA_VERSION!r}"
        )
    if packet.get("packet_type") != "subagent-result":
        errors.append("packet_type must be 'subagent-result'")
    for field in ("plan_id", "task_id"):
        if not valid_id(packet.get(field)):
            errors.append(f"{field} has an invalid identifier")
    if packet.get("status") not in EVIDENCE_PACKET_STATUSES:
        errors.append(f"status must be one of {sorted(EVIDENCE_PACKET_STATUSES)}")
    if not is_non_empty_string(packet.get("summary")):
        errors.append("summary must be a non-empty string")
    _validate_string_array(packet.get("assumptions"), "assumptions", errors)
    _validate_string_array(packet.get("unknowns"), "unknowns", errors)

    source_ids: set[str] | None = None
    plan_task: dict[str, Any] | None = None
    if plan is not None:
        if packet.get("schema_version") != plan.get("schema_version"):
            errors.append("packet schema_version does not match the plan")
        if packet.get("plan_id") != plan.get("plan_id"):
            errors.append("packet.plan_id does not match the plan")
        plan_tasks = plan.get("tasks")
        if isinstance(plan_tasks, list):
            plan_task = next(
                (
                    task
                    for task in plan_tasks
                    if isinstance(task, dict) and task.get("id") == packet.get("task_id")
                ),
                None,
            )
            if plan_task is None:
                errors.append("packet.task_id does not identify a task in the plan")
        plan_sources = plan.get("sources")
        if isinstance(plan_sources, list):
            source_ids = {
                source.get("id")
                for source in plan_sources
                if isinstance(source, dict) and valid_id(source.get("id"))
            }

    _validate_findings(packet.get("findings"), errors, source_ids)
    _validate_facts(packet.get("facts_for_parent"), errors, source_ids)
    _validate_expansions(packet, errors, source_ids, plan_task)
    if packet.get("status") in {"partial", "blocked"}:
        unknowns = packet.get("unknowns")
        if not isinstance(unknowns, list) or not unknowns:
            errors.append("partial or blocked packets must list the missing information in unknowns")
    if "metrics" in packet and not isinstance(packet.get("metrics"), dict):
        errors.append("metrics must be an object when present")

    _reject_forbidden_expansion_values(packet, "packet", errors)
    return {"valid": not errors, "errors": errors}


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path, help="path to an Evidence Packet JSON file")
    parser.add_argument(
        "--plan",
        type=Path,
        default=None,
        help="optional plan used to check task/source and expansion provenance",
    )
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        packet = load_packet(args.packet)
        plan = load_plan(args.plan) if args.plan else None
        report = validate_evidence_packet(packet, plan)
    except (TypeError, ValueError) as exc:
        report = {"valid": False, "errors": [str(exc)]}

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        status = "VALID" if report["valid"] else "INVALID"
        print(f"Evidence Packet status: {status}")
        for error in report["errors"]:
            print(f"  - {error}")
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
