#!/usr/bin/env python3
"""Validate the SKSE plugin template package without external dependencies."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Iterable
from urllib.parse import unquote


REQUIRED_PATHS = {
    "README.md",
    "CHANGELOG.md",
    "skills/skse-plugin-template/SKILL.md",
    "skills/skse-plugin-template/scripts/scaffold.py",
    "skills/skse-plugin-template/templates/CMakeLists.txt",
    "skills/skse-plugin-template/templates/CMakePresets.json",
    "skills/skse-plugin-template/templates/LICENSE",
    "skills/skse-plugin-template/templates/src/CMakeLists.txt",
    "skills/skse-plugin-template/templates/src/main.cpp",
    "skills/skse-plugin-template/references/structure.md",
    "skills/skse-plugin-template/references/patterns.md",
    "skills/skse-plugin-template/references/multi-runtime.md",
    "skills/skse-plugin-template/references/build-and-verify.md",
    "skills/skse-plugin-template/assets/coding-rules/manifest.json",
    "tests/test_scaffold.py",
    "tests/test_validate_package.py",
    "tools/validate_package.py",
}

CANONICAL_SECTIONS = {
    "Purpose",
    "Scope and non-goals",
    "Architecture and data flow",
    "Code map",
    "CLI and generated interfaces",
    "Runtime, build, and license invariants",
    "Failure modes",
    "Dependencies",
    "Tests",
    "Safe modification",
    "Synchronized files",
    "Release history",
}

MARKDOWN_LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def load_scaffold(package_root: Path) -> ModuleType:
    scaffold_path = package_root / "skills/skse-plugin-template/scripts/scaffold.py"
    spec = importlib.util.spec_from_file_location("skse_scaffold_validation", scaffold_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import scaffold module from {scaffold_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_python_artifacts(package_root: Path) -> list[str]:
    errors: list[str] = []
    for cache_directory in sorted(package_root.rglob("__pycache__")):
        if cache_directory.is_dir():
            relative_path = cache_directory.relative_to(package_root).as_posix()
            errors.append(f"Python cache directory is not allowed: {relative_path}")
    for bytecode_file in sorted(package_root.rglob("*.pyc")):
        if bytecode_file.is_file():
            relative_path = bytecode_file.relative_to(package_root).as_posix()
            errors.append(f"Python bytecode file is not allowed: {relative_path}")
    return errors


def validate_manifest(package_root: Path) -> list[str]:
    errors: list[str] = []
    coding_root = package_root / "skills/skse-plugin-template/assets/coding-rules"
    manifest_path = coding_root / "manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"cannot parse coding-rule manifest: {error}"]

    if manifest.get("schema_version") != 1:
        errors.append("coding-rule manifest schema_version must be 1")
    provenance = manifest.get("provenance")
    if not isinstance(provenance, dict) or not all(
        isinstance(provenance.get(field), str) and provenance[field]
        for field in ("source", "baseline_revision", "adaptation")
    ):
        errors.append("coding-rule manifest provenance is incomplete")
    notes = manifest.get("synchronization_notes")
    if not isinstance(notes, list) or not notes or not all(isinstance(note, str) and note for note in notes):
        errors.append("coding-rule manifest synchronization_notes must be a non-empty string list")

    entries = manifest.get("files")
    if not isinstance(entries, list):
        return [*errors, "coding-rule manifest files must be a list"]
    paths = [entry.get("path") for entry in entries if isinstance(entry, dict)]
    if len(paths) != len(entries):
        errors.append("coding-rule manifest contains a non-object file entry")
        return errors
    if len(paths) != len(set(paths)):
        errors.append("coding-rule manifest contains duplicate paths")
    if any(not isinstance(path, str) or "\\" in path or path.startswith("/") for path in paths):
        errors.append("coding-rule manifest paths must be normalized relative POSIX paths")

    expected_paths = {
        path.relative_to(coding_root).as_posix()
        for path in coding_root.rglob("*")
        if path.is_file() and path != manifest_path and "__pycache__" not in path.parts
    }
    manifest_paths = {path for path in paths if isinstance(path, str)}
    for missing in sorted(expected_paths - manifest_paths):
        errors.append(f"coding-rule manifest is missing {missing}")
    for extra in sorted(manifest_paths - expected_paths):
        errors.append(f"coding-rule manifest has extra path {extra}")

    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            continue
        relative_path = entry["path"]
        path = coding_root / relative_path
        if not path.is_file():
            errors.append(f"coding-rule manifest references missing file {relative_path}")
            continue
        expected_hash = entry.get("sha256")
        if not isinstance(expected_hash, str) or re.fullmatch(r"[0-9a-f]{64}", expected_hash) is None:
            errors.append(f"coding-rule manifest has invalid SHA-256 for {relative_path}")
        elif _hash_file(path) != expected_hash:
            errors.append(f"coding-rule manifest hash changed for {relative_path}")
    return errors


def validate_markdown_links(package_root: Path) -> list[str]:
    errors: list[str] = []
    for markdown_path in package_root.rglob("*.md"):
        if "__pycache__" in markdown_path.parts:
            continue
        text = markdown_path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK_PATTERN.findall(text):
            target = target.strip().split(maxsplit=1)[0].strip("<>")
            if not target or target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            relative_target = unquote(target.split("#", 1)[0])
            resolved = (markdown_path.parent / relative_target).resolve()
            if not resolved.exists():
                errors.append(
                    f"broken Markdown link in {markdown_path.relative_to(package_root).as_posix()}: {target}"
                )
    return errors


def _fixture_options(scaffold: ModuleType, output_dir: Path, **overrides: object) -> object:
    values: dict[str, object] = {
        "name": "ValidationPlugin",
        "author": "Template Author",
        "description": 'A "quoted" validation description; reproducible.',
        "version": "1.2.3",
        "runtimes": "all",
        "features": (),
        "baseline": scaffold.DEFAULT_VCPKG_BASELINE,
        "output_dir": output_dir,
        "git_init": False,
        "add_commonlib_submodule": False,
        "generation_date": "1970/01/01",
    }
    values.update(overrides)
    return scaffold.ScaffoldOptions(**values)


def validate_generated_fixtures(package_root: Path, scaffold: ModuleType) -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="skse-template-validation-") as temporary:
        temporary_root = Path(temporary)
        feature_sets = {
            "minimal": (),
            "all": tuple(scaffold.FEATURES),
        }
        for fixture_name, features in feature_sets.items():
            options = _fixture_options(scaffold, temporary_root / fixture_name, features=features)
            try:
                rendered = scaffold.render_project(options)
            except Exception as error:
                errors.append(f"{fixture_name} fixture did not render: {error}")
                continue
            if set(rendered) != scaffold.expected_output_files(features):
                errors.append(f"{fixture_name} fixture file set is inconsistent")
            for relative_path, content in rendered.items():
                if scaffold._placeholder_details(content) or "{{" in content:
                    errors.append(f"{fixture_name}/{relative_path.as_posix()} has unresolved placeholders")
                if relative_path.suffix == ".json":
                    try:
                        json.loads(content)
                    except json.JSONDecodeError as error:
                        errors.append(f"{fixture_name}/{relative_path.as_posix()} is invalid JSON: {error}")

            manifest = json.loads(rendered[Path("vcpkg.json")])
            if manifest.get("dependencies") != scaffold.BASE_VCPKG_DEPENDENCIES:
                errors.append(f"{fixture_name} fixture dependency set differs from CommonLibSSE-NG")
            if manifest.get("builtin-baseline") != scaffold.DEFAULT_VCPKG_BASELINE:
                errors.append(f"{fixture_name} fixture baseline is stale")

            presets = json.loads(rendered[Path("CMakePresets.json")])
            configure_names = {preset["name"] for preset in presets.get("configurePresets", [])}
            build_presets = {preset["name"]: preset for preset in presets.get("buildPresets", [])}
            if "msvc release" not in configure_names:
                errors.append(f"{fixture_name} fixture lacks the msvc release configure preset")
            if build_presets.get("msvc release", {}).get("configurePreset") != "msvc release":
                errors.append(f"{fixture_name} fixture build preset is not linked to its configure preset")

            source_cmake = rendered[Path("src/CMakeLists.txt")]
            main_cpp = rendered[Path("src/main.cpp")]
            if "add_commonlibsse_plugin(" not in source_cmake:
                errors.append(f"{fixture_name} fixture lacks add_commonlibsse_plugin")
            for stale in ("SKSEPlugin_Query", "SKSEPlugin_Version", "RUNTIME_SSE_LATEST", "RUNTIME_SSE_1_6_629"):
                if stale in main_cpp:
                    errors.append(f"{fixture_name} fixture contains stale declaration {stale}")
            if Path(".gitmodules") in rendered:
                errors.append(f"{fixture_name} fixture generated a fake .gitmodules")
            if "GPL-3.0-or-later" not in rendered[Path("LICENSE")]:
                errors.append(f"{fixture_name} fixture lacks GPL-3.0-or-later license text")
            version_resource = rendered[Path("cmake/version.rc.in")]
            if 'VALUE "LegalCopyright", "Copyright (C) @PROJECT_AUTHOR@"' not in version_resource:
                errors.append(f"{fixture_name} fixture has incorrect LegalCopyright metadata")
            if 'VALUE "Comments", "SPDX-License-Identifier: GPL-3.0-or-later"' not in version_resource:
                errors.append(f"{fixture_name} fixture lacks SPDX Comments metadata")
            if 'VALUE "LegalCopyright", "GPL-3.0-or-later"' in version_resource:
                errors.append(f"{fixture_name} fixture puts the license in LegalCopyright")

        try:
            all_rendered = scaffold.render_project(
                _fixture_options(scaffold, temporary_root / "present", features=tuple(scaffold.FEATURES))
            )
        except Exception as error:
            errors.append(f"Present fixture did not render: {error}")
            return errors
        present = all_rendered[Path("src/esp_renderer.cpp")]
        required_present_tokens = (
            "CreateDeferredContext",
            "FinishCommandList",
            "ExecuteCommandList(command_list.Get(), TRUE)",
            "ClearState()",
            "ComPtr<ID3D11Texture2D> back_buffer",
            "ComPtr<ID3D11RenderTargetView> render_target_view",
            "Every per-frame COM reference and command list is released before this call",
        )
        for token in required_present_tokens:
            if token not in present:
                errors.append(f"Present fixture lacks safety invariant: {token}")
        for forbidden in ("g_back_buffer", "g_back_buffer_rtv"):
            if forbidden in present:
                errors.append(f"Present fixture retains forbidden resource: {forbidden}")
        if "Input::poll();" not in present:
            errors.append("all-feature fixture does not invoke Input::poll() from Present")
    return errors


def validate_package(package_root: Path) -> list[str]:
    package_root = package_root.resolve()
    errors = validate_python_artifacts(package_root)
    for relative_path in sorted(REQUIRED_PATHS):
        if not (package_root / relative_path).is_file():
            errors.append(f"required package path is missing: {relative_path}")
    if errors:
        return errors

    scaffold = load_scaffold(package_root)
    template_root = package_root / "skills/skse-plugin-template/templates"
    allowed_placeholders = scaffold.TEMPLATE_VALUE_KEYS.union(scaffold.LINE_PLACEHOLDER_KEYS)
    for template_path in template_root.rglob("*"):
        if not template_path.is_file():
            continue
        text = template_path.read_text(encoding="utf-8")
        try:
            scaffold.validate_template_placeholders(text, allowed_placeholders)
        except scaffold.ScaffoldError as error:
            errors.append(f"{template_path.relative_to(package_root).as_posix()}: {error}")

    if (template_root / ".gitmodules").exists():
        errors.append("templates must not contain a fake .gitmodules")
    source_cmake = (template_root / "src/CMakeLists.txt").read_text(encoding="utf-8")
    presets_text = (template_root / "CMakePresets.json").read_text(encoding="utf-8")
    main_text = (template_root / "src/main.cpp").read_text(encoding="utf-8")
    package_text_paths: Iterable[Path] = [
        package_root / "README.md",
        package_root / "CHANGELOG.md",
        package_root / "skills/skse-plugin-template/SKILL.md",
        *sorted((package_root / "skills/skse-plugin-template/references").glob("*.md")),
        template_root / "README.md",
        template_root / "LICENSE",
        template_root / "cmake/version.rc.in",
    ]
    for path in package_text_paths:
        text = path.read_text(encoding="utf-8")
        if "MIT" in text:
            errors.append(f"stale permissive-license claim in {path.relative_to(package_root).as_posix()}")
    command_documentation = (
        package_root / "README.md",
        package_root / "skills/skse-plugin-template/SKILL.md",
        package_root / "skills/skse-plugin-template/references/build-and-verify.md",
    )
    for path in command_documentation:
        text = path.read_text(encoding="utf-8")
        relative_path = path.relative_to(package_root).as_posix()
        if "compileall" in text:
            errors.append(f"bytecode-producing compileall recommendation remains in {relative_path}")
        for stale_command in ("python -m unittest", "python tools/validate_package.py"):
            if stale_command in text:
                errors.append(f"validation command lacks -B in {relative_path}: {stale_command}")
        for required_command in (
            "python -B -m unittest discover -s tests -v",
            "python -B tools/validate_package.py .",
        ):
            if required_command not in text:
                errors.append(f"documented validation command is missing from {relative_path}: {required_command}")
    for stale in ("CMAKE_CXX_FLAGS", "VS_GLOBAL_VCToolsVersion", "14.44.35207"):
        if stale in source_cmake or stale in presets_text:
            errors.append(f"stale global/toolset setting remains: {stale}")
    for stale in ("SKSEPlugin_Query", "SKSEPlugin_Version", "RUNTIME_SSE_LATEST", "RUNTIME_SSE_1_6_629"):
        if stale in main_text:
            errors.append(f"stale hand-written plugin metadata remains: {stale}")

    canonical_readme = (package_root / "README.md").read_text(encoding="utf-8")
    headings = {
        match.group(1).strip()
        for match in re.finditer(r"^##\s+(.+?)\s*$", canonical_readme, flags=re.MULTILINE)
    }
    for missing_section in sorted(CANONICAL_SECTIONS - headings):
        errors.append(f"canonical README lacks section: {missing_section}")
    for required_reference in (
        "scripts/scaffold.py",
        "tools/validate_package.py",
        "tests/test_scaffold.py",
        "tests/test_validate_package.py",
    ):
        if required_reference not in canonical_readme:
            errors.append(f"canonical README lacks navigation to {required_reference}")

    symbol_requirements = {
        "skills/skse-plugin-template/scripts/scaffold.py": (
            "def main(",
            "def render_project(",
            "def setup_git(",
        ),
        "tools/validate_package.py": ("def main(", "def validate_package(", "def validate_manifest("),
        "tests/test_scaffold.py": ("class ScaffoldTests",),
        "tests/test_validate_package.py": ("class PackageValidatorTests",),
    }
    for relative_path, symbols in symbol_requirements.items():
        source_text = (package_root / relative_path).read_text(encoding="utf-8")
        for symbol in symbols:
            if symbol not in source_text:
                errors.append(f"named entry point {symbol!r} is missing from {relative_path}")

    errors.extend(validate_markdown_links(package_root))
    errors.extend(validate_manifest(package_root))
    errors.extend(validate_generated_fixtures(package_root, scaffold))
    for artifact_error in validate_python_artifacts(package_root):
        if artifact_error not in errors:
            errors.append(artifact_error)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "package_root",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="path to skse-plugin-template-spec",
    )
    args = parser.parse_args(argv)
    errors = validate_package(args.package_root)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        print(f"package validation failed with {len(errors)} error(s)", file=sys.stderr)
        return 1
    print("package validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
