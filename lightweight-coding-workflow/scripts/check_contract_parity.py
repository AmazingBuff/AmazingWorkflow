#!/usr/bin/env python3
"""Check that the routing schema, validator, config, packets, and Agent agree."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from build_task_packets import build_packet
from validate_evidence_packet import (
    EVIDENCE_PACKET_FINDING_FIELDS,
    EVIDENCE_PACKET_REQUIRED_FIELDS,
    EVIDENCE_PACKET_TOP_LEVEL_OPTIONAL_FIELDS,
)
from validate_plan import (
    DEFAULT_CONFIG_RELATIVE_PATH,
    REQUIRED_BUDGET_FIELDS,
    REQUIRED_TASK_FIELDS,
    REQUIRED_TOP_LEVEL_FIELDS,
    SUPPORTED_SCHEMA_VERSION,
    VALID_EXPANSION_MODES,
    VALID_MODES,
    load_effective_config,
    load_plan,
    sha256_text_normalized,
    validate_plan,
)

PLAN_SCHEMA_ID = "urn:lightweight-coding-workflow:orchestration-plan-schema:1.1"
EVIDENCE_SCHEMA_ID = "urn:lightweight-coding-workflow:evidence-packet-schema:1.1"
WORKFLOW_REVISION = "0.6.2"
CORE_PROTOCOL_VERSION = "0.6"
CODEX_ADAPTER_VERSION = "0.6"
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
    template_path = root / "assets/implementation-contract.md"
    skill_path = root / "SKILL.md"
    protocol_path = root / "references/protocol.md"
    adapter_path = root / "references/adapters/codex.md"

    try:
        plan_schema = load_json(schema_path)
        evidence_schema = load_json(evidence_schema_path)
        config = load_effective_config(config_path)
        example_plan = load_plan(example_path)
    except (TypeError, ValueError) as exc:
        return {"valid": False, "errors": [str(exc)]}

    check_equal(
        plan_schema.get("properties", {}).get("schema_version", {}).get("const"),
        SUPPORTED_SCHEMA_VERSION,
        "plan schema_version",
        errors,
    )
    check_equal(plan_schema.get("$id"), PLAN_SCHEMA_ID, "plan schema id", errors)
    check_equal(
        set(plan_schema.get("required", [])),
        REQUIRED_TOP_LEVEL_FIELDS,
        "plan required fields",
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
    except (OSError, UnicodeError) as exc:
        errors.append(f"unable to read Scout Agent: {agent_path}: {exc}")
    else:
        if 'sandbox_mode = "read-only"' not in agent_text:
            errors.append("Scout Agent does not declare sandbox_mode = 'read-only'")
        if "bounded" in agent_text:
            errors.append("Scout Agent mentions the forbidden bounded expansion mode")

    try:
        template_text = template_path.read_text(encoding="utf-8")
        skill_text = skill_path.read_text(encoding="utf-8")
        protocol_text = protocol_path.read_text(encoding="utf-8")
        adapter_text = adapter_path.read_text(encoding="utf-8")
        adapter_meta = read_adapter_front_matter(adapter_path)
        config_text = config_path.read_text(encoding="utf-8")
        example_text = example_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(f"contract parity source read failed: {exc}")
    else:
        validate_adapter_metadata(
            adapter_meta,
            errors,
            expected_adapter_version=CODEX_ADAPTER_VERSION,
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
        if "gpt-5.4-mini" in config_text or "gpt-5.4-mini" in example_text:
            errors.append("host-specific scout model defaults must not appear in config or examples")
        if example_plan.get("discovery_authorization", {}).get("scout_model") != "user-approved-scout-model":
            errors.append("example plan must use a non-catalog user-approved scout model placeholder")
        if 'CODEX_HOME' not in skill_text or 'Path.home() / ".codex"' not in skill_text:
            errors.append("Skill deployment guidance must resolve CODEX_HOME before the default Codex root")

    plan_report = validate_plan(example_plan, config_path)
    if not plan_report["valid"]:
        errors.extend(f"example plan: {error}" for error in plan_report["errors"])
    else:
        example_budget = example_plan["budget"]
        token_ceiling = example_plan["discovery_authorization"]["token_ceiling"]
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

    return {
        "valid": not errors,
        "errors": errors,
        "checked": [
            str(schema_path),
            str(evidence_schema_path),
            str(config_path),
            str(example_path),
            str(agent_path),
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
