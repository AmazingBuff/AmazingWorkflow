#!/usr/bin/env python3
"""Generate a minimal SKSE plugin; add modules only for concrete requirements."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
import sys
import unicodedata
import feature_support as features

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_DIR / "templates"
TOKEN = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")
RESERVED = frozenset(['alignas', 'alignof', 'and', 'and_eq', 'asm', 'atomic_cancel', 'atomic_commit', 'atomic_noexcept', 'auto', 'bitand', 'bitor', 'bool', 'break', 'case', 'catch', 'char', 'char16_t', 'char32_t', 'char8_t', 'class', 'co_await', 'co_return', 'co_yield', 'compl', 'concept', 'const', 'const_cast', 'consteval', 'constexpr', 'constinit', 'continue', 'decltype', 'default', 'delete', 'do', 'double', 'dynamic_cast', 'else', 'enum', 'explicit', 'export', 'extern', 'false', 'final', 'float', 'for', 'friend', 'goto', 'if', 'import', 'inline', 'int', 'long', 'module', 'mutable', 'namespace', 'new', 'noexcept', 'not', 'not_eq', 'nullptr', 'operator', 'or', 'or_eq', 'override', 'private', 'protected', 'public', 'reflexpr', 'register', 'reinterpret_cast', 'requires', 'return', 'short', 'signed', 'sizeof', 'static', 'static_assert', 'static_cast', 'std', 'struct', 'switch', 'synchronized', 'template', 'this', 'thread_local', 'throw', 'true', 'try', 'typedef', 'typeid', 'typename', 'union', 'unsigned', 'using', 'virtual', 'void', 'volatile', 'wchar_t', 'while', 'xor', 'xor_eq'])
SUBMODULES = (
    ("https://github.com/alandtse/CommonLibSSE-NG.git", "extern/CommonLibSSE"),
)
DEFAULT_BASELINE = "cd61e1e26a038e82d6550a3ebbe0fbbfe7da78e3"


class ScaffoldError(ValueError):
    pass


@dataclass(frozen=True)
class Options:
    name: str
    namespace: str
    author: str
    version: str
    package_version: str
    package_name: str
    display_name: str
    baseline: str
    output_dir: Path
    git_init: bool
    add_submodules: bool
    features: tuple[str, ...] = ()


def one_line(label: str, value: str) -> str:
    if not value.strip() or any(unicodedata.category(c) == "Cc" for c in value):
        raise ScaffoldError(f"{label} must be a nonempty single line")
    if "{{" in value or "}}" in value:
        raise ScaffoldError(f"{label} cannot contain template markers")
    return value


def identifier(label: str, value: str) -> str:
    one_line(label, value)
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value) or value in RESERVED or "__" in value:
        raise ScaffoldError(f"{label} must be a non-reserved C++ identifier")
    return value


def version(value: str) -> str:
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value):
        raise ScaffoldError("version must have three numeric components")
    parts = tuple(map(int, value.split(".")))
    if any(part > limit for part, limit in zip(parts, (255, 255, 4095))):
        raise ScaffoldError("SKSE version limits: major/minor <=255, patch <=4095")
    return ".".join(map(str, parts))


def package_name(name: str) -> str:
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", name)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value)
    return re.sub(r"[-_]+", "-", value).strip("-").lower()


def cmake_argument(value: str) -> str:
    # Preserve the reference's bare-token form for ordinary identifiers.
    if re.fullmatch(r"[A-Za-z0-9_:.-]+", value):
        return value
    value = value.replace("\\", "\\\\").replace('"', '\\"').replace("$", "\\$").replace(";", "\\;")
    return '"' + value + '"'


def render_project(options: Options) -> dict[Path, str]:
    values = {
        "PROJECT_NAME": options.name,
        "PROJECT_VERSION": options.version,
        "NAMESPACE_CMAKE": options.namespace,
        "AUTHOR_CMAKE": cmake_argument(options.author),
        "PROJECT_NAME_LOWER": options.package_name,
        "PACKAGE_VERSION": options.package_version,
        "VCPKG_BASELINE": options.baseline,
        "DISPLAY_NAME": options.display_name,
    }
    result = {}
    source_files = {p.relative_to(TEMPLATE_DIR):p for p in sorted(TEMPLATE_DIR.rglob("*"))
                    if p.is_file() and p.relative_to(TEMPLATE_DIR).parts[0] != "features"}
    for relative, path in features.files(options.features).items():
        if relative in source_files:
            raise ScaffoldError(f"Feature would overwrite base file: {relative}")
        source_files[relative] = path
    integration = features.blocks(options.features)
    for relative, path in source_files.items():
        def replace(match):
            if match[1] not in values:
                raise ScaffoldError(f"Unknown template token {match[0]} in {path.name}")
            return values[match[1]]
        content = features.expand_blocks(path.read_text(encoding="utf-8-sig"), integration)
        result[relative] = TOKEN.sub(replace, content)
    ports = features.entries(options.features, "ports")
    if ports:
        manifest = json.loads(result[Path("vcpkg.json")])
        for port in ports:
            if port not in manifest["dependencies"]:
                manifest["dependencies"].append(port)
        result[Path("vcpkg.json")] = json.dumps(manifest, indent=2) + "\n"
    for url, path in features.submodules(options.features):
        result[Path(".gitmodules")] += f'\n[submodule "{path}"]\n\tpath = {path}\n\turl = {url}\n'
    if options.features:
        result[Path("README.md")] += "\n## Selected features\n\n" + ", ".join(options.features) + "\n"
    for name in ("vcpkg.json", "CMakePresets.json"):
        json.loads(result[Path(name)])
    return result


def setup_git(options: Options) -> None:
    if not (options.git_init or options.add_submodules):
        return
    subprocess.run(["git", "init"], cwd=options.output_dir, check=True)
    if options.add_submodules:
        for url, path in (*SUBMODULES, *features.submodules(options.features)):
            subprocess.run(["git", "submodule", "add", url, path], cwd=options.output_dir, check=True)
        subprocess.run(["git", "submodule", "update", "--init", "--recursive"], cwd=options.output_dir, check=True)


def create_project(options: Options) -> dict[Path, str]:
    dest = options.output_dir
    if dest.is_symlink() or (dest.exists() and (not dest.is_dir() or any(dest.iterdir()))):
        raise ScaffoldError(f"Output must be absent or an empty real directory: {dest}")
    rendered = render_project(options)
    dest.mkdir(parents=True, exist_ok=True)
    for name, content in rendered.items():
        path = dest / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\r\n") as file:
            file.write(content)
    setup_git(options)
    return rendered


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True, help="Project and final namespace component")
    parser.add_argument("--namespace", default="MyPlugins", help="Namespace prefix; e.g. MyPlugins or Company::Mods")
    parser.add_argument("--author", default="Your Name")
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument("--package-version", help="Optional independent manifest version; defaults to --version")
    parser.add_argument("--package-name", help="Optional vcpkg name; otherwise derived from --name")
    parser.add_argument("--display-name", help="Project title in README; defaults to --name")
    parser.add_argument("--baseline", default=DEFAULT_BASELINE)
    parser.add_argument("--dir", help="Empty output directory")
    parser.add_argument("--features", default="", help="Comma-separated optional features (or all/none); dependencies are added automatically: " + ", ".join(features.catalog()))
    parser.add_argument("--git-init", action="store_true", help="Initialize local Git only")
    parser.add_argument("--add-submodules", action="store_true", help="NETWORK: initialize Git, add CommonLib and selected feature submodules")
    return parser


def options_from_args(args: argparse.Namespace) -> Options:
    name = identifier("name", args.name)
    devices = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1,10)), *(f"LPT{i}" for i in range(1,10))}
    if name.upper() in devices:
        raise ScaffoldError("name is a Windows device name")
    namespace = "::".join(identifier("namespace component", part) for part in args.namespace.split("::"))
    author = one_line("author", args.author)
    # Author crosses CMake, configured C++ and RC strings: keep delimiter rules explicit.
    if any(c in author for c in ('"', "\\", ";", "$", "@")):
        raise ScaffoldError("author contains unsupported metadata delimiters")
    display = one_line("display-name", args.display_name or name)
    baseline = args.baseline.lower()
    if not re.fullmatch(r"[0-9a-f]{40}", baseline):
        raise ScaffoldError("baseline must contain exactly 40 hexadecimal characters")
    package = args.package_name or package_name(name)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", package):
        raise ScaffoldError("invalid vcpkg package name")
    output = Path(one_line("dir", args.dir)) if args.dir else Path.cwd() / name
    return Options(name, namespace, author, version(args.version), version(args.package_version or args.version),
                   package, display, baseline, output, args.git_init, args.add_submodules, features.resolve(args.features))


def main(argv=None) -> int:
    try:
        options = options_from_args(build_parser().parse_args(argv))
        rendered = create_project(options)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(f"Generated {len(rendered)} project files at {options.output_dir}")
    print(f"Namespace: {options.namespace}::{options.name}")
    print("Features: " + (", ".join(options.features) or "none"))
    if not options.add_submodules:
        print("Dependency directories must contain actual checkouts; .gitmodules alone is not a gitlink.")
        print("git init")
        for url, path in (*SUBMODULES, *features.submodules(options.features)):
            print(f"git submodule add {url} {path}")
        print("git submodule update --init --recursive")
    print("cmake --preset Release")
    print("cmake --build build --config Release")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
