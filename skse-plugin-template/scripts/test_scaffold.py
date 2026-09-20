#!/usr/bin/env python3
"""Offline generator regressions. No Git, downloads, compiler, or game needed."""
import itertools
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import scaffold as s


def options(*args):
    return s.options_from_args(s.build_parser().parse_args(['--name', 'TestPlugin', *args]))


class ScaffoldTests(unittest.TestCase):
    def test_direct_project_tree_and_default_modules(self):
        all_files = {p.relative_to(s.TEMPLATE_DIR) for p in s.TEMPLATE_DIR.rglob('*') if p.is_file()}
        self.assertEqual(all_files, s.expected_output_files(tuple(s.FEATURES)))
        default = s.render_project(options())
        self.assertIn(Path('src/config/config.cpp'), default)
        self.assertIn(Path('src/input/input.cpp'), default)
        self.assertIn(Path('src/render/renderer.cpp'), default)
        minimal = s.render_project(options('--features', 'none'))
        self.assertEqual({p for p in minimal if p.parts[0] == 'src'}, {Path('src/main.cpp'), Path('src/pch.h')})

    def test_feature_runtime_matrix(self):
        for runtime, settings in s.RUNTIMES.items():
            for flags in itertools.product((False, True), repeat=len(s.FEATURES)):
                features = [name for name, enabled in zip(s.FEATURES, flags) if enabled]
                invalid = ('hotkey' in features and 'config' not in features) or (
                    settings['VR'] == 'ON' and bool({'present_hook', 'vtable_hook'}.intersection(features)))
                with self.subTest(runtime=runtime, features=features):
                    if invalid:
                        with self.assertRaises(s.ScaffoldError):
                            options('--runtimes', runtime, '--features', ','.join(features))
                        continue
                    result = s.render_project(options('--runtimes', runtime, '--features', ','.join(features)))
                    manifest = json.loads(result[Path('vcpkg.json')])
                    self.assertEqual(manifest['version'], '1.0.0')
                    presets = json.loads(result[Path('CMakePresets.json')])
                    configure = {p['name'] for p in presets['configurePresets']}
                    for p in presets['buildPresets']:
                        self.assertIn(p['configurePreset'], configure)
                    cmake = result[Path('CMakeLists.txt')]
                    self.assertNotIn(Path('src/CMakeLists.txt'), result)
                    self.assertIn(Path('cmake/Plugin.h.in'), result)
                    self.assertEqual(set(result), s.expected_output_files(features))
                    for path, text in result.items():
                        self.assertNotIn('{{', text)
                        if path.suffix not in {'.h', '.cpp'}:
                            continue
                        for include in re.findall(r'#include "([^"]+)"', text):
                            self.assertTrue(include == 'Plugin.h' or path.parent / include in result
                                            or Path('src') / include in result, (path, include))

    def test_inputs_rejected_before_writes(self):
        invalid = [('name', '../escape'), ('name', 'CON'), ('name', 'COM1'),
                   ('name', 'bad-name'), ('author', 'a"b'), ('author', 'a;b'),
                   ('description', 'line\nbreak'), ('baseline', '0' * 39),
                   ('version', '256.0.0'), ('version', '0.256.0'),
                   ('version', '0.0.4096'), ('features', 'config,config'),
                   ('features', 'hotkey'), ('commonlib', 'legacy')]
        with tempfile.TemporaryDirectory() as temp:
            for flag, value in invalid:
                output = Path(temp) / 'not-created'
                with self.subTest(flag=flag, value=value), self.assertRaises(s.ScaffoldError):
                    s.create_project(options('--dir', str(output), '--' + flag, value))
                self.assertFalse(output.exists())

    def test_normalization_and_escaping(self):
        o = options('--name', 'HTTP_TestPlugin', '--version', '01.002.0003',
                    '--description', 'Quoted "text"; $HOME and back\\slash')
        self.assertEqual(o.version, '1.2.3')
        self.assertEqual(s.normalize_cpp_namespace(o.name), 'http_test_plugin')
        self.assertEqual(s.normalize_vcpkg_name(o.name), 'http-test-plugin')
        self.assertEqual(s.normalize_cpp_namespace('std'), 'std_plugin')
        self.assertEqual(s.normalize_cpp_namespace('class'), 'class_plugin')
        self.assertIn('\\"text\\"', s.render_project(o)[Path('CMakeLists.txt')])

    def test_offline_unicode_path_and_nonoverwrite(self):
        with tempfile.TemporaryDirectory(prefix='skse skill ') as temp:
            dest = Path(temp) / '项目 with spaces'
            with patch.object(s.subprocess, 'run') as run:
                s.create_project(options('--dir', str(dest), '--features', 'config,hotkey'))
                run.assert_not_called()
            originals = {p.relative_to(dest): p.read_bytes() for p in dest.rglob('*') if p.is_file()}
            self.assertNotIn(Path('.gitmodules'), originals)
            with self.assertRaises(s.ScaffoldError):
                s.create_project(options('--dir', str(dest)))
            self.assertEqual(originals, {p.relative_to(dest): p.read_bytes() for p in dest.rglob('*') if p.is_file()})

    def test_explicit_git_modes(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(s.subprocess, 'run') as run:
            dest = Path(temp) / 'local'
            s.create_project(options('--dir', str(dest), '--git-init'))
            self.assertEqual([c.args[0] for c in run.call_args_list], [['git', 'init']])
            run.reset_mock()
            dest = Path(temp) / 'submodule'
            s.create_project(options('--dir', str(dest), '--add-commonlib-submodule'))
            self.assertEqual([c.args[0] for c in run.call_args_list], [['git', 'init'], s.COMMONLIB_SUBMODULE_COMMAND])

    def test_bad_template_and_deterministic_render(self):
        for text in ('{{UNKNOWN}}', '{{ BAD }}', '{{bad-key}}'):
            with self.assertRaises(s.ScaffoldError):
                s.substitute(text, {})
        self.assertEqual(s.render_project(options()), s.render_project(options()))


if __name__ == '__main__':
    unittest.main(verbosity=2)
