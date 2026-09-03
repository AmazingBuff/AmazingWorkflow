#!/usr/bin/env python3
"""Check that PLAN task schemas, validators, config, packets, and Agent agree."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from build_task_packets import build_micro_task_packet, build_packet
from validate_evidence_packet import (
    EVIDENCE_PACKET_EVIDENCE_FIELDS,
    EVIDENCE_PACKET_FACT_CONFIDENCE_VALUES,
    EVIDENCE_PACKET_FACT_FIELDS,
    EVIDENCE_PACKET_FINDING_CONFIDENCE_VALUES,
    EVIDENCE_PACKET_FINDING_FIELDS,
    EVIDENCE_PACKET_FINDING_SEVERITY_VALUES,
    EVIDENCE_PACKET_REQUIRED_FIELDS,
    EVIDENCE_PACKET_TOP_LEVEL_OPTIONAL_FIELDS,
)
from validate_plan import (
    DEFAULT_CONFIG_RELATIVE_PATH,
    PLAN_TASK_MAX_CONCURRENT,
    PLAN_TASK_MAX_INPUT_TOKENS_PER_ROUND,
    PLAN_TASK_MODEL,
    PLAN_TASK_REASONING_EFFORT,
    READ_ONLY_TASK_KINDS,
    REQUIRED_BUDGET_FIELDS,
    REQUIRED_TASK_FIELDS,
    REQUIRED_TOP_LEVEL_FIELDS,
    SUPPORTED_SCHEMA_VERSION,
    VALID_EXPANSION_MODES,
    VALID_MODES,
    load_effective_config,
    load_plan,
    sha256_text_normalized,
    validate_direct_routing,
    validate_micro_task,
    validate_plan,
)

PLAN_SCHEMA_ID = "urn:lightweight-coding-workflow:orchestration-plan-schema:2.0"
EVIDENCE_SCHEMA_ID = "urn:lightweight-coding-workflow:evidence-packet-schema:2.0"
WORKFLOW_REVISION = "0.7.0"
CORE_PROTOCOL_VERSION = "0.7"
CODEX_ADAPTER_VERSION = "0.7"
ADAPTER_CONTRACT_VERSION = "0.7"
HISTORICAL_CONTRACT_EVIDENCE = {
    (
        "0.6.2",
        "0.6",
        "codex",
        "0.6",
    ): {
        "protocol_sha256": "sha256:90decc027d54e93bf9cb5ebae9ee4c74f17b57e8ae98c9b231281eebd3d299f1",
        "adapter_sha256": "sha256:45f4267ca861558959e8a8b2b7a51ae27d4311dcc3d3bb44ec6f3551376ba26d",
    }
}
CONTRACT_EVIDENCE_FIELDS = (
    "workflow_revision",
    "protocol_version",
    "protocol_sha256",
    "host_adapter",
    "adapter_version",
    "adapter_sha256",
)
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
REQUIRED_ADAPTER_METADATA_FIELDS = {
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
REQUIRED_ADAPTER_CAPABILITIES = {
    "host_identification",
    "planner_binding",
    "model_validation",
    "worker_dispatch",
    "permission_inheritance",
    "lifecycle_control",
    "progress_reporting",
    "result_relay",
    "version_control_management",
}
OPTIONAL_ADAPTER_CAPABILITIES = {"read_only_scout_dispatch"}
VALID_SUPPORT_STATES = {
    "VERIFIED",
    "EXPERIMENTAL",
    "AUTHORING_ONLY",
    "UNSUPPORTED",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"unable to read JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise TypeError(f"JSON root must be an object: {path}")
    return value


def check_equal(
    actual: Any, expected: Any, label: str, errors: list[str]
) -> None:
    if actual != expected:
        errors.append(f"{label} drift: expected {expected!r}, got {actual!r}")


def read_front_matter(path: Path) -> dict[str, str | None]:
    content = path.read_text(encoding="utf-8")
    content = content.lstrip("\ufeff").replace("\r\n", "\n")
    if not content.startswith("---\n"):
        raise ValueError(f"contract has no YAML front matter: {path}")
    end = content.find("\n---", 4)
    if end < 0:
        raise ValueError(f"contract front matter is unterminated: {path}")
    values: dict[str, str | None] = {}
    for line in content[4:end].splitlines():
        if not line.strip() or line.lstrip().startswith(("#", "-")):
            continue
        key, separator, raw_value = line.partition(":")
        if not separator or not key.strip():
            raise ValueError(f"invalid contract front matter line: {line}")
        if key.strip() in values:
            raise ValueError(f"duplicate contract front matter key: {key.strip()}")
        value = raw_value.strip()
        if value in {"null", "~"}:
            values[key.strip()] = None
        else:
            values[key.strip()] = value.strip('"')
    return values


def _parse_front_matter_value(value: str) -> str | None:
    if value in {"null", "~"}:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def read_adapter_front_matter(path: Path) -> dict[str, Any]:
    """Read adapter metadata while preserving list items and duplicate errors."""
    content = path.read_text(encoding="utf-8")
    lines = (
        content.lstrip("\ufeff")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .splitlines()
    )
    if not lines or lines[0] != "---":
        raise ValueError(f"adapter has no YAML front matter: {path}")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError(f"adapter front matter is unterminated: {path}") from exc

    values: dict[str, Any] = {}
    active_list: str | None = None
    for line_number, line in enumerate(lines[1:end], start=2):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("-"):
            if not stripped.startswith("- "):
                raise ValueError(
                    f"invalid adapter front matter list item at {path}:{line_number}"
                )
            if active_list is None or not isinstance(values.get(active_list), list):
                raise ValueError(
                    f"adapter front matter list item has no list key at "
                    f"{path}:{line_number}"
                )
            values[active_list].append(_parse_front_matter_value(stripped[2:].strip()))
            continue
        if line[:1].isspace():
            raise ValueError(
                f"invalid adapter front matter indentation at {path}:{line_number}"
            )
        key, separator, raw_value = line.partition(":")
        key = key.strip()
        if not separator or not key:
            raise ValueError(
                f"invalid adapter front matter line at {path}:{line_number}: {line}"
            )
        if key in values:
            raise ValueError(
                f"duplicate adapter front matter key at {path}:{line_number}: {key}"
            )
        value = raw_value.strip()
        if value:
            values[key] = _parse_front_matter_value(value)
            active_list = None
        else:
            values[key] = []
            active_list = key
    return values


def validate_adapter_metadata(
    metadata: dict[str, Any],
    errors: list[str],
    *,
    expected_adapter_version: str | None = None,
) -> None:
    """Validate the exact adapter metadata required by the Core contract."""
    missing = sorted(REQUIRED_ADAPTER_METADATA_FIELDS - set(metadata))
    if missing:
        errors.append(
            "adapter metadata is incomplete; missing fields: " + ", ".join(missing)
        )

    for field in (
        "host_adapter",
        "host_id",
        "display_name",
        "protocol_version",
        "adapter_version",
        "support_state",
    ):
        value = metadata.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"adapter metadata field {field} must be a non-empty string")

    if metadata.get("protocol_version") != CORE_PROTOCOL_VERSION:
        errors.append(
            "adapter metadata protocol_version must be exactly "
            f"{CORE_PROTOCOL_VERSION!r}"
        )
    if (
        expected_adapter_version is not None
        and metadata.get("adapter_version") != expected_adapter_version
    ):
        errors.append(
            "adapter metadata adapter_version drift: expected "
            f"{expected_adapter_version!r}, got {metadata.get('adapter_version')!r}"
        )

    support_state = metadata.get("support_state")
    if support_state not in VALID_SUPPORT_STATES:
        errors.append(
            "adapter metadata support_state must be one of "
            f"{sorted(VALID_SUPPORT_STATES)}"
        )
    elif support_state != "VERIFIED":
        errors.append(
            "adapter metadata support_state must be 'VERIFIED' for implementation"
        )

    surfaces = metadata.get("supported_surfaces")
    if not isinstance(surfaces, list) or not surfaces:
        errors.append("adapter metadata supported_surfaces must be a non-empty list")
    elif any(not isinstance(item, str) or not item.strip() for item in surfaces):
        errors.append("adapter metadata supported_surfaces must contain strings")

    capabilities = metadata.get("capabilities")
    if not isinstance(capabilities, list):
        errors.append("adapter metadata capabilities must be a list")
    else:
        capability_names = [item for item in capabilities if isinstance(item, str)]
        duplicates = sorted(
            {item for item in capability_names if capability_names.count(item) > 1}
        )
        if duplicates:
            errors.append(
                "adapter metadata capabilities contains duplicates: "
                + ", ".join(duplicates)
            )
        if len(capability_names) != len(capabilities):
            errors.append("adapter metadata capabilities must contain strings")
        actual = set(capability_names)
        missing_capabilities = sorted(REQUIRED_ADAPTER_CAPABILITIES - actual)
        extra_capabilities = sorted(actual - REQUIRED_ADAPTER_CAPABILITIES)
        if missing_capabilities:
            errors.append(
                "adapter metadata capabilities is incomplete; missing: "
                + ", ".join(missing_capabilities)
            )
        if extra_capabilities:
            errors.append(
                "adapter metadata capabilities contains incompatible entries: "
                + ", ".join(extra_capabilities)
            )

    optional = metadata.get("optional_capabilities")
    if optional is not None:
        if not isinstance(optional, list):
            errors.append("adapter metadata optional_capabilities must be a list")
        else:
            optional_names = [item for item in optional if isinstance(item, str)]
            duplicates = sorted(
                {item for item in optional_names if optional_names.count(item) > 1}
            )
            if duplicates:
                errors.append(
                    "adapter metadata optional_capabilities contains duplicates: "
                    + ", ".join(duplicates)
                )
            if len(optional_names) != len(optional):
                errors.append(
                    "adapter metadata optional_capabilities must contain strings"
                )
            extra_optional = sorted(set(optional_names) - OPTIONAL_ADAPTER_CAPABILITIES)
            if extra_optional:
                errors.append(
                    "adapter metadata optional_capabilities contains incompatible "
                    "entries: "
                    + ", ".join(extra_optional)
                )

    if support_state == "VERIFIED":
        verified_on = metadata.get("verified_on")
        if not isinstance(verified_on, str) or not verified_on.strip():
            errors.append(
                "adapter metadata verified_on must be populated for VERIFIED adapters"
            )


def _source_revision(content: str, label: str) -> str | None:
    matches = re.findall(
        rf"(?m)^{re.escape(label)}:\s*[`\"]?([^`\"\s]+)[`\"]?\.?\s*$",
        content,
    )
    return matches[0] if len(matches) == 1 else None


def validate_approved_contract(
    contract_path: Path,
    root: Path,
    protocol_path: Path,
    adapter_path: Path,
) -> list[str]:
    errors: list[str] = []
    try:
        contract = read_front_matter(contract_path)
    except (OSError, UnicodeError, ValueError) as exc:
        return [f"contract evidence check: {exc}"]

    historical_key = (
        contract.get("workflow_revision"),
        contract.get("protocol_version"),
        contract.get("host_adapter"),
        contract.get("adapter_version"),
    )
    historical_evidence = HISTORICAL_CONTRACT_EVIDENCE.get(historical_key)
    if historical_evidence is not None:
        if contract.get("status") != "APPROVED":
            errors.append("contract evidence check: contract status must be APPROVED")
        for field in CONTRACT_EVIDENCE_FIELDS:
            value = contract.get(field)
            if not isinstance(value, str) or not value.strip() or "{{" in value:
                errors.append(
                    f"contract evidence check: {field} must be populated without placeholders"
                )
        for field, expected in historical_evidence.items():
            check_equal(
                contract.get(field), expected, f"historical contract {field}", errors
            )
        return errors

    host_adapter = contract.get("host_adapter")
    if isinstance(host_adapter, str) and host_adapter.strip() and "{{" not in host_adapter:
        adapter_name = Path(host_adapter).name
        selected_adapter = root / "references/adapters" / f"{adapter_name}.md"
        if adapter_name != host_adapter or not selected_adapter.is_file():
            errors.append(
                f"contract evidence check: unknown adapter {host_adapter!r}"
            )
        else:
            adapter_path = selected_adapter

    try:
        workflow_text = (root / "SKILL.md").read_text(encoding="utf-8")
        protocol_text = protocol_path.read_text(encoding="utf-8")
        adapter_text = adapter_path.read_text(encoding="utf-8")
        adapter_meta = read_adapter_front_matter(adapter_path)
    except (OSError, UnicodeError, ValueError) as exc:
        return [*errors, f"contract evidence check: {exc}"]

    if contract.get("status") != "APPROVED":
        errors.append("contract evidence check: contract status must be APPROVED")
    for field in CONTRACT_EVIDENCE_FIELDS:
        value = contract.get(field)
        if not isinstance(value, str) or not value.strip() or "{{" in value:
            errors.append(
                f"contract evidence check: {field} must be populated without placeholders"
            )

    validate_adapter_metadata(adapter_meta, errors)
    if adapter_meta.get("host_adapter") == "codex":
        check_equal(
            adapter_meta.get("adapter_version"),
            CODEX_ADAPTER_VERSION,
            "Codex adapter version",
            errors,
        )

    expected_workflow = _source_revision(workflow_text, "Workflow revision")
    expected_protocol = _source_revision(protocol_text, "Protocol version")
    expected_adapter = adapter_meta.get("adapter_version") or _source_revision(
        adapter_text, "adapter_version"
    )
    check_equal(
        expected_workflow,
        WORKFLOW_REVISION,
        "declared workflow revision",
        errors,
    )
    check_equal(
        expected_protocol,
        CORE_PROTOCOL_VERSION,
        "declared Core protocol version",
        errors,
    )
    check_equal(
        contract.get("workflow_revision"),
        expected_workflow,
        "contract workflow revision",
        errors,
    )
    check_equal(
        contract.get("protocol_version"), expected_protocol, "contract protocol version", errors
    )
    check_equal(
        contract.get("adapter_version"), expected_adapter, "contract adapter version", errors
    )
    if contract.get("host_adapter") != adapter_meta.get("host_adapter"):
        errors.append("contract evidence check: host_adapter must identify the selected adapter")

    protocol_digest = contract.get("protocol_sha256")
    adapter_digest = contract.get("adapter_sha256")
    if not (isinstance(protocol_digest, str) and SHA256_PATTERN.fullmatch(protocol_digest)):
        if isinstance(protocol_digest, str) and protocol_digest.strip():
            errors.append(
                f"contract evidence check: protocol_sha256 invalid sha256 format: {protocol_digest}"
            )
    else:
        check_equal(
            protocol_digest,
            f"sha256:{sha256_text_normalized(protocol_path)}",
            "contract protocol SHA-256",
            errors,
        )
    if not (isinstance(adapter_digest, str) and SHA256_PATTERN.fullmatch(adapter_digest)):
        if isinstance(adapter_digest, str) and adapter_digest.strip():
            errors.append(
                f"contract evidence check: adapter_sha256 invalid sha256 format: {adapter_digest}"
            )
    else:
        check_equal(
            adapter_digest,
            f"sha256:{sha256_text_normalized(adapter_path)}",
            "contract adapter SHA-256",
            errors,
        )
    return errors


def check_contract_parity(root: Path) -> dict[str, Any]:
    errors: list[str] = []
    schema_path = root / "assets/context-routing/orchestration-plan.schema.json"
    evidence_schema_path = root / "assets/context-routing/evidence-packet.schema.json"
    config_path = root / DEFAULT_CONFIG_RELATIVE_PATH
    example_path = root / "assets/context-routing/example-plan.json"
    agent_path = root / "agents/lightweight_scout.toml"
    implementer_path = root / "agents/lightweight_implementer.toml"
    template_path = root / "assets/implementation-contract.md"
    skill_path = root / "SKILL.md"
    protocol_path = root / "references/protocol.md"
    adapter_path = root / "references/adapters/codex.md"
    adapter_contract_path = root / "references/adapter-contract.md"

    try:
        plan_schema = load_json(schema_path)
        evidence_schema = load_json(evidence_schema_path)
        config = load_effective_config(config_path)
        example_plan = load_plan(example_path)
    except (TypeError, ValueError) as exc:
        return {"valid": False, "errors": [str(exc)]}

    check_equal(
        plan_schema.get("$defs", {})
        .get("batchPlan", {})
        .get("properties", {})
        .get("schema_version", {})
        .get("const"),
        SUPPORTED_SCHEMA_VERSION,
        "batch plan schema_version",
        errors,
    )
    check_equal(plan_schema.get("$id"), PLAN_SCHEMA_ID, "plan schema id", errors)
    check_equal(
        set(plan_schema.get("$defs", {}).get("batchPlan", {}).get("required", [])),
        REQUIRED_TOP_LEVEL_FIELDS,
        "batch plan required fields",
        errors,
    )
    expansion_enum = (
        plan_schema.get("$defs", {})
        .get("expansionPolicy", {})
        .get("properties", {})
        .get("mode", {})
        .get("enum")
    )
    check_equal(
        set(expansion_enum or []), VALID_EXPANSION_MODES, "expansion modes", errors
    )
    check_equal(
        set(
            plan_schema.get("$defs", {})
            .get("task", {})
            .get("required", [])
        ),
        REQUIRED_TASK_FIELDS,
        "task required fields",
        errors,
    )
    budget_schema_fields = set(
        plan_schema.get("$defs", {})
        .get("budget", {})
        .get("required", [])
    )
    check_equal(budget_schema_fields, REQUIRED_BUDGET_FIELDS, "budget fields", errors)
    micro_required = {
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
        "response_contract",
        "execution_rules",
    }
    check_equal(
        set(plan_schema.get("$defs", {}).get("microTask", {}).get("required", [])),
        micro_required,
        "micro-task required fields",
        errors,
    )

    check_equal(
        evidence_schema.get("properties", {}).get("schema_version", {}).get("const"),
        SUPPORTED_SCHEMA_VERSION,
        "Evidence Packet schema_version",
        errors,
    )
    check_equal(
        evidence_schema.get("properties", {}).get("packet_type", {}).get("const"),
        "subagent-result",
        "Evidence Packet packet_type",
        errors,
    )
    check_equal(
        evidence_schema.get("$id"), EVIDENCE_SCHEMA_ID, "Evidence Packet schema id", errors
    )
    check_equal(
        evidence_schema.get("required", []),
        EVIDENCE_PACKET_REQUIRED_FIELDS,
        "Evidence Packet required fields",
        errors,
    )
    check_equal(
        list(EVIDENCE_PACKET_TOP_LEVEL_OPTIONAL_FIELDS), ["metrics"],
        "Evidence Packet optional fields", errors
    )
    check_equal(
        evidence_schema.get("$defs", {}).get("finding", {}).get("required", []),
        EVIDENCE_PACKET_FINDING_FIELDS,
        "Evidence Packet finding fields",
        errors,
    )
    check_equal(
        evidence_schema.get("$defs", {})
        .get("finding", {})
        .get("properties", {})
        .get("severity", {})
        .get("enum"),
        EVIDENCE_PACKET_FINDING_SEVERITY_VALUES,
        "Evidence Packet finding severity values",
        errors,
    )
    check_equal(
        evidence_schema.get("$defs", {})
        .get("finding", {})
        .get("properties", {})
        .get("confidence", {})
        .get("enum"),
        EVIDENCE_PACKET_FINDING_CONFIDENCE_VALUES,
        "Evidence Packet finding confidence values",
        errors,
    )
    check_equal(
        evidence_schema.get("$defs", {}).get("fact", {}).get("required", []),
        EVIDENCE_PACKET_FACT_FIELDS,
        "Evidence Packet fact fields",
        errors,
    )
    check_equal(
        evidence_schema.get("$defs", {})
        .get("fact", {})
        .get("properties", {})
        .get("confidence", {})
        .get("enum"),
        EVIDENCE_PACKET_FACT_CONFIDENCE_VALUES,
        "Evidence Packet fact confidence values",
        errors,
    )

    configured_modes = config.get("scout_policy", {}).get("allowed_expansion_modes")
    check_equal(
        configured_modes, sorted(VALID_EXPANSION_MODES), "configured expansion modes", errors
    )
    check_equal(
        config.get("scout_policy", {}).get("response_schema_version"),
        SUPPORTED_SCHEMA_VERSION,
        "configured Evidence Packet schema version",
        errors,
    )
    check_equal(
        config.get("scout_policy", {}).get("task_kinds"),
        sorted(READ_ONLY_TASK_KINDS),
        "configured PLAN task kinds",
        errors,
    )
    configured_policy = config.get("plan_task_policy", {})
    check_equal(
        configured_policy.get("model"), PLAN_TASK_MODEL, "PLAN-task model", errors
    )
    check_equal(
        configured_policy.get("reasoning_effort"),
        PLAN_TASK_REASONING_EFFORT,
        "PLAN-task reasoning effort",
        errors,
    )
    check_equal(
        configured_policy.get("max_concurrent_tasks"),
        PLAN_TASK_MAX_CONCURRENT,
        "PLAN-task concurrency",
        errors,
    )
    check_equal(
        configured_policy.get("max_estimated_input_tokens_per_round"),
        PLAN_TASK_MAX_INPUT_TOKENS_PER_ROUND,
        "PLAN-task input ceiling",
        errors,
    )
    check_equal(set(config.get("mode_profiles", {})), VALID_MODES, "mode profiles", errors)
    if config.get("model_routing", {}).get("scout_model_default") is not None:
        errors.append("host-specific scout model defaults must not be in default-config.yaml")
    for mode, profile in config.get("mode_profiles", {}).items():
        if isinstance(profile, dict):
            check_equal(
                set(REQUIRED_BUDGET_FIELDS).issubset(profile),
                True,
                f"{mode} budget profile completeness",
                errors,
            )

    try:
        agent_text = agent_path.read_text(encoding="utf-8")
        implementer_text = implementer_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"unable to read PLAN/WORK Agent definitions: {exc}")
    else:
        if 'sandbox_mode = "read-only"' not in agent_text:
            errors.append("Evidence Task Agent does not declare sandbox_mode = 'read-only'")
        for task_kind in sorted(READ_ONLY_TASK_KINDS):
            if task_kind not in agent_text:
                errors.append(f"Evidence Task Agent does not document task kind {task_kind!r}")
        required_agent_terms = {
            "low, medium, high, or critical",
            "low, medium, or high",
            "id, statement, provenance, and confidence",
            "confirmed, inferred, or unverified",
        }
        for term in sorted(required_agent_terms):
            if term not in agent_text:
                errors.append(
                    f"Evidence Task Agent is missing response-contract term: {term}"
                )
        if 'mode = "bounded"' in agent_text or "mode: bounded" in agent_text:
            errors.append("Evidence Task Agent mentions the forbidden bounded expansion mode")
        if "You are the implementation phase" in implementer_text:
            errors.append(
                "Implementation Agent retains the obsolete phase-owner identity"
            )
        if (
            "You are the task-scoped implementation Agent used in the WORK phase"
            not in implementer_text
        ):
            errors.append(
                "Implementation Agent must identify as the task-scoped WORK Agent"
            )
        required_implementer_terms = {
            "Single-writer coding agent",
            "approved implementation contract",
            "sole authority",
            "Do not:",
            "spawn another agent",
            "Return BLOCKED",
            "Return FAILED",
            "Return DONE",
            "STATUS: DONE",
        }
        for term in sorted(required_implementer_terms):
            if term not in implementer_text:
                errors.append(
                    f"Implementation Agent is missing required WORK restriction: {term}"
                )

    try:
        template_text = template_path.read_text(encoding="utf-8")
        skill_text = skill_path.read_text(encoding="utf-8")
        protocol_text = protocol_path.read_text(encoding="utf-8")
        adapter_text = adapter_path.read_text(encoding="utf-8")
        adapter_contract_text = adapter_contract_path.read_text(encoding="utf-8")
        adapter_meta = read_adapter_front_matter(adapter_path)
        config_path.read_text(encoding="utf-8")
        example_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f"contract parity source read failed: {exc}")
    else:
        validate_adapter_metadata(
            adapter_meta,
            errors,
            expected_adapter_version=CODEX_ADAPTER_VERSION,
        )
        check_equal(
            adapter_meta.get("optional_capabilities"),
            ["read_only_scout_dispatch"],
            "Codex verified optional PLAN-task capabilities",
            errors,
        )
        if 'revision: {{REVISION}}' not in template_text:
            errors.append("implementation-contract template must retain the revision placeholder")
        if 'status: "DRAFT"' not in template_text:
            errors.append("implementation-contract template must default to DRAFT")
        if f'workflow_revision: "{WORKFLOW_REVISION}"' not in template_text:
            errors.append("implementation-contract template has the wrong workflow revision")
        if "source_revision:" in template_text or "source_digest:" in template_text:
            errors.append("implementation-contract template contains superseded source fields")
        for field in CONTRACT_EVIDENCE_FIELDS:
            if f"{field}:" not in template_text:
                errors.append(f"implementation-contract template is missing {field}")
        for field in ("workflow_revision", "protocol_sha256", "adapter_sha256"):
            if field not in skill_text or field not in protocol_text or field not in adapter_text:
                errors.append(f"approval/dispatch gate documentation is missing {field}")
        check_equal(
            _source_revision(skill_text, "Workflow revision"),
            WORKFLOW_REVISION,
            "Skill workflow revision",
            errors,
        )
        check_equal(
            _source_revision(protocol_text, "Protocol version"),
            CORE_PROTOCOL_VERSION,
            "Core protocol version",
            errors,
        )
        check_equal(
            _source_revision(adapter_text, "adapter_version"),
            CODEX_ADAPTER_VERSION,
            "Codex adapter version",
            errors,
        )
        check_equal(
            _source_revision(adapter_contract_text, "Contract version"),
            ADAPTER_CONTRACT_VERSION,
            "Host Adapter Contract version",
            errors,
        )
        required_live_evidence_terms = {
            "Live evidence recorded 2026-09-03",
            "real `lightweight_scout` micro",
            "`repository-read` task",
            "`gpt-5.6-luna/max`",
            "`fork_context=false`",
            "bounded task envelope",
            "validate_evidence_packet.py` with exit `0`",
            "used no expansion",
            "byte-for-byte identical",
            "does not by itself exercise expansion handling",
        }
        for term in sorted(required_live_evidence_terms):
            if term not in adapter_text:
                errors.append(
                    f"Codex adapter is missing retained PLAN-task evidence: {term}"
                )
        required_adapter_contract_terms = {
            "`PLAN` and `WORK`",
            "host_identification",
            "planner_binding",
            "model_validation",
            "worker_dispatch",
            "permission_inheritance",
            "lifecycle_control",
            "progress_reporting",
            "result_relay",
            "version_control_management",
            "identify_host",
            "bind_planner",
            "validate_model",
            "dispatch_worker",
            "inherit_permissions",
            "control_lifecycle",
            "report_progress",
            "relay_result",
            "manage_version_control",
            "requirement-research",
            "repository-read",
            "dependency-check",
            "evidence-analysis",
            "`lightweight_scout`",
            "`implementation`",
            "`direct`, `micro`, or `batch`",
            "plan_task_authorization",
            "gpt-5.6-luna",
            "max_concurrent_tasks",
            "12,000",
            "pass_parent_transcript",
            "read_only_scout_dispatch",
            "dispatch_scout",
            "no complete parent transcript",
            "without granting writes",
            "finding severity",
            "fact fields",
            "direct PLAN handling",
        }
        for term in sorted(required_adapter_contract_terms):
            if term not in adapter_contract_text:
                errors.append(
                    f"Host Adapter Contract is missing required PLAN-task term: {term}"
                )
        if "discovery_authorization.authorized" in adapter_contract_text:
            errors.append(
                "Host Adapter Contract retains obsolete discovery_authorization authorization semantics"
            )
        if "Phase 1 Scout" in adapter_contract_text:
            errors.append(
                "Host Adapter Contract retains obsolete Phase 1 Scout terminology"
            )
        if example_plan.get("plan_task_authorization", {}).get("model") != PLAN_TASK_MODEL:
            errors.append("example plan must use the approved PLAN-task model")
        if example_plan.get("plan_task_authorization", {}).get("reasoning_effort") != PLAN_TASK_REASONING_EFFORT:
            errors.append("example plan must use the approved PLAN-task reasoning effort")
        if example_plan.get("routing", {}).get("decision") != "batch":
            errors.append("example plan must exercise the validated batch routing path")
        if 'CODEX_HOME' not in skill_text or 'Path.home() / ".codex"' not in skill_text:
            errors.append("Skill deployment guidance must resolve CODEX_HOME before the default Codex root")

    plan_report = validate_plan(example_plan, config_path)
    if not plan_report["valid"]:
        errors.extend(f"example plan: {error}" for error in plan_report["errors"])
    else:
        example_budget = example_plan["budget"]
        token_ceiling = example_plan["plan_task_authorization"]["token_ceiling"]
        max_total = example_budget["max_total_dispatched_tokens"]
        worst_case = plan_report["metrics"]["worst_case_total_input_tokens"]
        if not worst_case <= token_ceiling <= max_total:
            errors.append(
                "example plan token ceiling must satisfy "
                "worst_case_total_input_tokens <= token_ceiling <= "
                "max_total_dispatched_tokens"
            )
        source_map = {source["id"]: source for source in example_plan["sources"]}
        sample_task = example_plan["tasks"][0]
        generated_packet = build_packet(
            example_plan,
            sample_task,
            source_map,
            plan_report["metrics"]["per_task"][sample_task["id"]],
        )
        response_contract = generated_packet["response_contract"]
        check_equal(
            response_contract.get("schema_version"),
            SUPPORTED_SCHEMA_VERSION,
            "generated response schema version",
            errors,
        )
        check_equal(
            response_contract.get("schema_ref"),
            "assets/context-routing/evidence-packet.schema.json",
            "generated response schema reference",
            errors,
        )
        check_equal(
            response_contract.get("validation_authority"),
            "scripts/validate_evidence_packet.py",
            "generated response validation authority",
            errors,
        )
        check_equal(
            response_contract.get("task_kinds"),
            sorted(READ_ONLY_TASK_KINDS),
            "generated response task kinds",
            errors,
        )
        check_equal(
            response_contract.get("finding_severity_values"),
            EVIDENCE_PACKET_FINDING_SEVERITY_VALUES,
            "generated finding severity values",
            errors,
        )
        check_equal(
            response_contract.get("finding_confidence_values"),
            EVIDENCE_PACKET_FINDING_CONFIDENCE_VALUES,
            "generated finding confidence values",
            errors,
        )
        check_equal(
            response_contract.get("evidence_fields"),
            EVIDENCE_PACKET_EVIDENCE_FIELDS,
            "generated evidence fields",
            errors,
        )
        check_equal(
            response_contract.get("fact_fields"),
            EVIDENCE_PACKET_FACT_FIELDS,
            "generated fact fields",
            errors,
        )
        check_equal(
            response_contract.get("fact_confidence_values"),
            EVIDENCE_PACKET_FACT_CONFIDENCE_VALUES,
            "generated fact confidence values",
            errors,
        )
        check_equal(
            response_contract.get("required_fields"),
            EVIDENCE_PACKET_REQUIRED_FIELDS,
            "generated response required fields",
            errors,
        )
        check_equal(
            response_contract.get("optional_fields"),
            EVIDENCE_PACKET_TOP_LEVEL_OPTIONAL_FIELDS,
            "generated response optional fields",
            errors,
        )
        check_equal(
            set(response_contract.get("finding_fields", [])),
            set(EVIDENCE_PACKET_FINDING_FIELDS),
            "generated response finding fields",
            errors,
        )
        check_equal(
            set(response_contract.get("expansion_modes", [])),
            VALID_EXPANSION_MODES,
            "generated response expansion modes",
            errors,
        )

        micro_fixture = {
            "schema_version": SUPPORTED_SCHEMA_VERSION,
            "envelope_type": "micro-task",
            "plan_id": "micro-fixture",
            "task_id": "micro-repository-read",
            "task_kind": "repository-read",
            "goal": "Read one source for a bounded planning fact.",
            "objective": "Identify the configured entry point.",
            "query": "Which function defines the entry point?",
            "sources": [
                {
                    "id": "src-micro",
                    "uri": "src/example.py",
                    "selector": {"type": "symbol", "name": "main"},
                    "estimated_tokens": 120,
                    "purpose": "Entry-point definition",
                }
            ],
            "deliverable": "One cited fact.",
            "stop_conditions": ["The function is located."],
            "evidence_required": True,
            "allowed_expansion": {"mode": "deny", "max_additional_tokens": 0},
            "budget": {
                "estimated_input_tokens": 500,
                "max_input_tokens": 1000,
                "max_result_tokens": 300,
            },
            "economics": {
                "planner_context_savings": 900,
                "delegated_input_tokens": 500,
                "estimated_result_tokens": 120,
                "coordination_overhead_tokens": 200,
                "weighted_cost_savings": 50,
                "weighted_cost_rationale": "The bounded read removes a larger Planner context slice; total tokens may increase.",
                "independently_describable": True,
                "evidence_already_present": False,
                "continuous_planner_judgment": False,
            },
            "plan_task_policy": configured_policy,
            "plan_task_authorization": {
                "authorized": True,
                "model": PLAN_TASK_MODEL,
                "reasoning_effort": PLAN_TASK_REASONING_EFFORT,
                "task_count": 1,
                "token_ceiling": 1000,
            },
            "model_override": {
                "model": PLAN_TASK_MODEL,
                "reasoning_effort": PLAN_TASK_REASONING_EFFORT,
                "explicit": True,
            },
            "response_contract": {
                "schema_version": SUPPORTED_SCHEMA_VERSION,
                "packet_type": "subagent-result",
                "schema_ref": "assets/context-routing/evidence-packet.schema.json",
                "validation_authority": "scripts/validate_evidence_packet.py",
                "task_kinds": sorted(READ_ONLY_TASK_KINDS),
                "finding_severity_values": EVIDENCE_PACKET_FINDING_SEVERITY_VALUES,
                "finding_confidence_values": EVIDENCE_PACKET_FINDING_CONFIDENCE_VALUES,
                "evidence_fields": EVIDENCE_PACKET_EVIDENCE_FIELDS,
                "fact_fields": EVIDENCE_PACKET_FACT_FIELDS,
                "fact_confidence_values": EVIDENCE_PACKET_FACT_CONFIDENCE_VALUES,
            },
            "execution_rules": {
                "read_only": True,
                "write_authority": "none",
                "external_mutations": "forbidden",
                "pass_parent_transcript": False,
                "may_make_decisions": False,
                "may_author_contract": False,
                "may_spawn_agents": False,
            },
        }
        micro_report = validate_micro_task(micro_fixture, config_path)
        if not micro_report["valid"]:
            errors.extend(f"micro fixture: {error}" for error in micro_report["errors"])
        else:
            generated_micro = build_micro_task_packet(
                micro_fixture, micro_report["metrics"]
            )
            check_equal(
                generated_micro.get("packet_type"),
                "plan-task",
                "generated micro packet type",
                errors,
            )
            check_equal(
                generated_micro.get("task_kind"),
                "repository-read",
                "generated micro task kind",
                errors,
            )

        direct_fixture = {
            "schema_version": SUPPORTED_SCHEMA_VERSION,
            "envelope_type": "routing-decision",
            "plan_id": "direct-fixture",
            "goal": "Use evidence already in the Planner context.",
            "routing": {
                "decision": "direct",
                "estimated_files": 1,
                "estimated_tokens": 50,
                "multiple_information_boundaries": False,
                "basis": "The answer is already present.",
                "economics": {
                    "planner_context_savings": 0,
                    "delegated_input_tokens": 0,
                    "estimated_result_tokens": 0,
                    "coordination_overhead_tokens": 200,
                    "weighted_cost_savings": 0,
                    "weighted_cost_rationale": "Direct handling avoids coordination.",
                    "independently_describable": False,
                    "evidence_already_present": True,
                    "continuous_planner_judgment": False,
                },
            },
        }
        direct_report = validate_direct_routing(direct_fixture, config_path)
        if not direct_report["valid"]:
            errors.extend(f"direct fixture: {error}" for error in direct_report["errors"])

    return {
        "valid": not errors,
        "errors": errors,
        "checked": [
            str(schema_path),
            str(evidence_schema_path),
            str(config_path),
            str(example_path),
            str(agent_path),
            str(implementer_path),
            str(adapter_contract_path),
        ],
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="workflow package root",
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=None,
        help="optional APPROVED contract to validate against current workflow resources",
    )
    parser.add_argument("--json", action="store_true", help="print a JSON report")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    report = check_contract_parity(args.root.resolve())
    if args.contract:
        root = args.root.resolve()
        report["errors"].extend(
            validate_approved_contract(
                args.contract.resolve(),
                root,
                root / "references/protocol.md",
                root / "references/adapters/codex.md",
            )
        )
        report["valid"] = not report["errors"]
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        status = "VALID" if report["valid"] else "INVALID"
        print(f"Contract parity: {status}")
        for error in report["errors"]:
            print(f"  - {error}")
    return 0 if report["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
