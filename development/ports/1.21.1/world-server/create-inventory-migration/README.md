# Create inventory migration

Run the converter on the closed Minecraft 1.20.1 region copy before opening it with Minecraft 1.21.1. Run it separately for each region directory you want to migrate. The tool converts stacks stored in Create Item Vaults, as well as list and item-tag filters stored in vaults, funnels and Stock Ticker categories. It leaves chunk version numbers for Minecraft to upgrade when it opens the world.

Provide the Java 21 JDK, the 1.21.1 NeoForge server `libraries` directory, and the registry from the target test server. To export it, temporarily install `export-target-registry.js` under the test server's `kubejs/server_scripts`, start it, and copy `kubejs/exported/create-inventory-target-registry.json`.

```json
{"items": ["minecraft:air"], "enchantments": ["minecraft:protection"]}
```

```sh
python3 migrate.py \
  --java-home /path/to/jdk-21 \
  --libraries /path/to/test-server/libraries \
  --source-regions /path/to/closed-copy/region \
  --target-registry /path/to/target-item-registry.json \
  --output /path/to/new-vault-conversion
```

The output `region` directory can be used for further region transformations and then installed in the test world. A plain Thermal copper nugget becomes the equivalent Create copper nugget when the Thermal ID is unavailable.

Retain `unconverted-stacks.nbt` with the source archive. `Stacks` preserves coordinates, slots or filter fields, reasons, and complete original stacks for unavailable IDs or unverified data. `RetainedWithWarnings` preserves the originals for migrated Vault stacks whose enchantments are absent from the target registry. If the JSON omits `enchantments`, that section preserves all enchantment-bearing Vault stacks for review. A retained warning does not remove the item from the migrated vault. The summary records both counts, the affected enchantment IDs, converted filters, and item ID changes. Review archived filters before enabling machines that depend on them.
