from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUITE = json.loads((ROOT / "suite.json").read_text(encoding="utf-8"))
TOKENS = {
    "{{STRONG_MODEL}}": "strong_model",
    "{{STRONG_VARIANT}}": "strong_variant",
    "{{EXECUTION_MODEL}}": "execution_model",
    "{{EXECUTION_VARIANT}}": "execution_variant",
    "{{STRONG_THINKING}}": "strong_thinking",
    "{{EXECUTION_THINKING}}": "execution_thinking",
}
PI_THINKING_LEVELS = {"off", "minimal", "low", "medium", "high", "xhigh", "max"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_skill(source: Path, destination: Path, harness: str) -> None:
    shutil.copytree(source, destination)
    if harness != "codex":
        metadata = destination / "agents"
        if metadata.exists():
            shutil.rmtree(metadata)

    if harness == "pi" and source.name != "small-project-workflow":
        skill_path = destination / "SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        marker = "---\n"
        second = text.find(marker, len(marker))
        if second < 0:
            raise ValueError(f"invalid frontmatter: {skill_path}")
        text = text[:second] + "disable-model-invocation: true\n" + text[second:]
        skill_path.write_text(text, encoding="utf-8", newline="\n")


def render_template(source: Path, destination: Path, values: dict[str, str]) -> None:
    text = source.read_text(encoding="utf-8")
    for token, key in TOKENS.items():
        if token in text:
            value = values.get(key, "")
            if not value:
                raise ValueError(f"missing value for {token} used by {source}")
            text = text.replace(token, value)
    if "{{" in text or "}}" in text:
        raise ValueError(f"unresolved template token in {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8", newline="\n")


def validate_output_path(output: Path) -> None:
    anchor = Path(output.anchor).resolve()
    if output == anchor or output == Path.home().resolve():
        raise ValueError(f"unsafe output path: {output}")
    if len(output.parts) < 3:
        raise ValueError(f"output path is too broad: {output}")


def build(args: argparse.Namespace, staging: Path) -> None:
    harness = args.harness
    config_root = staging / (".opencode" if harness == "opencode" else ".pi")
    skills_root = config_root / "skills"
    skills_root.mkdir(parents=True)
    for name in SUITE["skills"]:
        copy_skill(ROOT / "skills" / name, skills_root / name, harness)

    spec_source = ROOT / SUITE["spec"]
    embedded_spec = skills_root / "small-project-workflow" / "references" / "SPEC.md"
    embedded_spec.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(spec_source, embedded_spec)

    values = {
        "strong_model": args.strong_model,
        "strong_variant": args.strong_variant,
        "execution_model": args.execution_model,
        "execution_variant": args.execution_variant,
        "strong_thinking": args.strong_thinking,
        "execution_thinking": args.execution_thinking,
    }
    adapter = ROOT / "adapters" / harness
    for template in sorted((adapter / "agents").glob("*.md.tmpl")):
        render_template(template, config_root / "agents" / template.name.removesuffix(".tmpl"), values)

    if harness == "opencode":
        shutil.copytree(adapter / "commands", config_root / "commands")
    else:
        shutil.copytree(adapter / "prompts", config_root / "prompts")
        shutil.copytree(adapter / "extensions", config_root / "extensions")

    files = {
        path.relative_to(staging).as_posix(): sha256(path)
        for path in sorted(staging.rglob("*"))
        if path.is_file()
    }
    manifest = {
        "schema_version": 1,
        "suite": SUITE["name"],
        "suite_version": SUITE["version"],
        "harness": harness,
        "skills": SUITE["skills"],
        "spec_sha256": sha256(spec_source),
        "embedded_spec_sha256": sha256(embedded_spec),
        "model_roles": {
            "decision_strong": {"model": args.strong_model, "reasoning": args.strong_variant or args.strong_thinking},
            "review_strong_isolated": {
                "model": args.strong_model,
                "reasoning": args.strong_variant or args.strong_thinking,
                "isolated": True,
                "read_only": True,
            },
            "execution_bounded": {
                "model": args.execution_model,
                "reasoning": args.execution_variant or args.execution_thinking,
            },
            "report_bounded": {
                "model": args.execution_model,
                "reasoning": args.execution_variant or args.execution_thinking,
            },
        },
        "model_availability": "caller-asserted; runtime-unverified",
        "capabilities": {
            "isolated_subagents": True,
            "role_model_selection": True,
            "review_read_only": True,
            "live_discovery_verified": False,
        },
        "files": files,
    }
    (staging / ".small-project-workflow-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a project-local small-project workflow bundle.")
    parser.add_argument("--harness", required=True, choices=("opencode", "pi"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--force", action="store_true", help="Replace an existing output directory after validation.")
    parser.add_argument("--strong-model", required=True, help="Verified provider/model identifier for strong roles.")
    parser.add_argument("--execution-model", required=True, help="Verified provider/model identifier for bounded roles.")
    parser.add_argument("--strong-variant", default="")
    parser.add_argument("--execution-variant", default="")
    parser.add_argument("--strong-thinking", default="")
    parser.add_argument("--execution-thinking", default="")
    args = parser.parse_args()
    if args.harness == "opencode" and (not args.strong_variant or not args.execution_variant):
        parser.error("OpenCode requires --strong-variant and --execution-variant")
    if args.harness == "pi" and (not args.strong_thinking or not args.execution_thinking):
        parser.error("Pi requires --strong-thinking and --execution-thinking")
    if args.harness == "pi":
        for value in (args.strong_thinking, args.execution_thinking):
            if value not in PI_THINKING_LEVELS:
                parser.error(f"unsupported Pi thinking level: {value}")
    return args


def main() -> int:
    args = parse_args()
    output = args.output.resolve()
    validate_output_path(output)
    if output.exists() and not args.force:
        print(f"refusing to replace existing output: {output}", file=sys.stderr)
        return 2
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="spw-build-", dir=output.parent) as temp:
        staging = Path(temp) / "bundle"
        staging.mkdir()
        build(args, staging)
        if output.exists():
            if not output.is_dir() or output.is_symlink():
                raise ValueError(f"refusing to replace a non-directory or symlink: {output}")
            manifest = output / ".small-project-workflow-manifest.json"
            if not manifest.is_file():
                raise ValueError(f"refusing to replace unowned directory without bundle manifest: {output}")
            shutil.rmtree(output)
        shutil.move(str(staging), str(output))
    print(f"built {args.harness} bundle: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
