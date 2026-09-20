#!/usr/bin/env python3
"""Check the minimal output and generator I/O boundaries, not reference equality."""
import json
from pathlib import Path
import tempfile
import unittest
import itertools
from unittest.mock import patch
import scaffold as s


def options(*args):
    return s.options_from_args(s.build_parser().parse_args(['--name','TestPlugin',*args]))


class ScaffoldTests(unittest.TestCase):
    def test_feature_selection_and_pairs(self):
        names=list(s.features.catalog())
        selections=[(name,) for name in names]+list(itertools.combinations(names,2))+[tuple(names)]
        for selection in selections:
            with self.subTest(features=selection):
                o=options('--features',','.join(selection))
                output=s.render_project(o)
                self.assertTrue(all('features' not in p.parts for p in output))
                self.assertTrue(all(s.TOKEN.search(text) is None for text in output.values()))
                for name in o.features:
                    for dependency in s.features.catalog()[name]['requires']:
                        self.assertIn(dependency,o.features)
                for path,text in output.items():
                    if path.suffix not in ('.h','.cpp'):
                        continue
                    for inc in s.re.findall(r'#include "([^"\n]+)"',text):
                        self.assertTrue(inc in ('plugin.h','render/shader_sources.h') or path.parent/inc in output
                                        or Path('src')/inc in output,(path,inc))

    def test_conditional_dependencies(self):
        plain=s.render_project(options())
        self.assertNotIn('message_handler',plain[Path('src/main.cpp')])
        inputs=s.render_project(options('--features','input'))
        self.assertIn(Path('src/config/config.cpp'),inputs)
        self.assertNotIn(Path('src/ui/ui_menu.cpp'),inputs)
        self.assertNotIn('ui/ui_menu.h',inputs[Path('src/input/input.cpp')])
        menu=s.render_project(options('--features','input,menu'))
        self.assertIn('Menu::is_menu_open()',menu[Path('src/input/input.cpp')])
        self.assertIn('extern/SKSE-MCP',menu[Path('.gitmodules')])
        self.assertEqual(json.loads(menu[Path('vcpkg.json')])['dependencies'].count('simpleini'),1)
        shaders=s.render_project(options('--features','shaders'))
        self.assertIn(Path('cmake/embed_shaders.cmake'),shaders)
        self.assertIn('include(cmake/shaders.cmake)',shaders[Path('CMakeLists.txt')])

    def test_bad_features_and_cycle(self):
        for raw in ('unknown','input,input','../config','config,'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):
                options('--features',raw)
        with patch.object(s.features,'catalog',return_value={'a':{'requires':['b']},'b':{'requires':['a']}}):
            with self.assertRaises(ValueError):
                s.features.resolve('a')

    def test_minimal_dependency_and_source_boundary(self):
        result=s.render_project(options())
        self.assertEqual({p.as_posix() for p in result if p.parts[0]=='src'},
                         {'src/main.cpp','src/pch.h'})
        self.assertEqual(len(s.SUBMODULES),1)
        self.assertEqual(s.SUBMODULES[0][1],'extern/CommonLibSSE')
        deps=json.loads(result[Path('vcpkg.json')])['dependencies']
        self.assertNotIn('simpleini',deps)
        cmake=result[Path('CMakeLists.txt')]
        for optional in ('SKSE-MCP','SimpleIni::','GENERATED_SHADER_HEADER','d3dcompiler'):
            self.assertNotIn(optional,cmake)
        self.assertTrue(all(s.TOKEN.search(content) is None for content in result.values()))

    def test_identity(self):
        o=options('--namespace','Team::Mods','--author','Example Author','--version','01.02.003')
        result=s.render_project(o)
        self.assertEqual(o.version,'1.2.3')
        self.assertIn('Team::Mods::${PROJECT_NAME}',result[Path('CMakeLists.txt')])
        self.assertIn('set(PROJECT_AUTHOR "Example Author")',result[Path('CMakeLists.txt')])
        self.assertEqual(json.loads(result[Path('vcpkg.json')])['version'],'1.2.3')
        self.assertEqual(s.render_project(o),result)

    def test_invalid_inputs_never_write(self):
        bad=[('name','../bad'),('name','CON'),('namespace','std'),('namespace','Bad::'),
             ('author','a"b'),('author','a;b'),('version','256.0.0'),('version','0.0.4096'),
             ('baseline','a'*39),('display-name','two\nlines')]
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/'output'
            for key,value in bad:
                with self.subTest(key=key),self.assertRaises(s.ScaffoldError):
                    s.create_project(options('--dir',str(dest),'--'+key,value))
                self.assertFalse(dest.exists())

    def test_offline_generation_and_nonoverwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/'plugin with spaces'
            with patch.object(s.subprocess,'run') as run:
                s.create_project(options('--dir',str(dest)))
                run.assert_not_called()
            before={p.relative_to(dest):p.read_bytes() for p in dest.rglob('*') if p.is_file()}
            with self.assertRaises(s.ScaffoldError):
                s.create_project(options('--dir',str(dest)))
            self.assertEqual(before,{p.relative_to(dest):p.read_bytes() for p in dest.rglob('*') if p.is_file()})

    def test_explicit_acquisition_selects_only_commonlib(self):
        with tempfile.TemporaryDirectory() as temp,patch.object(s.subprocess,'run') as run:
            s.create_project(options('--dir',str(Path(temp)/'plugin'),'--add-submodules'))
            self.assertEqual([call.args[0] for call in run.call_args_list],
                [['git','init'],['git','submodule','add',*s.SUBMODULES[0]],
                 ['git','submodule','update','--init','--recursive']])


if __name__=='__main__':
    unittest.main(verbosity=2)
