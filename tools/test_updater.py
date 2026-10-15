"""Exercise real Git/file updates in disposable instances, including rollback."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
PLAYER = HERE / "player"
if not PLAYER.is_dir():
    PLAYER = HERE.parent / "pack/updater"


def digest(data):
    return hashlib.sha256(data).hexdigest()


class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="expedition-update-test-")
        self.work = Path(self.temp.name)
        self.root = self.work / "player"
        self.repo = self.work / "release"
        self.root.mkdir()
        self.repo.mkdir()
        (self.root / "updater").mkdir()
        shutil.copy2(PLAYER / "expedition-update.sh", self.root / "updater/expedition-update.sh")
        self.old_code = b"// original code\n"
        self.new_code = b"// updated code\n"
        self.old_jar = b"old jar contents\n"
        self.new_jar = b"new jar contents\n"
        self.write("kubejs/server_scripts/example.js", self.old_code)
        self.write("mods/example-1.jar", self.old_jar)
        self.write("mods/retired-1.jar", b"retired jar")
        self.write("mods/player-extra.jar", b"my extra mod")
        self.write("options.txt", b"player settings")
        self.write("saves/world/level.dat", b"player world")
        self.write("servers.dat", b"private server list")
        self.write(".expedition/installed.env", b"PACK_ID=mechanical-expedition\nVERSION=old\n")
        rows = [
            (digest(self.old_code), "kubejs/server_scripts/example.js"),
            (digest(self.old_jar), "mods/example-1.jar"),
            (digest(b"retired jar"), "mods/retired-1.jar"),
        ]
        self.write(".expedition/state.tsv", "".join(f"{h}\t{p}\n" for h, p in rows).encode())
        self.initial_state = (self.root / ".expedition/state.tsv").read_bytes()
        (self.repo / "pack/kubejs/server_scripts").mkdir(parents=True)
        (self.repo / "pack/kubejs/server_scripts/example.js").write_bytes(self.new_code)
        (self.repo / "pack/kubejs/new.js").write_bytes(b"new file")
        self.files = [
            (digest(self.new_code), "kubejs/server_scripts/example.js"),
            (digest(b"new file"), "kubejs/new.js"),
        ]
        self.download = self.work / "new.jar"
        self.download.write_bytes(self.new_jar)
        self.mod_url = self.download.as_uri()
        self.mod_hash = digest(self.new_jar)
        self.release = "PACK_ID=mechanical-expedition\nVERSION=next\nMINECRAFT=1.20.1\nFORGE=47.4.10\n"
        self.configure()
        self.commit()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def configure(self, remote=None):
        remote = self.repo.as_uri() if remote is None else remote
        self.write("updater/expedition.conf", f"PACK_ID=mechanical-expedition\nREMOTE_URL={remote}\nREF=main\nMINECRAFT=1.20.1\nFORGE=47.4.10\n".encode())

    def commit(self):
        (self.repo / "release.env").write_text(self.release)
        (self.repo / "files.tsv").write_text("".join(f"{h}\t{p}\n" for h, p in self.files))
        (self.repo / "mods.tsv").write_text(f"{self.mod_hash}\tmods/example-2.jar\t{self.mod_url}\n")
        if not (self.repo / ".git").exists():
            subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Local Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture", "--allow-empty"], check=True)

    def run_update(self, *args, **environment):
        env = {**os.environ, "EXPEDITION_ALLOW_LOCAL_TEST": "1", **environment}
        return subprocess.run(["/bin/bash", str(self.root / "updater/expedition-update.sh"), *args], env=env, text=True, capture_output=True, timeout=45)

    def assert_personal_files(self):
        for path, expected in [("options.txt", b"player settings"), ("saves/world/level.dat", b"player world"), ("servers.dat", b"private server list"), ("mods/player-extra.jar", b"my extra mod")]:
            self.assertEqual((self.root / path).read_bytes(), expected, path)

    def assert_unchanged(self):
        self.assertEqual((self.root / "kubejs/server_scripts/example.js").read_bytes(), self.old_code)
        self.assertEqual((self.root / "mods/example-1.jar").read_bytes(), self.old_jar)
        self.assertFalse((self.root / "mods/example-2.jar").exists())
        self.assertFalse((self.root / "kubejs/new.js").exists())
        self.assertEqual((self.root / ".expedition/state.tsv").read_bytes(), self.initial_state)
        self.assert_personal_files()

    def test_update_and_idempotent_repeat(self):
        result = self.run_update()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.root / "kubejs/server_scripts/example.js").read_bytes(), self.new_code)
        self.assertEqual((self.root / "mods/example-2.jar").read_bytes(), self.new_jar)
        self.assertFalse((self.root / "mods/example-1.jar").exists())
        self.assertFalse((self.root / "mods/retired-1.jar").exists())
        self.assert_personal_files()
        result = self.run_update()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("changed/removed files: 0", result.stdout)

    def test_check_only(self):
        result = self.run_update("--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assert_unchanged()

    def test_windows_style_git_line_ending_default(self):
        global_config = self.work / "gitconfig"
        global_config.write_text("[core]\n\tautocrlf = true\n")
        result = self.run_update(GIT_CONFIG_GLOBAL=str(global_config))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.root / "kubejs/server_scripts/example.js").read_bytes(), self.new_code)
        self.assert_personal_files()

    def test_modified_managed_file_is_preserved(self):
        self.write("kubejs/server_scripts/example.js", b"my local code")
        result = self.run_update()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Local modification", result.stdout + result.stderr)
        self.assertEqual((self.root / "kubejs/server_scripts/example.js").read_bytes(), b"my local code")
        self.assertTrue((self.root / "mods/example-1.jar").exists())
        self.assert_personal_files()

    def test_download_failure_leaves_whole_batch_unchanged(self):
        self.mod_url = (self.work / "missing.jar").as_uri()
        self.commit()
        self.assertNotEqual(self.run_update().returncode, 0)
        self.assert_unchanged()

    def test_download_checksum_failure_leaves_whole_batch_unchanged(self):
        self.mod_hash = "0" * 64
        self.commit()
        result = self.run_update()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checksum mismatch", result.stdout + result.stderr)
        self.assert_unchanged()

    def test_rollback_after_replacement_and_new_file(self):
        result = self.run_update(EXPEDITION_TEST_FAIL_AFTER="2")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("rollback", result.stdout)
        self.assert_unchanged()

    def test_rollback_after_retired_mod_removal(self):
        result = self.run_update(EXPEDITION_TEST_FAIL_AFTER="4")
        self.assertNotEqual(result.returncode, 0)
        self.assert_unchanged()

    def test_protected_save_path_is_rejected(self):
        self.files.append((digest(b"bad"), "saves/world/level.dat"))
        self.commit()
        self.assertNotEqual(self.run_update().returncode, 0)
        self.assert_unchanged()

    def test_parent_traversal_is_rejected(self):
        self.files.append((digest(b"bad"), "kubejs/../../escape.txt"))
        self.commit()
        self.assertNotEqual(self.run_update().returncode, 0)
        self.assertFalse((self.work / "escape.txt").exists())
        self.assert_unchanged()

    def test_player_directory_symlink_is_rejected(self):
        outside = self.work / "outside"
        outside.mkdir()
        shutil.rmtree(self.root / "kubejs")
        (self.root / "kubejs").symlink_to(outside, target_is_directory=True)
        self.assertNotEqual(self.run_update().returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])
        self.assert_personal_files()

    def test_wrong_pack_is_rejected(self):
        self.release = self.release.replace("mechanical-expedition", "another-pack")
        self.commit()
        self.assertNotEqual(self.run_update().returncode, 0)
        self.assert_unchanged()

    def test_loader_change_requires_new_install(self):
        self.release = self.release.replace("47.4.10", "47.4.28")
        self.commit()
        self.assertNotEqual(self.run_update().returncode, 0)
        self.assert_unchanged()

    def test_duplicate_managed_path_is_rejected(self):
        self.files.append(self.files[0])
        self.commit()
        self.assertNotEqual(self.run_update().returncode, 0)
        self.assert_unchanged()

    def test_missing_repository_fails_without_changing_instance(self):
        self.configure(remote="")
        result = self.run_update()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not configured", result.stderr)
        self.assert_unchanged()


if __name__ == "__main__":
    unittest.main(verbosity=2)
