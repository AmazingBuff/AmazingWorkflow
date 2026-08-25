from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from tools.validate_package import Issue, validate_package


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class PackageValidatorTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.fixture = Path(self.temporary_directory.name) / "package"
        shutil.copytree(PACKAGE_ROOT, self.fixture)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def validate(self, **kwargs: object) -> list[Issue]:
        return validate_package(self.fixture, **kwargs)

    def assert_issue(self, issues: list[Issue], code: str) -> None:
        self.assertIn(code, {issue.code for issue in issues}, issues)

    def replace(self, relative: str, old: str, new: str) -> None:
        path = self.fixture / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")

    def test_source_package_passes(self) -> None:
        self.assertEqual([], self.validate())

    def test_results_are_deterministic_and_sorted(self) -> None:
        readme = self.fixture / "README.md"
        with readme.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write("\n[missing](not-present.md)\n{{UNRESOLVED_FIXTURE}}\n")
        first = self.validate()
        second = self.validate()
        self.assertEqual(first, second)
        self.assertEqual(sorted(first), first)

    def test_detects_version_drift(self) -> None:
        self.replace(
            "skills/lightweight-coding-workflow/references/protocol.md",
            "Protocol version: `0.5`.",
            "Protocol version: `9.9`.",
        )
        self.assert_issue(self.validate(), "VERSION_DRIFT")

    def test_detects_broken_relative_link(self) -> None:
        readme = self.fixture / "README.md"
        with readme.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write("\n[missing fixture](missing-fixture.md)\n")
        self.assert_issue(self.validate(), "BROKEN_LINK")

    def test_detects_adapter_capability_drift(self) -> None:
        self.replace(
            "skills/lightweight-coding-workflow/references/adapters/codex.md",
            '  - "progress_reporting"\n',
            "",
        )
        self.assert_issue(self.validate(), "ADAPTER_CAPABILITIES")

    def test_detects_invalid_adapter_metadata(self) -> None:
        self.replace(
            "skills/lightweight-coding-workflow/references/adapters/dsh.md",
            'support_state: "EXPERIMENTAL"',
            'support_state: "VERIFIED"',
        )
        self.assert_issue(self.validate(), "ADAPTER_METADATA")

    def test_detects_unresolved_placeholder_outside_templates(self) -> None:
        readme = self.fixture / "README.md"
        with readme.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write("\n{{UNRESOLVED_FIXTURE}}\n")
        self.assert_issue(self.validate(), "UNRESOLVED_PLACEHOLDER")

    def test_detects_feature_documentation_integration_gap(self) -> None:
        self.replace(
            "skills/lightweight-coding-workflow/assets/implementation-contract.md",
            "## Documentation",
            "## Missing documentation fixture",
        )
        self.assert_issue(self.validate(), "FEATURE_DOCUMENTATION_INTEGRATION")

    def test_detects_bundled_rule_hash_drift(self) -> None:
        path = (
            self.fixture
            / "skills/lightweight-coding-workflow/assets/coding-rules/small-project-code-contract/SKILL.md"
        )
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write("\nfixture drift\n")
        self.assert_issue(self.validate(), "MANIFEST_HASH")

    def test_detects_missing_manifested_rule_file(self) -> None:
        path = (
            self.fixture
            / "skills/lightweight-coding-workflow/assets/coding-rules/small-project-python-rules/SKILL.md"
        )
        path.unlink()
        self.assert_issue(self.validate(), "MANIFEST_FILE_SET")

    def test_detects_unmanifested_rule_file(self) -> None:
        path = self.fixture / "skills/lightweight-coding-workflow/assets/coding-rules/extra.md"
        path.write_text("fixture\n", encoding="utf-8", newline="\n")
        self.assert_issue(self.validate(), "MANIFEST_FILE_SET")

    def test_detects_source_install_file_set_drift(self) -> None:
        installed = Path(self.temporary_directory.name) / "installed-skill"
        shutil.copytree(
            self.fixture / "skills/lightweight-coding-workflow",
            installed,
        )
        self.assertEqual([], self.validate(installed_skill=installed))
        (installed / "extra.txt").write_text("fixture\n", encoding="utf-8", newline="\n")
        self.assert_issue(
            self.validate(installed_skill=installed),
            "INSTALL_FILE_SET",
        )

    def test_detects_source_install_content_drift(self) -> None:
        installed = Path(self.temporary_directory.name) / "installed-skill"
        shutil.copytree(
            self.fixture / "skills/lightweight-coding-workflow",
            installed,
        )
        skill = installed / "SKILL.md"
        with skill.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write("\nfixture drift\n")
        self.assert_issue(
            self.validate(installed_skill=installed),
            "INSTALL_CONTENT",
        )

    def test_detects_invalid_agent_toml(self) -> None:
        agent = self.fixture / "agents/lightweight_implementer.toml"
        with agent.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write("\ninvalid = [\n")
        self.assert_issue(self.validate(), "TOML_PARSE")

    def test_detects_invalid_ui_yaml(self) -> None:
        yaml = self.fixture / "skills/lightweight-coding-workflow/agents/openai.yaml"
        with yaml.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write("  - unsupported\n")
        self.assert_issue(self.validate(), "YAML_PARSE")


if __name__ == "__main__":
    unittest.main()
