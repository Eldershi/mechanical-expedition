# Restore Modern Foundry tools in a migrated Create vault

Use a stopped copy of the Minecraft 1.21.1 world and Python with `nbtlib==2.0.4`. The tool reads the remaining recovery file produced by Create vault inventory migration. It stages region files and a new recovery file in a separate directory.

When restoring IE blueprints in the same copy, run the IE recovery tool first. Apply its changed Anvil regions to the stopped copy. Use its remaining `unconverted-stacks.nbt` as the input below. [IE recovery tool](../world-server/migration/restore_ie_state.py)

```sh
python3 restore_foundry_vault_tools.py \
  --target-regions /path/to/stopped-world-copy/region \
  --vault-recovery /path/to/blueprint-output/unconverted-stacks.nbt \
  --output /path/to/new-foundry-output
```

Review `foundry-tool-report.json` and copy only the staged `r.*.*.mca` files into the same stopped copy's `region` directory. Keep the output `unconverted-stacks.nbt` with the copy for the outstanding entries.

Add `--include-nebula` when the Nebula Tinker adapter is installed to restore the saved spider fang in its original vault slot.

Add `--include-legacy-pan-materials` with Nebula Tinker adapter 1.1 to restore the lead and Lumium pan and the cast iron and Soul-Infused pan. These two patterns use the adapter's hidden limb materials and keep the original part statistics and saved Luminescence trait.

Add `--include-equivalent-stacks` with Create Crafts & Additions and Modern Foundry installed. This restores the original CMI capacitor as `createaddition:capacitor` and matching Foundry stock such as Seared Bricks and Skyslime Balls. The stock must have only an original ID, count, and slot. Stored fluids, tool station textures, and other item payloads stay in the recovery file.

Add `--include-create-workpieces` with Create 6 and the Expedition industry recipes installed. It restores unworn sandpaper and super glue, belt connectors with their first shaft selection, and the verified copper, precision, light engineering, and motor rotor assembly stages. The assembly mappings require the original recipe ID, step, and progress to match a stage whose completed operations carry over to the current recipe.

Add `--spell-registry /path/to/spell-registry.json` to restore Iron's Spells 'n Spellbooks scrolls. Export the resource IDs in `SpellRegistry.REGISTRY` from a running copy of the target pack as a JSON object with a `spells` array. Each restored scroll keeps its original count and spell container, including the spell ID, level, and lock state. Scrolls whose spells are absent from the target registry stay in the recovery file.

The source vault coordinate and slot identify each tool. Empty slots receive the converted stack, exact matches are recorded as already valid, and occupied slots retain their contents. Unsupported materials and payloads stay in the recovery file. The tool restores the authoritative vault inventory. Create's cached packager summaries are left out of item recovery.

Reopen the copy and check the restored vault slots. The native Foundry item should retain its position, parts, durability, and supported tool-tank contents. Save and stop the copy before transferring its changed region files.
