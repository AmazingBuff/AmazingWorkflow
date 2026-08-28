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

from validate_evidence_packet import (
    EVIDENCE_PACKET_FINDING_FIELDS,
    EVIDENCE_PACKET_REQUIRED_FIELDS,
    EVIDENCE_PACKET_TOP_LEVEL_OPTIONAL_FIELDS,
)
from validate_plan import (
    SUPPORTED_SCHEMA_VERSION,
    facts_for_sources,
    load_plan,
    sha256_file,
    validate_plan,
)

GENERATOR_MARKER = "lightweight-coding-workflow.build_task_packets/v1"


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


def _authenticated_manifest_entries(
    path: Path, plan_id: str, generated_names: set[str]
) -> list[Path]:
    manifest_path = path / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(
            "refusing --overwrite: existing output has no generated manifest"
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(
            f"refusing --overwrite: generated manifest is unreadable: {manifest_path}"
        ) from exc
    if not isinstance(manifest, dict):
        raise TypeError("refusing --overwrite: generated manifest must be an object")
    if manifest.get("generator_marker") != GENERATOR_MARKER:
        raise ValueError(
            "refusing --overwrite: manifest does not contain the stable generator marker"
        )
    if manifest.get("plan_id") != plan_id:
        raise ValueError(
            "refusing --overwrite: manifest plan_id does not match the new plan"
        )

    expected_packet_names = sorted(generated_names - {"manifest.json"})
    packet_paths = manifest.get("packet_paths")
    if packet_paths != expected_packet_names:
        raise ValueError(
            "refusing --overwrite: manifest packet paths do not exactly match the new plan"
        )
    if any(
        not isinstance(packet_path, str)
        or Path(packet_path).name != packet_path
        or packet_path == "manifest.json"
        for packet_path in packet_paths
    ):
        raise ValueError(
            "refusing --overwrite: manifest contains an unsafe packet path"
        )

    packets = manifest.get("packets")
    if not isinstance(packets, list):
        raise TypeError("refusing --overwrite: manifest packets must be an array")
    packet_entries: dict[str, dict[str, Any]] = {}
    for packet in packets:
        if not isinstance(packet, dict):
            raise TypeError(
                "refusing --overwrite: manifest packet entries must be objects"
            )
        packet_path = packet.get("path")
        packet_digest = packet.get("sha256")
        if (
            not isinstance(packet_path, str)
            or packet_path in packet_entries
            or not isinstance(packet_digest, str)
            or not packet_digest.startswith("sha256:")
            or len(packet_digest) != len("sha256:") + 64
        ):
            raise ValueError(
                "refusing --overwrite: manifest packet entries lack unique path digests"
            )
        if packet_path not in expected_packet_names:
            raise ValueError(
                "refusing --overwrite: manifest packet paths do not exactly match the new plan"
            )
        packet_entries[packet_path] = packet
    if sorted(packet_entries) != expected_packet_names:
        raise ValueError(
            "refusing --overwrite: manifest packet entries do not exactly match the new plan"
        )

    entries = sorted(path.iterdir(), key=lambda entry: entry.name)
    authenticated_names = {"manifest.json", *expected_packet_names}
    if {entry.name for entry in entries} != authenticated_names:
        raise ValueError(
            "refusing --overwrite: output contains files not authenticated by its manifest"
        )
    authenticated_entries = [manifest_path]
    for packet_path in expected_packet_names:
        packet_file = path / packet_path
        if not packet_file.is_file():
            raise ValueError(
                f"refusing --overwrite: authenticated packet is missing: {packet_file}"
            )
        expected_digest = packet_entries[packet_path]["sha256"]
        actual_digest = f"sha256:{sha256_file(packet_file)}"
        if actual_digest != expected_digest:
            raise ValueError(
                f"refusing --overwrite: authenticated packet digest mismatch: {packet_file}"
            )
        authenticated_entries.append(packet_file)
    return authenticated_entries


def prepare_output_directory(
    path: Path, overwrite: bool, plan_id: str, generated_names: set[str]
) -> None:
    if path.exists() and not path.is_dir():
        raise ValueError(f"output path exists and is not a directory: {path}")
    if path.exists() and any(path.iterdir()):
        if not overwrite:
            raise ValueError(
                f"output directory is not empty: {path}; pass --overwrite to replace it"
            )
        authenticated_entries = _authenticated_manifest_entries(
            path, plan_id, generated_names
        )
        for entry in authenticated_entries:
            entry.unlink()
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
        "configuration": plan["configuration"],
        "routing": plan["routing"],
        "discovery_authorization": plan["discovery_authorization"],
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
            "Use only the declared deny-or-request expansion policy for missing information.",
            "A request-mode expansion requires explicit Planner approval before reading the requested source.",
            "Return conclusions, evidence, uncertainty, and reusable facts; do not return private chain-of-thought.",
            "Preserve source IDs and precise locators in every material finding.",
        ],
        "response_contract": {
            "schema_version": SUPPORTED_SCHEMA_VERSION,
            "packet_type": "subagent-result",
            "schema_ref": "assets/context-routing/evidence-packet.schema.json",
            "validation_authority": "scripts/validate_evidence_packet.py",
            "required_fields": EVIDENCE_PACKET_REQUIRED_FIELDS,
            "optional_fields": EVIDENCE_PACKET_TOP_LEVEL_OPTIONAL_FIELDS,
            "status_values": ["complete", "partial", "blocked"],
            "finding_fields": EVIDENCE_PACKET_FINDING_FIELDS,
            "evidence_fields": ["source_id", "locator", "note"],
            "expansion_modes": ["deny", "request"],
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
        "--config",
        type=Path,
        default=None,
        help="effective routing configuration (default: package default-config.yaml)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace only packet files authenticated by a matching generated manifest",
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
    except (TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    report = validate_plan(plan, args.config)
    if not report["valid"]:
        print("plan validation failed:", file=sys.stderr)
        for error in report["errors"]:
            print(f"  - {error}", file=sys.stderr)
        return 2

    try:
        layers = topological_layers(plan["tasks"])
    except (TypeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    generated_names = {"manifest.json"}
    generated_names.update(f"{task['id']}.json" for task in plan["tasks"])
    try:
        prepare_output_directory(
            args.out, args.overwrite, plan["plan_id"], generated_names
        )
    except (TypeError, ValueError) as exc:
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
                "sha256": f"sha256:{sha256_file(packet_path)}",
                "dependencies": task.get("dependencies", []),
                "estimated_input_tokens": report["metrics"]["per_task"][task_id][
                    "estimated_input_tokens"
                ],
            }
        )

    manifest = {
        "schema_version": plan["schema_version"],
        "packet_type": "task-packet-manifest",
        "generator_marker": GENERATOR_MARKER,
        "plan_id": plan["plan_id"],
        "mode": plan["mode"],
        "discovery_authorization": plan["discovery_authorization"],
        "packet_paths": sorted(entry["path"] for entry in packet_entries),
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
