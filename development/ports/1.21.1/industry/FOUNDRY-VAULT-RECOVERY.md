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

The source vault coordinate and slot identify each tool. Empty slots receive the converted stack, exact matches are recorded as already valid, and occupied slots retain their contents. Unsupported materials and payloads stay in the recovery file. The tool restores the authoritative vault inventory. Create's cached packager summaries are left out of item recovery.

Reopen the copy and check the restored vault slots. The native Foundry item should retain its position, parts, durability, and supported tool-tank contents. Save and stop the copy before transferring its changed region files.
