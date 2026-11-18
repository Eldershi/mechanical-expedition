# Expedition smeltery transfer

Use the NeoForge 1.21.1 build and Hilt versions pinned in `mods.json` on both sides. Generate the datapack to keep the Expedition copper and brass casting IDs and the custom biodiesel and blazing blood fuel recipes.

```sh
python3 build_datapack.py path/to/legacy-tconstruct.jar path/to/target-foundry.jar path/to/world/datapacks/expedition-tconstruct --namespace modernfoundry
```

With `nbtlib==2.0.4`, export the machines from a copy of the old Anvil region.

```sh
python3 export_smelteries.py --namespace modernfoundry --target-jar path/to/target-foundry.jar --output path/to/new-export --hold terramity:fairy_dust path/to/region.mca
```

To export specific smelteries from a shared region, pass `--controller X Y Z` once per controller.

Each template contains the smeltery and nearby Tinkers' blocks, plus converted fluids, casting inputs, inventory slots and controller offsets. Positions in `transfer.json` refer to the source block at the template origin. Put the templates under `data/expedition/structure/` in a test-world datapack and use `/place template expedition:smeltery_1 <x> <y> <z>` to load one at a time. The mod redetects wall links and its internal check position on load. Check the controller structure and the fuel, fluid and casting inventories after saving and reopening the copy.

Thermal fluids and any explicitly held IDs are listed in `transfer.json`. The corresponding `*_unresolved.nbt` retains the complete source block entity so those contents can be inspected separately. The exporter reads the source regions and creates a new output directory.
