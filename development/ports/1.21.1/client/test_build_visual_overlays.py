import json
from pathlib import Path
import re
import tempfile
import unittest
from zipfile import ZipFile

from build_visual_overlays import AE2_CHARGER, transparent_png, write_compatibility_packs


class CompatibilityPackFiltersTest(unittest.TestCase):
    def test_filters_match_complete_paths_in_their_own_namespace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "ae2.jar"
            charger = transparent_png(64, 64)
            with ZipFile(source, "w") as pack:
                pack.writestr(AE2_CHARGER, charger)
            output = root / "Expedition-Resource-Compat-1.21.1.zip"
            write_compatibility_packs(output, source)
            with ZipFile(output) as pack:
                self.assertEqual(pack.read(AE2_CHARGER), charger)
                self.assertIn("ATTRIBUTION-AE2.txt", pack.namelist())
            filters = []
            for path in root.glob("*.zip"):
                with ZipFile(path) as pack:
                    filters.append(json.loads(pack.read("pack.mcmeta"))["filter"]["block"])

        def blocked(namespace, path):
            # Minecraft checks namespace and path independently with regex search.
            return any(
                any(re.search(rule["namespace"], namespace) for rule in rules)
                and any(re.search(rule["path"], path) for rule in rules)
                for rules in filters
            )

        self.assertEqual(len(filters), 3)
        self.assertTrue(blocked("mm", "models/block/controller.json"))
        self.assertTrue(blocked("edenring", "textures/block/portal_block_center_n.png"))
        self.assertTrue(blocked("minecraft", "textures/entity/enchanting_table_book_e.png"))
        self.assertFalse(blocked("immersiveengineering", "models/block/cokebrick.json"))
        self.assertFalse(blocked("minecraft", "models/block/cube_all.json"))
        self.assertFalse(blocked("mm", "archive/models/block/controller.json.bak"))
