# Expedition smeltery transfer

Use the NeoForge 1.21.1 build and Hilt versions pinned in `mods.json` on both sides. Generate the datapack to keep the Expedition copper and brass casting IDs and the custom biodiesel and blazing blood fuel recipes.

```sh
python3 build_datapack.py path/to/legacy-tconstruct.jar path/to/target-foundry.jar path/to/world/datapacks/expedition-tconstruct --namespace modernfoundry
```

With `nbtlib==2.0.4`, export the machines from a copy of the old Anvil region.

```sh
python3 export_smelteries.py --namespace modernfoundry --target-jar path/to/target-foundry.jar --output path/to/new-export --hold terramity:fairy_dust path/to/region.mca
```

To export specific smelteries from a shared region, pass `--controller X Y Z` once per controller. When selecting one controller, add `--casting-basin X Y Z` for each detached casting basin that belongs in the transfer.

Each template contains the smeltery and nearby Tinkers' blocks, plus converted fluids, casting inputs, inventory slots and controller offsets. Positions in `transfer.json` refer to the source block at the template origin. Put the templates under `data/expedition/structure/` in a test-world datapack and use `/place template expedition:smeltery_1 <x> <y> <z>` to load one at a time. The mod redetects wall links and its internal check position on load. Check the controller structure and the fuel, fluid and casting inventories after saving and reopening the copy.

Install the industry startup script `ExpeditionLegacyFoundryContents.js` with the target pack to preserve the `thermal:redstone` fluid and `terramity:fairy_dust` item IDs. Pass `--target-registry` with a JSON export containing the target server's `items` and `fluids` ID arrays. The manifest lists any unavailable or explicitly held contents, and the corresponding `*_unresolved.nbt` preserves the original block entity data for review.

For an offline transfer, run `apply_smeltery_transfer.py <closed-world> <block-catalog.json> <new-world-copy> <export-directory>...` with NumPy and nbtlib. Supply the target block catalog from the optional world-server probe. Pass exports with complete contents. Use the prepared copy as the export source for machines with retained data and the matching legacy archive for missing machines. The installer checks each destination block and block entity, then writes a new closed copy. Verify the native controllers, casting blocks, items and fluids after saving and reopening a disposable copy.
