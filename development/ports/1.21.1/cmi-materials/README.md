# CMI registrations for Minecraft 1.21.1

The port registers the CMI materials, molds, casts, assembly intermediates and passive mechanisms listed in the startup scripts. It also registers peat, the retained ores and molten andesite alloy, dreamcore and mechanium. Create and KubeJS Create provide the sequenced assembly item type. The cast tags use the selected Tinkers' Construct namespace.

Run the registration builder from the migration branch for both sides.

```sh
python3 build_registrations.py path/to/startup_scripts/register path/to/target/kubejs/startup_scripts/cmi --tinkers-namespace modernfoundry
```

Reuse the pack's CMI and Nebula KubeJS assets on the client. To extract the mechanism textures from a local CMI Core JAR into the client assets, add `--core-art path/to/cmi-core.jar path/to/target/kubejs/assets`.

Generate the ore-drop datapack with the Minecraft 1.21.1 vanilla client JAR.

```sh
python3 build_ore_loot.py path/to/1.21.1.jar path/to/world/datapacks/cmi-ore-loot
```

Quartz drops quartz, certus quartz drops an AE2 crystal, and etrium drops raw etrium. Silk Touch drops the source ore. Peat burns for 3,200 ticks.
