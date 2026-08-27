#!/usr/bin/env python3
"""Build standalone, source-descriptor-only task packets from a validated plan."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from validate_plan import facts_for_sources, load_plan, validate_plan


def topological_layers(tasks: list[dict[str, Any]]) -> list[list[str]]:
    dependencies = {task["id"]: set(task.get("dependencies", [])) for task in tasks}
    dependents: dict[str, set[str]] = defaultdict(set)
    for task_id, task_dependencies in dependencies.items():
        for dependency in task_dependencies:
            dependents[dependency].add(task_id)

    remaining = set(dependencies)
    completed: set[str] = set()
    layers: list[list[str]] = []
    while remaining:
        ready = sorted(
            task_id
            for task_id in remaining
            if dependencies[task_id].issubset(completed)
        )
        if not ready:
            raise ValueError("dependency graph contains a cycle")
        layers.append(ready)
        completed.update(ready)
        remaining.difference_update(ready)
    return layers


def prepare_output_directory(path: Path, overwrite: bool) -> None:
    if path.exists() and not path.is_dir():
        raise ValueError(f"output path exists and is not a directory: {path}")
    if path.exists() and any(path.iterdir()):
        if not overwrite:
            raise ValueError(
                f"output directory is not empty: {path}; pass --overwrite to replace it"
            )
        for entry in path.iterdir():
            if entry.name == "manifest.json" or entry.suffix == ".json":
                entry.unlink()
            else:
                raise ValueError(
                    f"refusing --overwrite: directory contains a non-generated file: {entry}"
                )
    path.mkdir(parents=True, exist_ok=True)


def build_packet(
    plan: dict[str, Any],
    task: dict[str, Any],
    source_map: dict[str, dict[str, Any]],
    task_metrics: dict[str, Any],
) -> dict[str, Any]:
    shared_context = plan["shared_context"]
    all_shared_source_ids = set(shared_context.get("source_ids", []))
    inherited_shared_source_ids = (
        all_shared_source_ids if task.get("inherit_shared_sources", True) else set()
    )
    assigned_source_ids = inherited_shared_source_ids.union(task.get("source_ids", []))

    assigned_sources: list[dict[str, Any]] = []
    for source_id in sorted(assigned_source_ids):
        source = copy.deepcopy(source_map[source_id])
        source["scope_origin"] = (
            "shared" if source_id in inherited_shared_source_ids else "task"
        )
        assigned_sources.append(source)

    relevant_facts = facts_for_sources(
        shared_context.get("facts", []), assigned_source_ids
    )
    dependency_placeholders = {
        dependency: {
            "status": "pending",
            "summary": None,
            "facts": [],
            "unknowns": [],
        }
        for dependency in task.get("dependencies", [])
    }

    return {
        "schema_version": plan["schema_version"],
        "packet_type": "subagent-task",
        "plan_id": plan["plan_id"],
        "task_id": task["id"],
        "parent_goal": plan["goal"],
        "mode": plan["mode"],
        "agent_role": task["agent_role"],
        "objective": task["objective"],
        "context": {
            "assumptions": plan.get("assumptions", []),
            "facts": relevant_facts,
            "constraints": shared_context.get("constraints", []),
        },
        "assigned_sources": assigned_sources,
        "questions": task.get("questions", []),
        "deliverable": task["deliverable"],
        "dependencies": task.get("dependencies", []),
        "upstream_context": dependency_placeholders,
        "capabilities": task.get("capabilities", []),
        "allowed_expansion": task["allowed_expansion"],
        "stop_conditions": task.get("stop_conditions", []),
        "evidence_required": task["evidence_required"],
        "intentional_overlap": task["intentional_overlap"],
        "inherit_shared_sources": task.get("inherit_shared_sources", True),
        "execution_rules": [
            "Read only assigned sources initially.",
            "Do not request or assume access to the full parent transcript.",
            "Treat shared summaries as context, not primary evidence, when original sources are assigned.",
            "Use the declared expansion policy for missing information.",
            "Return conclusions, evidence, uncertainty, and reusable facts; do not return private chain-of-thought.",
            "Preserve source IDs and precise locators in every material finding.",
        ],
        "response_contract": {
            "packet_type": "subagent-result",
            "required_fields": [
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
            ],
            "optional_fields": [
                "metrics"
            ],
            "status_values": ["complete", "partial", "blocked"],
            "finding_fields": [
                "id",
                "claim",
                "severity",
                "confidence",
                "evidence",
                "recommendation",
            ],
            "evidence_fields": ["source_id", "locator", "note"],
        },
        "estimated_input": task_metrics,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="path to orchestration-plan.json")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("task-packets"),
        help="output directory, default: task-packets",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace a non-empty output directory",
    )
    return parser.parse_args(argv)


def configure_output_streams() -> None:
    """Keep Unicode report output alive on cp936-style Windows consoles."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    configure_output_streams()
    try:
        plan = load_plan(args.plan)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    report = validate_plan(plan)
    if not report["valid"]:
        print("plan validation failed:", file=sys.stderr)
        for error in report["errors"]:
            print(f"  - {error}", file=sys.stderr)
        return 2

    try:
        prepare_output_directory(args.out, args.overwrite)
        layers = topological_layers(plan["tasks"])
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    source_map = {source["id"]: source for source in plan["sources"]}
    packet_entries: list[dict[str, Any]] = []

    for task in plan["tasks"]:
        task_id = task["id"]
        filename = f"{task_id}.json"
        packet_path = args.out / filename
        packet = build_packet(
            plan,
            task,
            source_map,
            report["metrics"]["per_task"][task_id],
        )
        packet_path.write_text(
            json.dumps(packet, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        packet_entries.append(
            {
                "task_id": task_id,
                "path": filename,
                "dependencies": task.get("dependencies", []),
                "estimated_input_tokens": report["metrics"]["per_task"][task_id][
                    "estimated_input_tokens"
                ],
            }
        )

    manifest = {
        "schema_version": plan["schema_version"],
        "packet_type": "task-packet-manifest",
        "plan_id": plan["plan_id"],
        "mode": plan["mode"],
        "dispatch_layers": layers,
        "packets": packet_entries,
        "plan_metrics": report["metrics"],
        "warnings": report["warnings"],
        "scheduler_note": (
            "Materialize only assigned source descriptors and replace pending upstream_context "
            "entries with compact dependency summaries before invocation."
        ),
    }
    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Built {len(packet_entries)} task packets in {args.out}")
    print(f"Manifest: {manifest_path}")
    print(f"Dispatch layers: {json.dumps(layers, ensure_ascii=False)}")
    print(
        "Estimated total input tokens: "
        f"{report['metrics']['estimated_total_input_tokens']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
