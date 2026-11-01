"""Verify activation and publication boundaries for external resource integrations."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


class ExternalIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / "project"
        self.active = self.root / "client"
        self.active.mkdir()
        self.manifests = self.project / "integrations/resourcepacks"
        self.manifests.mkdir(parents=True)
        spec = importlib.util.spec_from_file_location(
            "snapshot_under_test", Path(__file__).with_name("snapshot_current.py"))
        self.snapshot = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.snapshot)
        self.snapshot.__file__ = str(self.root / "maintained/tools/snapshot_current.py")
        self.relative = "config/paxi/resourcepacks/example.zip"
        self.blob = b"exact external resource fixture"
        self.entry = {"path": self.relative, "sha256": hashlib.sha256(self.blob).hexdigest()}

    def manifest(self, **fields):
        metadata = {"clientFiles": [self.entry], **fields}
        (self.manifests / "example.json").write_text(json.dumps(metadata))

    def install(self):
        source = self.active / self.relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(self.blob)
        return source

    def read(self):
        return self.snapshot.external_resource_files(self.project, self.active)

    def test_legacy_manifest_remains_enabled_and_verifies_exact_bytes(self):
        self.manifest()
        source = self.install()
        result = self.read()
        self.assertEqual(result[self.relative]["bytes"], len(self.blob))
        self.assertTrue(self.snapshot.configured_pack_preserved(
            self.root / "snapshot", self.active, "example.zip", result))
        source.write_bytes(b"different bytes")
        with self.assertRaisesRegex(RuntimeError, "hash mismatch"):
            self.read()

    def test_explicit_enabled_manifest_still_requires_source(self):
        self.manifest(enabled=True)
        with self.assertRaisesRegex(RuntimeError, "source is missing"):
            self.read()
        self.install()
        self.assertEqual(self.read()[self.relative]["sha256"], self.entry["sha256"])

    def test_disabled_manifest_accepts_absent_source(self):
        self.manifest(enabled=False)
        result = self.read()
        self.assertIs(result[self.relative]["enabled"], False)
        self.assertEqual(result[self.relative]["sha256"], self.entry["sha256"])

    def test_disabled_manifest_rejects_present_source_even_with_matching_hash(self):
        self.manifest(enabled=False)
        self.install()
        with self.assertRaisesRegex(RuntimeError, "Disabled external integration source is still present"):
            self.read()

    def test_disabled_pack_cannot_remain_in_load_order(self):
        self.manifest(enabled=False)
        with self.assertRaisesRegex(RuntimeError, "remains in load order"):
            self.snapshot.configured_pack_preserved(
                self.root / "snapshot", self.active, "example.zip", self.read())

    def test_disabled_entries_preserve_path_hash_and_activation_validation(self):
        self.entry["path"] = "../outside.zip"
        self.manifest(enabled=False)
        with self.assertRaisesRegex(RuntimeError, "normalized client-relative path"):
            self.read()
        self.entry["path"] = self.relative
        self.entry["sha256"] = "invalid"
        self.manifest(enabled=False)
        with self.assertRaisesRegex(RuntimeError, "sha256"):
            self.read()
        self.entry["sha256"] = hashlib.sha256(self.blob).hexdigest()
        self.manifest(enabled="false")
        with self.assertRaisesRegex(RuntimeError, "enabled must be a boolean"):
            self.read()

    def test_disabled_entries_reject_symlinked_sources(self):
        self.manifest(enabled=False)
        source = self.active / self.relative
        source.parent.mkdir(parents=True)
        source.symlink_to(self.root / "absent.zip")
        with self.assertRaisesRegex(RuntimeError, "must not be symlinked"):
            self.read()


if __name__ == "__main__":
    unittest.main()
