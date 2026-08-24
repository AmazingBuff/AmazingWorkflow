"""Inspect a C++/CMake project without enforcing a style profile."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence


CODE_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cppm",
    ".cxx",
    ".h",
    ".hh",
    ".hpp",
    ".hxx",
    ".inl",
    ".ipp",
    ".ixx",
    ".tpp",
}
HEADER_SUFFIXES = {".h", ".hh", ".hpp", ".hxx"}
CONFIGURATION_NAMES = {
    ".clang-format": "formatting",
    ".clang-tidy": "static_analysis",
    ".editorconfig": "editor",
    "CMakePresets.json": "cmake_presets",
    "CMakeUserPresets.json": "cmake_user_presets",
    "conanfile.py": "package_management",
    "conanfile.txt": "package_management",
    "vcpkg.json": "package_management",
}
DIRECTORY_ROLES = {
    "applications": {"app", "apps"},
    "benchmarks": {"benchmark", "benchmarks"},
    "documentation": {"doc", "docs"},
    "examples": {"example", "examples", "sample", "samples"},
    "public_headers": {"include", "includes"},
    "sources": {"lib", "libs", "source", "sources", "src"},
    "tests": {"spec", "specs", "test", "tests"},
    "tools": {"tool", "tools"},
}
VENDOR_NAMES = {
    "3rdparty",
    "dependencies",
    "dependency",
    "deps",
    "external",
    "extern",
    "third-party",
    "third_party",
    "vendor",
    "vendors",
}
BUILD_NAMES = {
    "_build",
    "build",
    "dist",
    "install",
    "out",
}
BUILD_MARKERS = {
    "build.ninja",
    "CMakeCache.txt",
    "cmake_install.cmake",
}
TEST_COMMANDS = {
    "add_test",
    "catch_discover_tests",
    "doctest_discover_tests",
    "enable_testing",
    "gtest_discover_tests",
    "gtest_add_tests",
}
DIRECTORY_WIDE_COMMANDS = {
    "add_compile_definitions",
    "add_compile_options",
    "add_definitions",
    "include_directories",
    "link_directories",
    "link_libraries",
}


@dataclass(frozen=True)
class ExcludedDirectory:
    """Describe a directory omitted from first-party inspection."""

    path: str
    role: str
    evidence: str


@dataclass(frozen=True)
class CMakeCommand:
    """Represent one observed CMake command."""

    name: str
    body: str
    path: str
    line: int


@dataclass(frozen=True)
class CMakeTarget:
    """Represent one target declaration."""

    name: str
    kind: str
    path: str
    line: int
    dynamic: bool


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Inspect C++/CMake project structure and conventions without "
            "enforcing them."
        )
    )
    parser.add_argument(
        "project_root",
        type=Path,
        help="Project directory to inspect.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="NAME_OR_PATH",
        help="Additional directory name or relative path to omit.",
    )
    parser.add_argument(
        "--scan-candidates",
        action="store_true",
        help="Include detected build and vendored directories in statistics.",
    )
    return parser.parse_args(argv)


def relative_path(path: Path, root: Path) -> str:
    """Return a deterministic POSIX-style path relative to root."""

    return path.relative_to(root).as_posix() or "."


def is_custom_exclusion(path: Path, root: Path, exclusions: set[str]) -> bool:
    """Return whether a path matches a user-provided exclusion."""

    relative = relative_path(path, root).lower()
    name = path.name.lower()
    return name in exclusions or relative in exclusions


def classify_candidate_directory(path: Path) -> tuple[str, str] | None:
    """Classify a likely build or vendored directory."""

    name = path.name.lower()
    if name in VENDOR_NAMES:
        return ("vendored", f"directory name '{path.name}'")
    if name in BUILD_NAMES or name.startswith("cmake-build-"):
        return ("build", f"directory name '{path.name}'")
    markers = sorted(
        marker for marker in BUILD_MARKERS if (path / marker).is_file()
    )
    if markers:
        return ("build", f"marker file '{markers[0]}'")
    return None


def walk_project(
    root: Path,
    *,
    exclusions: set[str],
    scan_candidates: bool,
) -> tuple[list[Path], list[Path], list[ExcludedDirectory], list[str]]:
    """Walk a project and return inspected files, directories, and notes."""

    files: list[Path] = []
    directories: list[Path] = []
    excluded: list[ExcludedDirectory] = []
    notes: list[str] = []

    for directory, child_names, file_names in os.walk(
        root,
        followlinks=False,
    ):
        directory_path = Path(directory)
        directories.append(directory_path)
        kept_children: list[str] = []
        for child_name in sorted(child_names):
            child_path = directory_path / child_name
            child_relative = relative_path(child_path, root)
            if child_path.is_symlink():
                excluded.append(
                    ExcludedDirectory(
                        child_relative,
                        "symlink",
                        "directory symlinks are not followed",
                    )
                )
                continue
            if child_name.lower() == ".git":
                excluded.append(
                    ExcludedDirectory(
                        child_relative,
                        "metadata",
                        "Git metadata",
                    )
                )
                continue
            if is_custom_exclusion(child_path, root, exclusions):
                excluded.append(
                    ExcludedDirectory(
                        child_relative,
                        "custom",
                        "matched --exclude",
                    )
                )
                continue
            candidate = classify_candidate_directory(child_path)
            if candidate and not scan_candidates:
                role, evidence = candidate
                excluded.append(
                    ExcludedDirectory(child_relative, role, evidence)
                )
                continue
            kept_children.append(child_name)
        child_names[:] = kept_children

        for file_name in sorted(file_names):
            path = directory_path / file_name
            if path.is_symlink():
                notes.append(
                    f"Skipped file symlink: {relative_path(path, root)}"
                )
                continue
            files.append(path)

    return (
        sorted(files),
        sorted(directories),
        sorted(excluded, key=lambda item: (item.path, item.role)),
        sorted(notes),
    )


def read_text(path: Path, root: Path, notes: list[str]) -> str:
    """Read text while recording replacement-decoding events."""

    try:
        raw = path.read_bytes()
    except OSError as error:
        notes.append(
            f"Could not read {relative_path(path, root)}: {error}"
        )
        return ""
    text = raw.decode("utf-8", errors="replace")
    if "\ufffd" in text:
        notes.append(
            f"Decoded with replacement characters: "
            f"{relative_path(path, root)}"
        )
    return text


def detect_header_protection(text: str) -> str:
    """Classify the protection style near the beginning of a header."""

    prefix = "\n".join(text.splitlines()[:120])
    if re.search(r"^\s*#\s*pragma\s+once\b", prefix, re.MULTILINE):
        return "pragma_once"
    guard = re.search(
        r"^\s*#\s*ifndef\s+([A-Za-z_][A-Za-z0-9_]*)\s*$",
        prefix,
        re.MULTILINE,
    )
    if guard:
        name = re.escape(guard.group(1))
        if re.search(
            rf"^\s*#\s*define\s+{name}(?:\s|$)",
            prefix,
            re.MULTILINE,
        ):
            return "macro_guard"
    return "unrecognized"


def scan_cmake_commands(text: str, path: str) -> list[CMakeCommand]:
    """Scan balanced CMake command calls without executing CMake."""

    commands: list[CMakeCommand] = []
    index = 0
    length = len(text)
    while index < length:
        character = text[index]
        if character == "#":
            newline = text.find("\n", index)
            index = length if newline < 0 else newline + 1
            continue
        if not (character.isalpha() or character == "_"):
            index += 1
            continue

        name_start = index
        index += 1
        while index < length and (
            text[index].isalnum() or text[index] == "_"
        ):
            index += 1
        name = text[name_start:index]
        cursor = index
        while cursor < length and text[cursor].isspace():
            cursor += 1
        if cursor >= length or text[cursor] != "(":
            index = cursor
            continue

        line = text.count("\n", 0, name_start) + 1
        body_start = cursor + 1
        cursor = body_start
        depth = 1
        quoted = False
        escaped = False
        while cursor < length and depth:
            current = text[cursor]
            if quoted:
                if escaped:
                    escaped = False
                elif current == "\\":
                    escaped = True
                elif current == '"':
                    quoted = False
            elif current == '"':
                quoted = True
            elif current == "#":
                newline = text.find("\n", cursor)
                if newline < 0:
                    cursor = length
                    break
                cursor = newline
            elif current == "(":
                depth += 1
            elif current == ")":
                depth -= 1
            cursor += 1

        if depth == 0:
            body = text[body_start : cursor - 1]
            commands.append(
                CMakeCommand(name.lower(), body, path, line)
            )
        index = max(cursor, index + 1)
    return commands


def cmake_tokens(body: str) -> list[str]:
    """Extract simple tokens from a CMake command body."""

    pattern = r'"(?:\\.|[^"])*"|[^\s()]+'
    return [token.strip('"') for token in re.findall(pattern, body)]


def inspect_cmake(
    commands: Sequence[CMakeCommand],
) -> dict[str, Any]:
    """Build a neutral summary of observed CMake commands."""

    counts = Counter(command.name for command in commands)
    targets: list[CMakeTarget] = []
    projects: list[dict[str, Any]] = []
    minimum_versions: list[dict[str, Any]] = []
    standards: set[str] = set()
    dependencies: list[dict[str, Any]] = []

    for command in commands:
        tokens = cmake_tokens(command.body)
        if command.name == "project" and tokens:
            projects.append(
                {
                    "name": tokens[0],
                    "path": command.path,
                    "line": command.line,
                }
            )
        elif command.name == "cmake_minimum_required":
            upper_tokens = [token.upper() for token in tokens]
            if "VERSION" in upper_tokens:
                position = upper_tokens.index("VERSION") + 1
                if position < len(tokens):
                    minimum_versions.append(
                        {
                            "value": tokens[position],
                            "path": command.path,
                            "line": command.line,
                        }
                    )
        elif command.name in {"add_library", "add_executable"} and tokens:
            kind = (
                "executable"
                if command.name == "add_executable"
                else "library"
            )
            if command.name == "add_library" and len(tokens) > 1:
                candidate = tokens[1].lower()
                known_kinds = {
                    "alias",
                    "interface",
                    "module",
                    "object",
                    "shared",
                    "static",
                    "unknown",
                }
                if candidate in known_kinds:
                    kind = candidate
            targets.append(
                CMakeTarget(
                    name=tokens[0],
                    kind=kind,
                    path=command.path,
                    line=command.line,
                    dynamic="$" in tokens[0],
                )
            )
        elif command.name in {
            "add_subdirectory",
            "fetchcontent_declare",
            "find_package",
        } and tokens:
            dependencies.append(
                {
                    "mechanism": command.name,
                    "name": tokens[0],
                    "path": command.path,
                    "line": command.line,
                }
            )

        standards.update(re.findall(r"\bcxx_std_\d+\b", command.body))
        if command.name == "set" and len(tokens) > 1:
            if tokens[0].upper() == "CMAKE_CXX_STANDARD":
                standards.add(f"CMAKE_CXX_STANDARD={tokens[1]}")

    target_scoped_count = sum(
        count for name, count in counts.items() if name.startswith("target_")
    )
    directory_wide_count = sum(
        counts[name] for name in DIRECTORY_WIDE_COMMANDS
    )
    return {
        "command_counts": dict(sorted(counts.items())),
        "dependencies": sorted(
            dependencies,
            key=lambda item: (
                item["path"],
                item["line"],
                item["mechanism"],
            ),
        ),
        "directory_wide_command_count": directory_wide_count,
        "minimum_versions": sorted(
            minimum_versions,
            key=lambda item: (item["path"], item["line"]),
        ),
        "projects": sorted(
            projects,
            key=lambda item: (item["path"], item["line"]),
        ),
        "standards": sorted(standards),
        "target_scoped_command_count": target_scoped_count,
        "targets": [
            asdict(target)
            for target in sorted(
                targets,
                key=lambda item: (item.path, item.line, item.name),
            )
        ],
    }


def collect_configuration_files(
    files: Sequence[Path],
    root: Path,
) -> dict[str, list[str]]:
    """Collect known project configuration files."""

    found: dict[str, list[str]] = defaultdict(list)
    for path in files:
        role = CONFIGURATION_NAMES.get(path.name)
        if role:
            found[role].append(relative_path(path, root))
        elif path.name == "CMakeLists.txt" or path.suffix == ".cmake":
            found["cmake"].append(relative_path(path, root))
    return {
        role: sorted(paths)
        for role, paths in sorted(found.items())
    }


def collect_directory_roles(
    directories: Sequence[Path],
    root: Path,
) -> dict[str, list[str]]:
    """Collect directory names that suggest common project roles."""

    roles: dict[str, list[str]] = defaultdict(list)
    for path in directories:
        name = path.name.lower()
        for role, names in DIRECTORY_ROLES.items():
            if name in names:
                roles[role].append(relative_path(path, root))
    return {
        role: sorted(paths)
        for role, paths in sorted(roles.items())
    }


def build_report(
    root: Path,
    *,
    exclusions: set[str],
    scan_candidates: bool,
) -> dict[str, Any]:
    """Inspect a project and return a serializable report."""

    files, directories, excluded, notes = walk_project(
        root,
        exclusions=exclusions,
        scan_candidates=scan_candidates,
    )
    configurations = collect_configuration_files(files, root)
    directory_roles = collect_directory_roles(directories, root)
    extension_counts: Counter[str] = Counter()
    protection_counts: Counter[str] = Counter()
    cmake_commands: list[CMakeCommand] = []
    cmake_files: list[str] = []

    for path in files:
        suffix = path.suffix.lower()
        if suffix in CODE_SUFFIXES:
            extension_counts[suffix] += 1
            if suffix in HEADER_SUFFIXES:
                text = read_text(path, root, notes)
                protection_counts[detect_header_protection(text)] += 1
        if path.name == "CMakeLists.txt" or suffix == ".cmake":
            relative = relative_path(path, root)
            cmake_files.append(relative)
            text = read_text(path, root, notes)
            cmake_commands.extend(scan_cmake_commands(text, relative))

    cmake_report = inspect_cmake(cmake_commands)
    cmake_report["files"] = sorted(cmake_files)
    test_commands = {
        f"{command.path}:{command.line}:{command.name}"
        for command in cmake_commands
        if command.name in TEST_COMMANDS
        or (
            command.name == "include"
            and cmake_tokens(command.body)
            and cmake_tokens(command.body)[0].lower() == "ctest"
        )
    }
    test_evidence = sorted(
        {*directory_roles.get("tests", []), *test_commands}
    )
    example_evidence = sorted(directory_roles.get("examples", []))

    return {
        "schema_version": 1,
        "root": ".",
        "scan": {
            "directories": len(directories),
            "excluded_directories": [
                asdict(item) for item in excluded
            ],
            "files": len(files),
            "notes": sorted(set(notes)),
            "scan_candidates": scan_candidates,
        },
        "configuration_files": configurations,
        "directory_roles": directory_roles,
        "cpp": {
            "extensions": dict(sorted(extension_counts.items())),
            "files": sum(extension_counts.values()),
            "header_protection": dict(
                sorted(protection_counts.items())
            ),
        },
        "cmake": cmake_report,
        "tests": {
            "evidence": test_evidence,
            "present": bool(test_evidence),
        },
        "examples": {
            "evidence": example_evidence,
            "present": bool(example_evidence),
        },
    }


def render_text(report: dict[str, Any]) -> str:
    """Render an inspection report for humans."""

    scan = report["scan"]
    cpp = report["cpp"]
    cmake = report["cmake"]
    lines = [
        "C++/CMake project inspection",
        f"Scanned: {scan['files']} file(s), "
        f"{scan['directories']} directorie(s)",
        f"Excluded directories: "
        f"{len(scan['excluded_directories'])}",
        "",
        "Configuration files:",
    ]
    configurations = report["configuration_files"]
    if configurations:
        for role, paths in configurations.items():
            lines.append(f"  {role}: {', '.join(paths)}")
    else:
        lines.append("  none detected")

    lines.extend(
        [
            "",
            f"C/C++ files: {cpp['files']}",
            "  extensions: "
            + (
                ", ".join(
                    f"{suffix}={count}"
                    for suffix, count in cpp["extensions"].items()
                )
                or "none"
            ),
            "  header protection: "
            + (
                ", ".join(
                    f"{style}={count}"
                    for style, count in cpp["header_protection"].items()
                )
                or "none"
            ),
            "",
            f"CMake files: {len(cmake['files'])}",
            f"  targets: {len(cmake['targets'])}",
            "  standards: "
            + (", ".join(cmake["standards"]) or "none detected"),
            f"  target-scoped commands: "
            f"{cmake['target_scoped_command_count']}",
            f"  directory-wide commands: "
            f"{cmake['directory_wide_command_count']}",
            "",
            "Tests: "
            + ("evidence detected" if report["tests"]["present"] else "none"),
            "Examples: "
            + (
                "evidence detected"
                if report["examples"]["present"]
                else "none"
            ),
        ]
    )
    if scan["notes"]:
        lines.extend(["", "Notes:"])
        lines.extend(f"  {note}" for note in scan["notes"])
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the project inspector."""

    args = parse_args(argv)
    root = args.project_root.resolve()
    if not root.is_dir():
        raise SystemExit(f"Project root is not a directory: {root}")
    exclusions = {
        item.replace("\\", "/").strip("/").lower()
        for item in args.exclude
        if item.strip("/")
    }
    report = build_report(
        root,
        exclusions=exclusions,
        scan_candidates=args.scan_candidates,
    )
    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
