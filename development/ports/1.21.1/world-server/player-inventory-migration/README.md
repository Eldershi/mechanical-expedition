# Player inventory migration

Stage the player data and Sophisticated Backpacks storage from the same closed Minecraft 1.20.1 world. Use Java 21, Python with `nbtlib==2.0.4`, the target NeoForge server libraries, and an item and enchantment registry exported from the matching test server. The [registry exporter](../create-inventory-migration/export-target-registry.js) runs only in the test instance.

```sh
python3 migrate.py \
  --source /path/to/closed-world-source \
  --target-registry /path/to/create-inventory-target-registry.json \
  --java-home /path/to/jdk-21 \
  --libraries /path/to/test-server/libraries \
  --output /path/to/new-player-recovery
```

The source directory must contain `playerdata/` and `data/sophisticatedbackpacks.dat`. The staged output uses the same layout. Apply both to a stopped 1.21.1 copy and verify the inventories, equipped Curios and backpack contents after saving and reopening.

The converter uses Minecraft's player and item data fixers. It preserves player UUIDs, vanilla inventory and Ender Chest slots, nested inventory entries, Sophisticated Backpacks content UUIDs and extended stack counts, and registered enchantments and levels. It translates the Iron's Spells ’n Spellbooks spell item components and player magic data, Create Jetpack air and the supported MultiBuilder Tool fields.

Keep `legacy-recovery.nbt` with the original private world copy. It contains the original stacks and their locations for unavailable items, unsupported enchantments and unverified item payloads, along with original player capabilities. Unsupported enchantments are left out of active stacks so a missing enchantment can't invalidate an otherwise usable item. Unsupported legacy slot payloads and compiled multiblock selections require a separate target-specific mapping. Player files, the backpack storage and the recovery NBT are private world data.
