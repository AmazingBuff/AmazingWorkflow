#!/usr/bin/env python3
"""Generate a validated CommonLibSSE-NG SKSE plugin project."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_DIR / "templates"
FEATURES_DIR = TEMPLATE_DIR / "features"

COMMONLIB_URL = "https://github.com/alandtse/CommonLibSSE-NG.git"
COMMONLIB_BRANCH = "ng"
COMMONLIB_SUBMODULE_COMMAND = [
    "git",
    "submodule",
    "add",
    "-b",
    COMMONLIB_BRANCH,
    COMMONLIB_URL,
    "ext/CommonLibSSE",
]

# CommonLibSSE-NG ng v6.7.0 manifest baseline on 2026-08-25.
DEFAULT_VCPKG_BASELINE = "ee12231b20c95013c6638d845d04c91559a1d1ff"
BASE_VCPKG_DEPENDENCIES: list[object] = [
    {"name": "vcpkg-cmake-config", "host": True},
    {"name": "directxmath", "version>=": "2025-04-03"},
    {"name": "directxtk", "version>=": "2025-10-27"},
    {"name": "fmt", "version>=": "12.1.0"},
    {"name": "nlohmann-json", "version>=": "3.12.0"},
    {"name": "rapidcsv", "version>=": "8.90"},
    {"name": "simpleini", "version>=": "4.25"},
    {"name": "spdlog", "version>=": "1.16.0"},
    {"name": "toml11", "version>=": "4.4.0"},
    {"name": "xbyak", "version>=": "7.28"},
]

RUNTIMES = {
    "all": {"SE": "ON", "AE": "ON", "VR": "ON"},
    "se": {"SE": "ON", "AE": "OFF", "VR": "OFF"},
    "ae": {"SE": "OFF", "AE": "ON", "VR": "OFF"},
    "vr": {"SE": "OFF", "AE": "OFF", "VR": "ON"},
    "se-ae": {"SE": "ON", "AE": "ON", "VR": "OFF"},
    "se-vr": {"SE": "ON", "AE": "OFF", "VR": "ON"},
    "ae-vr": {"SE": "OFF", "AE": "ON", "VR": "ON"},
}

FEATURES = {
    "config": {
        "files": ["src/config.h", "src/config.cpp"],
        "depends": [],
        "cmake_find": ["find_path(SIMPLEINI_INCLUDE_DIR SimpleIni.h REQUIRED)"],
        "include_dirs": ["${SIMPLEINI_INCLUDE_DIR}"],
        "link": [],
        "includes": ['#include "config.h"'],
        "load_glue": ["config::load();"],
        "dataloaded_glue": [],
    },
    "present_hook": {
        "files": ["src/esp_renderer.h", "src/esp_renderer.cpp"],
        "depends": [],
        "cmake_find": ["find_package(directxtk CONFIG REQUIRED)"],
        "include_dirs": [],
        "link": ["Microsoft::DirectXTK", "d3d11", "dxgi"],
        "includes": ['#include "esp_renderer.h"'],
        "load_glue": [],
        "dataloaded_glue": ["esp_renderer::install();"],
    },
    "hotkey": {
        "files": ["src/input.h", "src/input.cpp"],
        "depends": ["config", "present_hook"],
        "cmake_find": [],
        "include_dirs": [],
        "link": [],
        "includes": ['#include "input.h"'],
        "load_glue": [],
        "dataloaded_glue": [],
    },
    "vtable_hook": {
        "files": ["src/hooks.h", "src/hooks.cpp"],
        "depends": [],
        "cmake_find": [],
        "include_dirs": [],
        "link": [],
        "includes": ['#include "hooks.h"'],
        "load_glue": ["hooks::install();"],
        "dataloaded_glue": [],
    },
    "event_sink": {
        "files": ["src/hit_events.h", "src/hit_events.cpp"],
        "depends": [],
        "cmake_find": [],
        "include_dirs": [],
        "link": [],
        "includes": ['#include "hit_events.h"'],
        "load_glue": ["hit_events::install();"],
        "dataloaded_glue": [],
    },
}

PLACEHOLDER_KEY_PATTERN = re.compile(r"[A-Z][A-Z0-9_]*")
PLACEHOLDER_CANDIDATE_PATTERN = re.compile(r"\{\s*\{\s*([^{}\r\n]*?)\s*\}\s*\}")
PROJECT_NAME_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9_]*")
CPP_NAMESPACE_PATTERN = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")
BASELINE_PATTERN = re.compile(r"[0-9A-Fa-f]{40}")
VERSION_PATTERN = re.compile(r"(\d+)\.(\d+)\.(\d+)")
CPP_KEYWORDS = frozenset(
    {
        "alignas",
        "alignof",
        "and",
        "and_eq",
        "asm",
        "atomic_cancel",
        "atomic_commit",
        "atomic_noexcept",
        "auto",
        "bitand",
        "bitor",
        "bool",
        "break",
        "case",
        "catch",
        "char",
        "char8_t",
        "char16_t",
        "char32_t",
        "class",
        "co_await",
        "co_return",
        "co_yield",
        "compl",
        "concept",
        "const",
        "const_cast",
        "consteval",
        "constexpr",
        "constinit",
        "continue",
        "decltype",
        "default",
        "delete",
        "do",
        "double",
        "dynamic_cast",
        "else",
        "enum",
        "explicit",
        "export",
        "extern",
        "false",
        "final",
        "float",
        "for",
        "friend",
        "goto",
        "if",
        "inline",
        "int",
        "import",
        "long",
        "module",
        "mutable",
        "namespace",
        "new",
        "noexcept",
        "not",
        "not_eq",
        "nullptr",
        "operator",
        "or",
        "or_eq",
        "override",
        "private",
        "protected",
        "public",
        "reflexpr",
        "register",
        "reinterpret_cast",
        "requires",
        "return",
        "short",
        "signed",
        "sizeof",
        "static",
        "static_assert",
        "static_cast",
        "struct",
        "switch",
        "synchronized",
        "template",
        "this",
        "thread_local",
        "throw",
        "true",
        "try",
        "typedef",
        "typeid",
        "typename",
        "union",
        "unsigned",
        "using",
        "virtual",
        "void",
        "volatile",
        "wchar_t",
        "while",
        "xor",
        "xor_eq",
    }
)
CPP_RESERVED_NAMESPACE_NAMES = CPP_KEYWORDS.union({"std"})
LINE_PLACEHOLDER_KEYS = frozenset(
    {
        "FEATURE_INCLUDES",
        "ON_LOAD",
        "ON_DATALOADED",
        "RENDERER_EXTRA_INCLUDES",
        "ON_PRESENT_BODY",
        "SOURCE_FILES",
        "HEADER_FILES",
        "FEATURE_FIND_PACKAGES",
        "FEATURE_INCLUDE_DIRECTORIES",
        "FEATURE_LINK_LIBRARIES",
    }
)
TEMPLATE_VALUE_KEYS = frozenset(
    {
        "PROJECT_NAME",
        "PROJECT_NAME_LOWER",
        "PROJECT_NAMESPACE",
        "PROJECT_VERSION",
        "PROJECT_VERSION_MAJOR",
        "PROJECT_VERSION_MINOR",
        "PROJECT_VERSION_PATCH",
        "AUTHOR",
        "AUTHOR_CMAKE",
        "DESCRIPTION",
        "DESCRIPTION_CMAKE",
        "ENABLE_SKYRIM_SE",
        "ENABLE_SKYRIM_AE",
        "ENABLE_SKYRIM_VR",
        "RUNTIME_SELECTION",
        "FEATURE_SELECTION",
        "VCPKG_BASELINE",
        "VCPKG_DEPENDENCIES",
        "DATE",
    }
)


class ScaffoldError(ValueError):
    """An actionable scaffold validation or generation failure."""


@dataclass(frozen=True)
class ScaffoldOptions:
    name: str
    author: str
    description: str
    version: str
    runtimes: str
    features: tuple[str, ...]
    baseline: str
    output_dir: Path
    git_init: bool
    add_commonlib_submodule: bool
    generation_date: str


def _contains_control(value: str) -> bool:
    return any(unicodedata.category(character) == "Cc" for character in value)


def _validate_single_line(label: str, value: str, *, allow_empty: bool = False) -> str:
    if not value and not allow_empty:
        raise ScaffoldError(f"{label} must not be empty")
    if _contains_control(value):
        raise ScaffoldError(f"{label} must be one line and contain no control characters")
    if "{" in value or "}" in value:
        raise ScaffoldError(f"{label} must not contain template delimiters")
    return value


def validate_project_name(name: str) -> str:
    _validate_single_line("name", name)
    if len(name) > 80:
        raise ScaffoldError("name must be 80 characters or fewer")
    if PROJECT_NAME_PATTERN.fullmatch(name) is None:
        raise ScaffoldError("name must match ^[A-Za-z][A-Za-z0-9_]*$ for CMake and C++ identifiers")
    normalize_cpp_namespace(name)
    return name


def normalize_cpp_namespace(name: str) -> str:
    namespace = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    namespace = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", namespace)
    namespace = re.sub(r"_+", "_", namespace.lower()).strip("_")
    if namespace in CPP_RESERVED_NAMESPACE_NAMES:
        namespace += "_plugin"
    if CPP_NAMESPACE_PATTERN.fullmatch(namespace) is None or "__" in namespace:
        raise ScaffoldError(f"name {name!r} cannot be normalized to a safe C++ namespace")
    return namespace


def normalize_vcpkg_name(name: str) -> str:
    normalized = re.sub(r"_+", "-", name.lower()).strip("-")
    if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", normalized) is None:
        raise ScaffoldError(f"name {name!r} cannot be normalized to a valid vcpkg package name")
    return normalized


def validate_author(author: str) -> str:
    _validate_single_line("author", author)
    if len(author) > 120:
        raise ScaffoldError("author must be 120 characters or fewer")
    unsafe = sorted(set(author).intersection({'"', "\\", ";", "$"}))
    if unsafe:
        rendered = ", ".join(repr(character) for character in unsafe)
        raise ScaffoldError(f"author contains characters unsafe for generated CMake/C++ metadata: {rendered}")
    return author


def validate_description(description: str) -> str:
    _validate_single_line("description", description)
    if len(description) > 240:
        raise ScaffoldError("description must be 240 characters or fewer")
    return description


def parse_version(version: str) -> tuple[str, str, str]:
    _validate_single_line("version", version)
    match = VERSION_PATTERN.fullmatch(version)
    if match is None:
        raise ScaffoldError(f"version must look like 1.0.0, got: {version!r}")
    if any(int(component) > 65535 for component in match.groups()):
        raise ScaffoldError("version components must be between 0 and 65535 for Windows VERSIONINFO")
    return match.group(1), match.group(2), match.group(3)


def validate_baseline(baseline: str) -> str:
    _validate_single_line("baseline", baseline)
    if BASELINE_PATTERN.fullmatch(baseline) is None:
        raise ScaffoldError("baseline must be exactly 40 hexadecimal characters")
    return baseline.lower()


def parse_features(raw_features: str) -> tuple[str, ...]:
    _validate_single_line("features", raw_features, allow_empty=True)
    requested = [feature.strip() for feature in raw_features.split(",") if feature.strip()]
    duplicates = sorted({feature for feature in requested if requested.count(feature) > 1})
    if duplicates:
        raise ScaffoldError(f"duplicate features: {', '.join(duplicates)}")
    unknown = sorted(feature for feature in requested if feature not in FEATURES)
    if unknown:
        raise ScaffoldError(f"unknown features: {', '.join(unknown)}; available: {', '.join(FEATURES)}")
    requested_set = set(requested)
    for feature in FEATURES:
        if feature not in requested_set:
            continue
        missing = [dependency for dependency in FEATURES[feature]["depends"] if dependency not in requested_set]
        if missing:
            raise ScaffoldError(
                f"feature '{feature}' requires missing features: {', '.join(missing)} "
                f"(add --features {','.join([*missing, feature])})"
            )
    return tuple(feature for feature in FEATURES if feature in requested_set)


def generation_date_from_environment() -> str:
    source_date_epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if source_date_epoch is None:
        return datetime.now().astimezone().strftime("%Y/%m/%d")
    if re.fullmatch(r"\d+", source_date_epoch) is None:
        raise ScaffoldError("SOURCE_DATE_EPOCH must be a non-negative integer when set")
    try:
        timestamp = datetime.fromtimestamp(int(source_date_epoch), tz=timezone.utc)
    except (OverflowError, OSError, ValueError) as error:
        raise ScaffoldError("SOURCE_DATE_EPOCH is outside the supported timestamp range") from error
    return timestamp.strftime("%Y/%m/%d")


def cmake_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace(";", "\\;")


def _placeholder_details(text: str) -> list[tuple[str, str]]:
    return [(match.group(0), match.group(1).strip()) for match in PLACEHOLDER_CANDIDATE_PATTERN.finditer(text)]


def validate_template_placeholders(text: str, allowed_keys: frozenset[str]) -> None:
    for raw, key in _placeholder_details(text):
        if PLACEHOLDER_KEY_PATTERN.fullmatch(key) is None:
            raise ScaffoldError(f"malformed template placeholder: {raw!r}")
        expected = "{{" + key + "}}"
        if raw != expected:
            raise ScaffoldError(f"malformed spaced template placeholder {raw!r}; use {expected!r}")
        if key not in allowed_keys:
            raise ScaffoldError(f"unknown template placeholder: {expected}")


def substitute(text: str, values: dict[str, str], ignore: frozenset[str] = frozenset()) -> str:
    validate_template_placeholders(text, frozenset(values).union(ignore))
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    leftovers = [raw for raw, key in _placeholder_details(text) if key not in ignore]
    if leftovers:
        raise ScaffoldError(f"unsubstituted template placeholders: {sorted(set(leftovers))}")
    return text


def substitute_lines(content: str, replacements: dict[str, list[str]]) -> str:
    result: list[str] = []
    for line in content.splitlines(keepends=True):
        stripped = line.strip()
        matching_key = next((key for key in replacements if stripped == "{{" + key + "}}"), None)
        if matching_key is None:
            result.append(line)
            continue
        indent = line[: len(line) - len(line.lstrip())]
        block = "\n".join(indent + replacement for replacement in replacements[matching_key])
        result.append(block + ("\n" if line.endswith("\n") else ""))
    rendered = "".join(result)
    if _placeholder_details(rendered) or "{{" in rendered:
        raise ScaffoldError("unsubstituted template placeholder remains after line substitution")
    return rendered


def expected_output_files(features: Sequence[str]) -> set[Path]:
    files = {
        Path(".gitignore"),
        Path("CMakeLists.txt"),
        Path("CMakePresets.json"),
        Path("LICENSE"),
        Path("README.md"),
        Path("vcpkg.json"),
        Path("cmake/plugin_version.h.in"),
        Path("cmake/packaging.cmake"),
        Path("cmake/version.rc.in"),
        Path("src/CMakeLists.txt"),
        Path("src/main.cpp"),
        Path("src/pch.h"),
    }
    for feature in features:
        files.update(Path(path) for path in FEATURES[feature]["files"])
    return files


def _dependency_json_body() -> str:
    lines = json.dumps(BASE_VCPKG_DEPENDENCIES, indent=2).splitlines()
    return "\n".join("  " + line for line in lines[1:-1])


def render_project(options: ScaffoldOptions) -> dict[Path, str]:
    major, minor, patch = parse_version(options.version)
    project_namespace = normalize_cpp_namespace(options.name)
    runtime_values = RUNTIMES[options.runtimes]
    includes: list[str] = ['#include "plugin.h"']
    load_glue: list[str] = []
    dataloaded_glue: list[str] = []
    source_files = ["${source_dir}/main.cpp"]
    header_files = ["${source_dir}/pch.h"]
    find_packages = ["find_package(fmt CONFIG REQUIRED)", "find_package(spdlog CONFIG REQUIRED)"]
    include_directories: list[str] = []
    link_libraries = ["fmt::fmt", "spdlog::spdlog"]
    for feature in options.features:
        includes.extend(FEATURES[feature]["includes"])
        load_glue.extend(
            f"::{project_namespace}::{statement}" for statement in FEATURES[feature]["load_glue"]
        )
        dataloaded_glue.extend(
            f"::{project_namespace}::{statement}" for statement in FEATURES[feature]["dataloaded_glue"]
        )
        for relative_path in FEATURES[feature]["files"]:
            generated_path = "${source_dir}/" + relative_path.split("/", 1)[1]
            (source_files if relative_path.endswith(".cpp") else header_files).append(generated_path)
        find_packages.extend(FEATURES[feature]["cmake_find"])
        include_directories.extend(FEATURES[feature]["include_dirs"])
        link_libraries.extend(FEATURES[feature]["link"])
    hotkey_enabled = "hotkey" in options.features
    line_values = {
        "FEATURE_INCLUDES": sorted(dict.fromkeys(includes)),
        "ON_LOAD": load_glue,
        "ON_DATALOADED": dataloaded_glue,
        "RENDERER_EXTRA_INCLUDES": ['#include "input.h"'] if hotkey_enabled else [],
        "ON_PRESENT_BODY": [f"::{project_namespace}::input::poll();"] if hotkey_enabled else [],
        "SOURCE_FILES": source_files,
        "HEADER_FILES": header_files,
        "FEATURE_FIND_PACKAGES": list(dict.fromkeys(find_packages)),
        "FEATURE_INCLUDE_DIRECTORIES": list(dict.fromkeys(include_directories)),
        "FEATURE_LINK_LIBRARIES": list(dict.fromkeys(link_libraries)),
    }
    values = {
        "PROJECT_NAME": options.name,
        "PROJECT_NAME_LOWER": normalize_vcpkg_name(options.name),
        "PROJECT_NAMESPACE": project_namespace,
        "PROJECT_VERSION": options.version,
        "PROJECT_VERSION_MAJOR": major,
        "PROJECT_VERSION_MINOR": minor,
        "PROJECT_VERSION_PATCH": patch,
        "AUTHOR": options.author,
        "AUTHOR_CMAKE": cmake_escape(options.author),
        "DESCRIPTION": options.description,
        "DESCRIPTION_CMAKE": cmake_escape(options.description),
        "ENABLE_SKYRIM_SE": runtime_values["SE"],
        "ENABLE_SKYRIM_AE": runtime_values["AE"],
        "ENABLE_SKYRIM_VR": runtime_values["VR"],
        "RUNTIME_SELECTION": options.runtimes,
        "FEATURE_SELECTION": ", ".join(options.features) if options.features else "none",
        "VCPKG_BASELINE": options.baseline,
        "VCPKG_DEPENDENCIES": _dependency_json_body(),
        "DATE": options.generation_date,
    }
    if frozenset(values) != TEMPLATE_VALUE_KEYS:
        raise ScaffoldError("internal template value key set is inconsistent")

    def read_template(relative_path: str) -> str:
        try:
            return (TEMPLATE_DIR / relative_path).read_text(encoding="utf-8")
        except OSError as error:
            raise ScaffoldError(f"cannot read template {relative_path}: {error}") from error

    rendered: dict[Path, str] = {}
    for relative_path in ["CMakeLists.txt", "CMakePresets.json", "vcpkg.json", "README.md", "LICENSE", ".gitignore"]:
        rendered[Path(relative_path)] = substitute(read_template(relative_path), values)
    for filename in ["packaging.cmake", "plugin_version.h.in", "version.rc.in"]:
        relative_path = f"cmake/{filename}"
        rendered[Path(relative_path)] = substitute(read_template(relative_path), values)

    line_templates = {
        "src/main.cpp": ("FEATURE_INCLUDES", "ON_LOAD", "ON_DATALOADED"),
        "src/CMakeLists.txt": (
            "SOURCE_FILES",
            "HEADER_FILES",
            "FEATURE_FIND_PACKAGES",
            "FEATURE_INCLUDE_DIRECTORIES",
            "FEATURE_LINK_LIBRARIES",
        ),
    }
    for relative_path, keys in line_templates.items():
        content = substitute(read_template(relative_path), values, LINE_PLACEHOLDER_KEYS)
        rendered[Path(relative_path)] = substitute_lines(content, {key: line_values[key] for key in keys})
    rendered[Path("src/pch.h")] = substitute(read_template("src/pch.h"), values)

    for feature in options.features:
        for relative_path in FEATURES[feature]["files"]:
            feature_template = FEATURES_DIR / feature / relative_path
            try:
                content = feature_template.read_text(encoding="utf-8")
            except OSError as error:
                raise ScaffoldError(f"cannot read feature template {feature}/{relative_path}: {error}") from error
            ignored = (
                frozenset({"RENDERER_EXTRA_INCLUDES", "ON_PRESENT_BODY"})
                if feature == "present_hook"
                else frozenset()
            )
            content = substitute(content, values, ignored)
            if feature == "present_hook" and relative_path.endswith("esp_renderer.cpp"):
                content = substitute_lines(
                    content,
                    {
                        "RENDERER_EXTRA_INCLUDES": line_values["RENDERER_EXTRA_INCLUDES"],
                        "ON_PRESENT_BODY": line_values["ON_PRESENT_BODY"],
                    },
                )
            rendered[Path(relative_path)] = content

    for relative_path, content in rendered.items():
        if _placeholder_details(content) or "{{" in content:
            raise ScaffoldError(f"generated {relative_path.as_posix()} contains unresolved template syntax")
    if set(rendered) != expected_output_files(options.features):
        raise ScaffoldError("internal generated file set does not match the selected features")
    try:
        json.loads(rendered[Path("CMakePresets.json")])
        json.loads(rendered[Path("vcpkg.json")])
    except json.JSONDecodeError as error:
        raise ScaffoldError(f"generated JSON is invalid: {error}") from error
    return rendered


def _prepare_output_directory(output_dir: Path) -> None:
    if output_dir.exists():
        if output_dir.is_symlink():
            raise ScaffoldError(f"output directory must not be a symbolic link: {output_dir}")
        if not output_dir.is_dir():
            raise ScaffoldError(f"output path is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            raise ScaffoldError(f"output directory not empty: {output_dir}")


def write_project(output_dir: Path, rendered: dict[Path, str]) -> None:
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        for relative_path in sorted(rendered, key=lambda path: path.as_posix()):
            path = output_dir / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("x", encoding="utf-8", newline="\r\n") as output_file:
                output_file.write(rendered[relative_path])
    except OSError as error:
        raise ScaffoldError(f"failed to write scaffold at {output_dir}: {error}") from error


def setup_git(output_dir: Path, *, git_init: bool, add_commonlib_submodule: bool) -> None:
    if not git_init and not add_commonlib_submodule:
        return
    try:
        subprocess.run(["git", "init"], cwd=output_dir, check=True)
        if add_commonlib_submodule:
            subprocess.run(COMMONLIB_SUBMODULE_COMMAND, cwd=output_dir, check=True)
    except FileNotFoundError as error:
        raise ScaffoldError("git executable was not found; install Git or omit the Git option") from error
    except subprocess.CalledProcessError as error:
        command = subprocess.list2cmdline(error.cmd)
        raise ScaffoldError(f"Git command failed with exit {error.returncode}: {command}") from error


def create_project(options: ScaffoldOptions) -> dict[Path, str]:
    _prepare_output_directory(options.output_dir)
    rendered = render_project(options)
    write_project(options.output_dir, rendered)
    setup_git(
        options.output_dir,
        git_init=options.git_init,
        add_commonlib_submodule=options.add_commonlib_submodule,
    )
    return rendered


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a CommonLibSSE-NG Skyrim SE/AE/VR plugin.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Available --features (comma separated): " + ", ".join(FEATURES) + "\n"
            "Available --runtimes: " + ", ".join(RUNTIMES)
        ),
    )
    parser.add_argument(
        "--name",
        required=True,
        help="safe CMake/C++ identifier; also derives a lowercase snake_case namespace",
    )
    parser.add_argument("--author", default="Your Name", help="author for generated plugin metadata")
    parser.add_argument("--description", default="A Skyrim SKSE plugin.", help="one-line project description")
    parser.add_argument("--version", default="1.0.0", help="three-part version such as 1.0.0")
    parser.add_argument("--runtimes", default="all", choices=sorted(RUNTIMES), help="runtime set compiled into the DLL")
    parser.add_argument("--features", default="", help="comma-separated feature modules")
    parser.add_argument(
        "--commonlib",
        default="ng",
        help="CommonLib implementation; only ng from alandtse/CommonLibSSE-NG is supported",
    )
    parser.add_argument("--baseline", default=DEFAULT_VCPKG_BASELINE, help="40-hex vcpkg builtin baseline")
    parser.add_argument("--dir", default=None, help="empty output directory (default: ./<name>)")
    parser.add_argument("--git-init", action="store_true", help="run local-only git init; performs no network access")
    parser.add_argument(
        "--add-commonlib-submodule",
        action="store_true",
        help="NETWORK: initialize Git and add CommonLibSSE-NG branch ng as a real submodule",
    )
    return parser


def options_from_args(args: argparse.Namespace) -> ScaffoldOptions:
    name = validate_project_name(args.name)
    author = validate_author(args.author)
    description = validate_description(args.description)
    parse_version(args.version)
    baseline = validate_baseline(args.baseline)
    if args.commonlib != "ng":
        raise ScaffoldError(
            "--commonlib supports only ng from alandtse/CommonLibSSE-NG; the legacy VR fork is unsupported"
        )
    if args.dir is not None:
        _validate_single_line("dir", args.dir)
    return ScaffoldOptions(
        name=name,
        author=author,
        description=description,
        version=args.version,
        runtimes=args.runtimes,
        features=parse_features(args.features),
        baseline=baseline,
        output_dir=Path(args.dir) if args.dir else Path.cwd() / name,
        git_init=args.git_init,
        add_commonlib_submodule=args.add_commonlib_submodule,
        generation_date=generation_date_from_environment(),
    )


def print_summary(options: ScaffoldOptions) -> None:
    runtime_values = RUNTIMES[options.runtimes]
    print(f"Scaffolded SKSE plugin at: {options.output_dir}")
    print(f"  name:      {options.name}")
    print(f"  package:   {normalize_vcpkg_name(options.name)}")
    print(f"  namespace: {normalize_cpp_namespace(options.name)}")
    print(f"  author:    {options.author}")
    print(f"  version:   {options.version}")
    print(
        f"  runtimes:  {options.runtimes} "
        f"(SE={runtime_values['SE']}, AE={runtime_values['AE']}, VR={runtime_values['VR']})"
    )
    print(f"  commonlib: {COMMONLIB_URL} (branch {COMMONLIB_BRANCH})")
    print(f"  features:  {', '.join(options.features) if options.features else '(none)'}")
    print("\nNext steps:")
    print(f"  cd {options.output_dir}")
    if not options.git_init and not options.add_commonlib_submodule:
        print("  git init")
    if not options.add_commonlib_submodule:
        print("  " + subprocess.list2cmdline(COMMONLIB_SUBMODULE_COMMAND))
    print("  git submodule update --init --recursive")
    print('  cmake --preset "msvc debug"')
    print('  cmake --build --preset "msvc debug"')
    print('  cmake --preset "msvc release"')
    print('  cmake --build --preset "msvc release"')
    if options.add_commonlib_submodule:
        print("  commit both .gitmodules and the ext/CommonLibSSE gitlink")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        options = options_from_args(args)
        create_project(options)
    except (OSError, ScaffoldError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print_summary(options)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
