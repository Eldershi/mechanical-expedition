#!/usr/bin/env python3
"""Exercise transactions on temporary disposable copies, never a live instance."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

RELEASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RELEASE))
import install_client as installer
import build_packages as builder


class ClientInstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='expedition-installer-test-')
        self.base = Path(self.temp.name)
        self.release = self.base / 'release'
        self.stage = self.release / 'staging'
        self.target = self.base / 'instance'
        self.stage.mkdir(parents=True)
        self.target.mkdir()
        self.old = {
            'kubejs/server_scripts/a.js': b'// original\n',
            'mods/old-version.jar': b'old jar bytes\x00\xff',
            'config/jei/recipe-category-sort-order.ini': b'personal order',
            'updater/expedition.conf': b'preserve release channel',
            **{rel: ('original catalog ' + str(i)).encode() for i, rel in enumerate(installer.PROTECTED_CATALOGS)},
        }
        for rel, blob in self.old.items():
            for folder in (self.target, self.stage):
                p = folder / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(blob)
        (self.target / 'kubejs/server_scripts/a.js').chmod(0o744)
        (self.target / 'unrelated.txt').write_bytes(b'untouched')
        (self.stage / 'kubejs/server_scripts/a.js').write_bytes(b'// updated\n')
        (self.stage / 'kubejs/server_scripts/b.js').write_bytes(b'// newly added\n')
        (self.stage / 'mods/old-version.jar').unlink()
        (self.stage / 'mods/new-version.jar').write_bytes(b'new jar bytes\x00\xfe')
        # Generated/host-specific changes must never enter the delta.
        (self.stage / 'server.properties').write_bytes(b'do not ship')
        (self.stage / 'config/jei/recipe-category-sort-order.ini').write_bytes(b'generated order')
        p = self.stage / 'kubejs/exported/audit.json'
        p.parent.mkdir(parents=True); p.write_bytes(b'{}')
        snapshot = {'files': {rel: {'sha256': installer.digest(self.target / rel), 'bytes': len(blob)} for rel, blob in self.old.items()}}
        (self.release / 'evidence').mkdir()
        installer.write_json(self.release / 'evidence/active-before.json', snapshot)
        shutil.copy2(RELEASE / 'install_client.py', self.release / 'install_client.py')
        installer.write_json(self.release / 'evidence/runtime-pass.json', {'passed': True})
        installer.write_json(self.release / 'evidence/fixture-pass.json', {'passed': True})
        self.output = self.release / 'package'
        builder.build(self.release, output=self.output, validation_reports=[self.release / 'evidence/runtime-pass.json', self.release / 'evidence/fixture-pass.json'])
        self.manifest = installer.read_json(self.output / 'client-manifest.json')

    def tearDown(self):
        self.temp.cleanup()

    def assert_original(self):
        for rel, blob in self.old.items():
            self.assertEqual((self.target / rel).read_bytes(), blob, rel)
        self.assertFalse((self.target / 'kubejs/server_scripts/b.js').exists())
        self.assertFalse((self.target / 'mods/new-version.jar').exists())
        self.assertEqual((self.target / 'unrelated.txt').read_bytes(), b'untouched')

    def test_success_idempotence_and_full_rollback(self):
        checked = installer.preflight(self.target, self.output, self.manifest)
        self.assertEqual(checked['pending'], 4)
        result = installer.install(self.target, self.output, self.manifest)
        self.assertEqual(result['status'], 'installed')
        self.assertEqual(result['changedFiles'], 4)
        backup = Path(result['backup'])
        self.assertEqual((backup / 'files/mods/old-version.jar').read_bytes(), self.old['mods/old-version.jar'])
        self.assertEqual((backup / 'files/kubejs/server_scripts/a.js').read_bytes(), self.old['kubejs/server_scripts/a.js'])
        repeat = installer.install(self.target, self.output, self.manifest)
        self.assertEqual(repeat['status'], 'already_applied')
        self.assertIsNone(repeat['backup'])
        self.assertEqual(installer.rollback(self.target, backup)['status'], 'rolled_back')
        self.assert_original()
        self.assertEqual((self.target / 'kubejs/server_scripts/a.js').stat().st_mode & 0o777, 0o744)
        self.assertEqual(installer.rollback(self.target, backup)['restoredFiles'], 0)

    def test_concurrent_edit_refused_before_writes(self):
        changed = b'// another task edited this\n'
        (self.target / 'kubejs/server_scripts/a.js').write_bytes(changed)
        with self.assertRaisesRegex(installer.PatchError, 'Preflight refused'):
            installer.install(self.target, self.output, self.manifest)
        self.assertEqual((self.target / 'kubejs/server_scripts/a.js').read_bytes(), changed)
        self.assertFalse((self.target / 'kubejs/server_scripts/b.js').exists())
        self.assertTrue((self.target / 'mods/old-version.jar').exists())
        self.assertFalse((self.target / '.expedition-patch-backups').exists())

    def test_protected_catalog_drift_refused(self):
        rel = installer.PROTECTED_CATALOGS[0]
        (self.target / rel).write_bytes(b'new recipes from another task')
        with self.assertRaisesRegex(installer.PatchError, 'protected_catalog_changed'):
            installer.install(self.target, self.output, self.manifest)
        self.assertEqual((self.target / rel).read_bytes(), b'new recipes from another task')
        self.assertEqual((self.target / 'kubejs/server_scripts/a.js').read_bytes(), self.old['kubejs/server_scripts/a.js'])

    def test_tampered_payload_refused(self):
        (self.output / 'client-payload/mods/new-version.jar').write_bytes(b'corrupt jar')
        with self.assertRaisesRegex(installer.PatchError, 'payload_missing_or_hash_mismatch'):
            installer.install(self.target, self.output, self.manifest)
        self.assert_original()

    def test_failure_after_first_write_auto_rolls_back(self):
        real = installer.atomic_copy
        calls = 0
        def fail_once(source, target, mode=0o644):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('simulated disk failure after one successful write')
            return real(source, target, mode)
        installer.atomic_copy = fail_once
        try:
            with self.assertRaisesRegex(installer.PatchError, 'was rolled back'):
                installer.install(self.target, self.output, self.manifest)
        finally:
            installer.atomic_copy = real
        self.assert_original()
        transactions = list((self.target / '.expedition-patch-backups').rglob('transaction.json'))
        self.assertEqual(len(transactions), 1)
        self.assertEqual(installer.read_json(transactions[0])['status'], 'rolled_back')

    def test_rollback_does_not_overwrite_new_edits(self):
        result = installer.install(self.target, self.output, self.manifest)
        target = self.target / 'kubejs/server_scripts/a.js'
        target.write_bytes(b'// edited after install\n')
        with self.assertRaisesRegex(installer.PatchError, 'Rollback refused'):
            installer.rollback(self.target, Path(result['backup']))
        self.assertEqual(target.read_bytes(), b'// edited after install\n')
        self.assertTrue((self.target / 'mods/new-version.jar').exists())

    def test_payload_exclusions_and_catalog_protection(self):
        paths = {op['path'] for op in self.manifest['operations']}
        self.assertEqual(paths, {'kubejs/server_scripts/a.js', 'kubejs/server_scripts/b.js', 'mods/old-version.jar', 'mods/new-version.jar'})
        self.assertEqual(set(self.manifest['protectedCatalogs']), set(installer.PROTECTED_CATALOGS))
        bad = copy.deepcopy(self.manifest)
        bad['operations'].append({'path': installer.PROTECTED_CATALOGS[0], 'action': 'delete', 'beforeSha256': '0' * 64, 'afterSha256': None})
        with self.assertRaises(installer.PatchError):
            installer.validate_manifest(bad)

    def test_symlink_and_traversal_refused(self):
        bad = copy.deepcopy(self.manifest)
        bad['operations'][0]['path'] = '../escape'
        with self.assertRaises(installer.PatchError):
            installer.validate_manifest(bad)
        a = self.target / 'kubejs/server_scripts/a.js'
        a.unlink(); a.symlink_to(self.target / 'unrelated.txt')
        with self.assertRaisesRegex(installer.PatchError, 'Symbolic link rejected'):
            installer.install(self.target, self.output, self.manifest)
        self.assertEqual((self.target / 'unrelated.txt').read_bytes(), b'untouched')

    def test_preview_install_refused(self):
        preview = copy.deepcopy(self.manifest)
        preview['validationStatus'] = 'preview_unvalidated'
        with self.assertRaisesRegex(installer.PatchError, 'cannot be installed'):
            installer.install(self.target, self.output, preview)
        self.assert_original()

    def test_backup_symlink_refused(self):
        elsewhere = self.base / 'elsewhere'
        elsewhere.mkdir()
        (self.target / '.expedition-patch-backups').symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaisesRegex(installer.PatchError, 'Symbolic link rejected in backup'):
            installer.install(self.target, self.output, self.manifest)
        self.assert_original()
        self.assertFalse(list(elsewhere.iterdir()))

    def test_builder_rejects_catalog_change(self):
        (self.stage / installer.PROTECTED_CATALOGS[1]).write_bytes(b'overwritten catalog')
        with self.assertRaisesRegex(installer.PatchError, 'Protected restored catalog changed'):
            builder.build(self.release, output=self.output, validation_reports=[self.release / 'evidence/runtime-pass.json'])


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ClientInstallerTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {'passed': result.wasSuccessful(), 'testsRun': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors),
              'scope': 'Disposable temporary copies only; active client and staging never modified by these tests.'}
    (RELEASE / 'evidence/client-installer-tests.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
