from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = PACKAGE_ROOT / "tools/validate_package.py"
SPEC = importlib.util.spec_from_file_location("skse_package_validator_tests", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {VALIDATOR_PATH}")
validator = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = validator
SPEC.loader.exec_module(validator)


class PackageValidatorTests(unittest.TestCase):
    def copied_package(self, temporary: str) -> Path:
        destination = Path(temporary) / "package"
        shutil.copytree(
            PACKAGE_ROOT,
            destination,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        return destination

    def test_current_package_passes(self) -> None:
        self.assertEqual(validator.validate_package(PACKAGE_ROOT), [])

    def test_package_rejects_python_cache_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = self.copied_package(temporary)
            cache_directory = package / "tools/__pycache__"
            cache_directory.mkdir()
            errors = validator.validate_package(package)
            self.assertTrue(any("Python cache directory is not allowed" in error for error in errors), errors)

    def test_package_rejects_python_bytecode_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = self.copied_package(temporary)
            bytecode_file = package / "orphan.pyc"
            bytecode_file.write_bytes(b"not bytecode")
            errors = validator.validate_package(package)
            self.assertTrue(any("Python bytecode file is not allowed" in error for error in errors), errors)

    def test_manifest_detects_changed_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = self.copied_package(temporary)
            target = (
                package
                / "skills/skse-plugin-template/assets/coding-rules"
                / "small-project-code-contract/SKILL.md"
            )
            target.write_text(target.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
            errors = validator.validate_manifest(package)
            self.assertTrue(any("hash changed" in error for error in errors), errors)

    def test_manifest_detects_missing_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = self.copied_package(temporary)
            target = (
                package
                / "skills/skse-plugin-template/assets/coding-rules"
                / "small-project-code-contract/SKILL.md"
            )
            target.unlink()
            errors = validator.validate_manifest(package)
            self.assertTrue(any("missing file" in error for error in errors), errors)

    def test_manifest_detects_extra_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = self.copied_package(temporary)
            coding_root = package / "skills/skse-plugin-template/assets/coding-rules"
            (coding_root / "extra.md").write_text("unexpected", encoding="utf-8")
            errors = validator.validate_manifest(package)
            self.assertTrue(any("manifest is missing extra.md" in error for error in errors), errors)

    def test_manifest_detects_duplicate_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = self.copied_package(temporary)
            manifest_path = package / "skills/skse-plugin-template/assets/coding-rules/manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["files"].append(dict(manifest["files"][0]))
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            errors = validator.validate_manifest(package)
            self.assertIn("coding-rule manifest contains duplicate paths", errors)

    def test_validator_rejects_malformed_template_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = self.copied_package(temporary)
            main_path = package / "skills/skse-plugin-template/templates/src/main.cpp"
            main_text = main_path.read_text(encoding="utf-8")
            main_path.write_text(
                main_text.replace("{{ON_LOAD}}", "{ { ON_LOAD } }"),
                encoding="utf-8",
            )
            errors = validator.validate_package(package)
            self.assertTrue(any("malformed spaced" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
