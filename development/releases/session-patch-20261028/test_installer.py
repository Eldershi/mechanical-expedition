#!/usr/bin/env python3
"""Self-contained installer fixture checks; no Minecraft process is started."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('patch_installer', HERE / 'install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
DELTA = installer.read_json(HERE / 'catalog-delta.json')


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='expedition-patch-test-')
        self.root = Path(self.temporary.name).resolve()
        self.manifest = copy.deepcopy(installer.load_bundle())
        (self.root / 'mods').mkdir()
        # Small synthetic JARs exercise dependency parsing and hash checks. They
        # are not substitutes for the real-JAR active-instance verification.
        for index, row in enumerate(self.manifest['requiredMods']):
            path = self.root / 'mods' / row['filename']
            with zipfile.ZipFile(path, 'w') as jar:
                jar.writestr('META-INF/mods.toml', '[[mods]]\nmodId="fixture_' + str(index) + '"\n')
            row['sha256'] = installer.sha(path.read_bytes())
        for name in self.manifest['requiredBaseFiles']:
            self.put(name, b'// base CMI fixture, intentionally unchanged\n')
        base = {'schemaVersion': 1, 'mode': 'parallel_native_and_cmi', 'selectionCount': 239,
                'recipes': copy.deepcopy(DELTA['groups'][2]['recipes']),
                'customTopLevel': {'keep': True}, 'baselineUnavailable': ['fixture:untouched']}
        base['recipes'].append({'id': 'fixture:custom', 'nativeId': 'fixture:original',
                                'json': {'type': 'minecraft:crafting_shapeless', 'custom': True}})
        self.put(installer.CATALOG, installer.encoded(base))
        script = next(r for r in self.manifest['payload'] if r['path'].endswith('/SelectedParallelRecipes.js'))
        # Use the tested current dependency rather than impersonating its old SHA.
        self.put(script['path'], (HERE / 'payload' / script['path']).read_bytes())
        layout = b'''element {
  instance_identifier = expedition_quark_config_button_20261027
  anchor_point_element = mc_titlescreen_quit_button
  x = 77
  y = 30
  width = 20
  height = 20
  screen = org.violetmoon.quark.base.client.config.QuarkConfigHomeScreen
}
'''
        self.put('config/fancymenu/customization/title_screen_layout.txt', layout)
        self.put('config/quark-common.toml', b'# keep BOM-free bytes\r\n[general]\r\n  "Enable \'q\' Button" = true # keep comment\r\n  "Other Setting" = 73\r\n[management]\r\n"Sorting" = true\r\n')
        self.put('options.txt', b'guiScale:3\n')

    def tearDown(self):
        self.temporary.cleanup()

    def put(self, name, data):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): p.read_bytes() for p in self.root.rglob('*')
                if p.is_file() and installer.BACKUPS not in p.parts}

    def plan(self, role='client'):
        return installer.make_plan(self.root, role, self.manifest)

    def install(self, role='client'):
        jobs, report = self.plan(role)
        return installer.apply_plan(self.root, role, jobs, report)

    def test_fresh_merge_apply_verify_idempotent_and_rollback(self):
        before = self.snapshot()
        jobs, report = self.plan()
        self.assertEqual(self.snapshot(), before, 'dry-run wrote files')
        self.assertEqual(len(report['catalog']['addedRecipes']), 25)
        self.assertEqual(report['catalog']['selectionCount'], 241)
        installed = installer.apply_plan(self.root, 'client', jobs, report)
        self.assertEqual(installed['status'], 'installed')
        self.assertEqual((self.root / 'options.txt').read_bytes(), before['options.txt'])
        self.assertEqual((self.root / 'config/fancymenu/customization/title_screen_layout.txt').read_bytes(), before['config/fancymenu/customization/title_screen_layout.txt'])
        config = (self.root / 'config/quark-common.toml').read_bytes()
        self.assertEqual(config, before['config/quark-common.toml'].replace(b'Button" = true', b'Button" = false'))
        catalog = installer.read_json(self.root / installer.CATALOG)
        self.assertEqual(catalog['customTopLevel'], {'keep': True})
        index = len(DELTA['groups'][2]['recipes'])
        self.assertEqual(catalog['recipes'][index], json.loads(before[installer.CATALOG])['recipes'][index])
        after = self.snapshot()
        jobs, verified = self.plan()
        self.assertTrue(all(job['before'] == job['after'] for job in jobs))
        self.assertEqual(self.install()['status'], 'already_installed')
        self.assertEqual(self.snapshot(), after)
        receipt = Path(installed['receipt'])
        installer.rollback(self.root, receipt, False)
        self.assertEqual(self.snapshot(), after, 'rollback dry-run wrote files')
        installer.rollback(self.root, receipt, True)
        self.assertEqual(self.snapshot(), before)
        installer.rollback(self.root, receipt, True)
        self.assertEqual(self.snapshot(), before, 'repeat rollback changed files')

    def test_server_excludes_menu_assets_and_client_scripts(self):
        (self.root / 'config/quark-common.toml').unlink()
        (self.root / 'config/fancymenu/customization/title_screen_layout.txt').unlink()
        for row in self.manifest['requiredMods']:
            if row['roles'] == ['client']:
                (self.root / 'mods' / row['filename']).unlink()
        jobs, report = self.plan('server')
        self.assertEqual(len(jobs), 8)
        self.assertTrue(all(not job['path'].startswith(('config/', 'kubejs/assets/', 'kubejs/client_scripts/', 'kubejs/startup_scripts/')) for job in jobs))
        self.install('server')
        self.assertFalse((self.root / 'kubejs/assets').exists())

    def test_unknown_payload_edit_is_refused_before_any_write(self):
        self.put('kubejs/data/oei/replacements/zinc.json', b'{"custom":"do not overwrite"}')
        before = self.snapshot()
        with self.assertRaises(installer.Conflict):
            self.plan()
        self.assertEqual(self.snapshot(), before)

    def test_unknown_catalog_row_conflict_is_refused(self):
        x = installer.read_json(self.root / installer.CATALOG)
        bad = copy.deepcopy(DELTA['groups'][0]['recipes'][0])
        bad['json']['result']['count'] = 99
        x['recipes'].append(bad)
        self.put(installer.CATALOG, installer.encoded(x))
        with self.assertRaises(installer.Conflict):
            self.plan()

    def test_partial_stone_group_is_refused_instead_of_guessing_count(self):
        x = installer.read_json(self.root / installer.CATALOG)
        x['recipes'].append(copy.deepcopy(DELTA['groups'][1]['recipes'][0]))
        self.put(installer.CATALOG, installer.encoded(x))
        with self.assertRaises(installer.Conflict):
            self.plan()

    def test_intermediate_groups_count_correctly(self):
        for installed_index in (0, 1):
            x = installer.read_json(self.root / installer.CATALOG)
            x['recipes'].extend(copy.deepcopy(DELTA['groups'][installed_index]['recipes']))
            x['selectionCount'] = 240
            result, report = installer.merge_catalog(installer.encoded(x), DELTA)
            self.assertEqual(report['selectionCount'], 241)
            self.assertEqual(len(report['addedSelectionGroups']), 1)

    def test_missing_dependency_rows_repaired_without_count_increment(self):
        x = installer.read_json(self.root / installer.CATALOG)
        x['recipes'] = x['recipes'][len(DELTA['groups'][2]['recipes']):]
        result, report = installer.merge_catalog(installer.encoded(x), DELTA)
        self.assertEqual(len(report['addedRecipes']), 28)
        self.assertEqual(report['selectionCount'], 241)

    def test_missing_mod_or_base_file_refused(self):
        (self.root / 'mods' / self.manifest['requiredMods'][0]['filename']).unlink()
        with self.assertRaises(installer.Conflict):
            self.plan()

    def test_native_condition_conflict_refused(self):
        for mod_id in ('aeronautics', 'exnihilosequentia'):
            extra = self.root / 'mods' / 'renamed-condition.jar'
            with zipfile.ZipFile(extra, 'w') as jar:
                jar.writestr('META-INF/mods.toml', '[[mods]]\nmodId="' + mod_id + '"\n')
            with self.assertRaises(installer.Conflict):
                self.plan()
            extra.unlink()

    def test_optional_dependency_is_not_installed_mod(self):
        extra = self.root / 'mods' / 'optional-dependency.jar'
        with zipfile.ZipFile(extra, 'w') as jar:
            jar.writestr('META-INF/mods.toml', '[[mods]]\nmodId="fixture_optional"\n[[dependencies.fixture_optional]]\nmodId="aeronautics"\nmandatory=false\n[[dependencies.fixture_optional]]\nmodId="exnihilosequentia"\nmandatory=false\n')
        self.plan()

    def test_missing_retained_menu_entry_refused(self):
        self.put('config/fancymenu/customization/title_screen_layout.txt', b'other layout')
        with self.assertRaises(ValueError):
            self.plan()

    def test_rollback_refuses_post_install_custom_edit(self):
        installed = self.install()
        self.put('kubejs/data/oei/replacements/zinc.json', b'new edit after install')
        before = self.snapshot()
        with self.assertRaises(installer.Conflict):
            installer.rollback(self.root, Path(installed['receipt']), True)
        self.assertEqual(self.snapshot(), before)

    def test_apply_failure_restores_already_written_files(self):
        before = self.snapshot()
        jobs, report = self.plan()
        original = installer.atomic_write
        failed = [False]
        second = self.root / jobs[1]['path']
        def fail_once(path, data):
            if path == second and not failed[0]:
                failed[0] = True
                raise OSError('simulated write failure')
            return original(path, data)
        installer.atomic_write = fail_once
        try:
            with self.assertRaises(OSError):
                installer.apply_plan(self.root, 'client', jobs, report)
        finally:
            installer.atomic_write = original
        self.assertEqual(self.snapshot(), before)

    def test_symlink_and_traversal_refused(self):
        (self.root / 'link').symlink_to(self.root / 'options.txt')
        for name in ('../outside', '/outside', 'link'):
            with self.assertRaises(installer.Conflict):
                installer.safe_path(self.root, name)

if __name__ == '__main__':
    unittest.main(verbosity=2)
