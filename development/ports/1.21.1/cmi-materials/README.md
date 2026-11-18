# CMI minerals and peat for Minecraft 1.21.1

Install `CmiMineralsAndPeat.js` in the client and server KubeJS startup scripts. It registers peat, dreamcore ore, the stone and deepslate variants of quartz, certus quartz and etrium, and raw etrium. Keep a single startup registration for each of these IDs. The client uses the corresponding CMI textures and the Nebula ore model already supplied in the pack's KubeJS assets.

Generate the world datapack with the Minecraft 1.21.1 vanilla client JAR.

```sh
python3 build_ore_loot.py path/to/1.21.1.jar path/to/cmi-ore-loot
```

Install the output in the world's `datapacks` directory. Quartz drops quartz, certus quartz drops an AE2 certus quartz crystal, and etrium drops raw etrium. Silk Touch drops the source ore. Peat burns for 3,200 ticks.
