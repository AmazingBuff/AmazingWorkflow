from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD_PATH = PACKAGE_ROOT / "skills/skse-plugin-template/scripts/scaffold.py"
SPEC = importlib.util.spec_from_file_location("skse_scaffold_tests", SCAFFOLD_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {SCAFFOLD_PATH}")
scaffold = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = scaffold
SPEC.loader.exec_module(scaffold)


class ScaffoldTests(unittest.TestCase):
    def options(self, output_dir: Path, **overrides: object) -> object:
        values: dict[str, object] = {
            "name": "ExamplePlugin",
            "author": "Example Author",
            "description": "A deterministic plugin fixture.",
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

    def test_minimal_cli_scaffold_is_offline_and_complete(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "MinimalPlugin"
            environment = dict(os.environ)
            environment["SOURCE_DATE_EPOCH"] = "0"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCAFFOLD_PATH),
                    "--name",
                    "MinimalPlugin",
                    "--dir",
                    str(output_dir),
                ],
                check=False,
                capture_output=True,
                text=True,
                env=environment,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Scaffolded SKSE plugin", result.stdout)
            self.assertIn(
                "git submodule add -b ng https://github.com/alandtse/CommonLibSSE-NG.git extern/CommonLibSSE",
                result.stdout,
            )
            generated = {
                path.relative_to(output_dir)
                for path in output_dir.rglob("*")
                if path.is_file()
            }
            self.assertEqual(generated, scaffold.expected_output_files(()))
            self.assertFalse((output_dir / ".gitmodules").exists())
            self.assertFalse((output_dir / ".git").exists())
            self.assertIn("1970/01/01", (output_dir / "src/main.cpp").read_text(encoding="utf-8"))

    def test_all_runtime_choices_set_authoritative_options(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            for runtime, expected in scaffold.RUNTIMES.items():
                with self.subTest(runtime=runtime):
                    rendered = scaffold.render_project(
                        self.options(Path(temporary) / runtime, runtimes=runtime)
                    )
                    root_cmake = rendered[Path("CMakeLists.txt")]
                    for edition, setting in expected.items():
                        self.assertIn(
                            f'option(ENABLE_SKYRIM_{edition} "Enable support for Skyrim {edition} '
                            f'in the dynamic runtime feature." {setting})',
                            root_cmake,
                        )

    def test_all_features_have_exact_files_dependencies_and_wiring(self) -> None:
        features = tuple(scaffold.FEATURES)
        with tempfile.TemporaryDirectory() as temporary:
            rendered = scaffold.render_project(
                self.options(Path(temporary) / "all", features=features)
            )
        self.assertEqual(set(rendered), scaffold.expected_output_files(features))
        manifest = json.loads(rendered[Path("vcpkg.json")])
        self.assertEqual(manifest["dependencies"], scaffold.BASE_VCPKG_DEPENDENCIES)
        self.assertEqual(manifest["builtin-baseline"], scaffold.DEFAULT_VCPKG_BASELINE)
        self.assertIn("Input::poll();", rendered[Path("src/esp_renderer.cpp")])
        self.assertIn('#include "input.h"', rendered[Path("src/esp_renderer.cpp")])
        self.assertIn("Config::load();", rendered[Path("src/main.cpp")])
        self.assertIn("ESPRenderer::install();", rendered[Path("src/main.cpp")])
        self.assertIn("find_path(SIMPLEINI_INCLUDE_DIR SimpleIni.h REQUIRED)", rendered[Path("src/CMakeLists.txt")])
        self.assertIn("${SIMPLEINI_INCLUDE_DIR}", rendered[Path("src/CMakeLists.txt")])

    def test_name_normalization_and_quoted_description(self) -> None:
        description = 'A "quoted" value; costs $5 and uses C:\\mods.'
        with tempfile.TemporaryDirectory() as temporary:
            rendered = scaffold.render_project(
                self.options(
                    Path(temporary) / "name",
                    name="My__Plugin_2",
                    description=description,
                )
            )
        manifest = json.loads(rendered[Path("vcpkg.json")])
        self.assertEqual(manifest["name"], "my-plugin-2")
        self.assertIn(description, rendered[Path("README.md")])
        self.assertIn(
            r'DESCRIPTION "A \"quoted\" value\; costs \$5 and uses C:\\mods."',
            rendered[Path("CMakeLists.txt")],
        )

    def test_presets_and_modern_commonlib_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            rendered = scaffold.render_project(self.options(Path(temporary) / "modern"))
        presets = json.loads(rendered[Path("CMakePresets.json")])
        configure = {item["name"]: item for item in presets["configurePresets"]}
        build = {item["name"]: item for item in presets["buildPresets"]}
        self.assertIn("msvc release", configure)
        self.assertEqual(build["msvc release"]["configurePreset"], "msvc release")
        source_cmake = rendered[Path("src/CMakeLists.txt")]
        self.assertIn("add_commonlibsse_plugin(", source_cmake)
        self.assertIn('AUTHOR "${PROJECT_AUTHOR}"', source_cmake)
        self.assertIn("USE_ADDRESS_LIBRARY", source_cmake)
        combined = "\n".join(rendered.values())
        for stale in (
            "CMAKE_CXX_FLAGS",
            "VS_GLOBAL_VCToolsVersion",
            "14.44.35207",
            "SKSEPlugin_Query",
            "SKSEPlugin_Version",
            "RUNTIME_SSE_LATEST",
            "RUNTIME_SSE_1_6_629",
        ):
            self.assertNotIn(stale, combined)

    def test_license_resource_and_warning_clean_patterns(self) -> None:
        features = tuple(scaffold.FEATURES)
        with tempfile.TemporaryDirectory() as temporary:
            rendered = scaffold.render_project(
                self.options(Path(temporary) / "license", features=features)
            )
        self.assertIn("GPL-3.0-or-later", rendered[Path("LICENSE")])
        self.assertIn("GPL-3.0-or-later", rendered[Path("README.md")])
        version_resource = rendered[Path("cmake/version.rc.in")]
        self.assertIn(
            'VALUE "LegalCopyright", "Copyright (C) @PROJECT_AUTHOR@"',
            version_resource,
        )
        self.assertIn(
            'VALUE "Comments", "SPDX-License-Identifier: GPL-3.0-or-later"',
            version_resource,
        )
        self.assertNotIn('VALUE "LegalCopyright", "GPL-3.0-or-later"', version_resource)
        self.assertNotIn("MIT", "\n".join(rendered.values()))
        self.assertNotIn("parse_hex", rendered[Path("src/config.cpp")])
        hit_events = rendered[Path("src/hit_events.cpp")]
        self.assertNotIn("a_event", hit_events)
        self.assertNotIn("a_source", hit_events)
        self.assertNotIn("new HitSink", hit_events)
        self.assertIn("HitSink g_sink", hit_events)

    def test_present_hook_uses_deferred_context_and_per_frame_resources(self) -> None:
        features = scaffold.parse_features("config,present_hook,hotkey")
        with tempfile.TemporaryDirectory() as temporary:
            present = scaffold.render_project(
                self.options(Path(temporary) / "present", features=features)
            )[Path("src/esp_renderer.cpp")]
        for required in (
            "CreateDeferredContext",
            "FinishCommandList",
            "ExecuteCommandList(command_list.Get(), TRUE)",
            "ComPtr<ID3D11Texture2D> back_buffer",
            "ComPtr<ID3D11RenderTargetView> render_target_view",
            "g_draw_resources.device.Get() == a_device",
            "g_draw_resources.reset();",
            "return g_original_present",
        ):
            self.assertIn(required, present)
        self.assertNotIn("g_back_buffer", present)
        self.assertNotIn("g_back_buffer_rtv", present)
        self.assertLess(
            present.index("Every per-frame COM reference"),
            present.index("return g_original_present"),
        )

    def test_unknown_and_malformed_placeholders_fail(self) -> None:
        with self.assertRaisesRegex(scaffold.ScaffoldError, "unknown template placeholder"):
            scaffold.substitute("{{NOT_A_KEY}}", {"KNOWN": "value"})
        with self.assertRaisesRegex(scaffold.ScaffoldError, "malformed spaced"):
            scaffold.substitute("{ { KNOWN } }", {"KNOWN": "value"})
        with self.assertRaisesRegex(scaffold.ScaffoldError, "malformed spaced"):
            scaffold.substitute("{{ KNOWN }}", {"KNOWN": "value"})

    def test_invalid_boundaries_are_actionable(self) -> None:
        for name in ("1Plugin", "Plugin-Name", "Plugin Name", "Plugin\nName"):
            with self.subTest(name=name), self.assertRaises(scaffold.ScaffoldError):
                scaffold.validate_project_name(name)
        for baseline in ("abc", "g" * 40, "a" * 39, "a" * 41):
            with self.subTest(baseline=baseline), self.assertRaisesRegex(
                scaffold.ScaffoldError, "40 hexadecimal"
            ):
                scaffold.validate_baseline(baseline)
        self.assertEqual(scaffold.validate_baseline("A" * 40), "a" * 40)
        with self.assertRaisesRegex(scaffold.ScaffoldError, "between 0 and 65535"):
            scaffold.parse_version("1.2.65536")
        for author in ('Bad"Author', r"Bad\Author", "Bad;Author", "Bad$Author", "Bad\nAuthor"):
            with self.subTest(author=author), self.assertRaises(scaffold.ScaffoldError):
                scaffold.validate_author(author)
        for description in ("line one\nline two", "bad\x01value", "{{INJECT}}"):
            with self.subTest(description=description), self.assertRaises(scaffold.ScaffoldError):
                scaffold.validate_description(description)
        with self.assertRaisesRegex(scaffold.ScaffoldError, "unknown features"):
            scaffold.parse_features("unknown")
        with self.assertRaisesRegex(scaffold.ScaffoldError, "duplicate features"):
            scaffold.parse_features("config,config")
        with mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "invalid"}):
            with self.assertRaisesRegex(scaffold.ScaffoldError, "non-negative integer"):
                scaffold.generation_date_from_environment()

    def test_nonempty_output_directory_fails_before_writes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "occupied"
            output_dir.mkdir()
            marker = output_dir / "keep.txt"
            marker.write_text("user data", encoding="utf-8")
            with self.assertRaisesRegex(scaffold.ScaffoldError, "not empty"):
                scaffold.create_project(self.options(output_dir))
            self.assertEqual(marker.read_text(encoding="utf-8"), "user data")
            self.assertEqual(list(output_dir.iterdir()), [marker])

    def test_hotkey_reports_every_missing_dependency(self) -> None:
        with self.assertRaisesRegex(scaffold.ScaffoldError, "config, present_hook"):
            scaffold.parse_features("hotkey")
        with self.assertRaisesRegex(scaffold.ScaffoldError, "present_hook"):
            scaffold.parse_features("config,hotkey")
        with self.assertRaisesRegex(scaffold.ScaffoldError, "config"):
            scaffold.parse_features("present_hook,hotkey")

    def test_legacy_commonlib_is_rejected(self) -> None:
        args = scaffold.build_parser().parse_args(["--name", "Plugin", "--commonlib", "vr"])
        with self.assertRaisesRegex(scaffold.ScaffoldError, "only ng"):
            scaffold.options_from_args(args)

    def test_git_modes_use_exact_argument_arrays(self) -> None:
        output_dir = Path("C:/fixture")
        with mock.patch.object(scaffold.subprocess, "run") as run:
            scaffold.setup_git(output_dir, git_init=False, add_commonlib_submodule=False)
            run.assert_not_called()
        with mock.patch.object(scaffold.subprocess, "run") as run:
            scaffold.setup_git(output_dir, git_init=True, add_commonlib_submodule=False)
            run.assert_called_once_with(["git", "init"], cwd=output_dir, check=True)
        with mock.patch.object(scaffold.subprocess, "run") as run:
            scaffold.setup_git(output_dir, git_init=False, add_commonlib_submodule=True)
            self.assertEqual(
                run.call_args_list,
                [
                    mock.call(["git", "init"], cwd=output_dir, check=True),
                    mock.call(scaffold.COMMONLIB_SUBMODULE_COMMAND, cwd=output_dir, check=True),
                ],
            )

    def test_git_failure_propagates_before_success(self) -> None:
        output_dir = Path("C:/fixture")
        failure = subprocess.CalledProcessError(7, ["git", "init"])
        with mock.patch.object(scaffold.subprocess, "run", side_effect=failure):
            with self.assertRaisesRegex(scaffold.ScaffoldError, "exit 7"):
                scaffold.setup_git(output_dir, git_init=True, add_commonlib_submodule=False)

        submodule_failure = subprocess.CalledProcessError(
            9,
            scaffold.COMMONLIB_SUBMODULE_COMMAND,
        )
        with mock.patch.object(
            scaffold.subprocess,
            "run",
            side_effect=[None, submodule_failure],
        ):
            with self.assertRaisesRegex(scaffold.ScaffoldError, "exit 9"):
                scaffold.setup_git(output_dir, git_init=False, add_commonlib_submodule=True)


if __name__ == "__main__":
    unittest.main()
