# Expedition world and server adapters

Build with Java 21 and an installed Minecraft 1.21.1 NeoForge 21.1.267 dedicated server.

```sh
python3 build.py --java /path/to/java --server /path/to/server \
  --mods /path/to/mods --output /path/to/output \
  teleport motion-guard world-rules equipment railway twilight alpine
```

- `teleport` handles vanilla teleport commands while their destination chunks load. Install it on the server.
- `motion-guard` bounds invalid player movement and provides `/expeditiondiagnostics`. Install it on the server. It uses `config/expedition-diagnostics.json` when present.
- `world-rules` handles player damage, selective Born in Chaos spawning, Biomes O’ Plenty tall grass, and cryotheum. Install it on a dedicated server. Install it on the client for local worlds and cryotheum particles.
- `equipment` enforces Curios slot types, retains the unlockable slot bonuses, and reconciles misplaced equipment at login. Put the JAR and `equipment/config/curios-common.toml` on both sides.
- `railway` prevents new structure pieces from crossing planned TongDa Railway tracks and stations. Install it on the dedicated server or integrated server.
- `twilight` controls Twilight Forest landmark density. Install it on both sides for its placement registry. Copy `development/servers/cmi-expedition/deployment/config/expedition-boss-density.json` to the server's `config` directory.
- `alpine` applies the Expedition mountain temperature and surface rules. Its placement modifier can enforce the treeline on selected tree features.

Build the Alpine tree placement overlay from the candidate's installed mod JARs and the installed Minecraft server's `server-*-extra.jar` under `libraries/net/minecraft/server`.

```sh
python3 alpine/build_treeline_pack.py --vanilla-data /path/to/server-extra.jar \
  --mods /path/to/mods --output /path/to/expedition-alpine-treeline.zip
```

Place the generated ZIP in the world's `datapacks` directory and enable it. The overlay loaded 40 current tree placements with Tectonic, Terralith, Biomes O’ Plenty, Regions Unexplored, Biomes We've Gone, and Geophilic.

`migration/migrate_level_metadata.py` uses `nbtlib` to write a candidate `level.dat` from the source world and a fresh world made with the target pack. The loaded 1.21.1 pack selects its current Overworld preset and retains the source seed. Keep the existing region files, including partially generated chunks that continue the old biomes near explored terrain.

`migration/prepare_region_copy.py --track-spawners` transfers TongDa track spawner block IDs and block entity IDs while retaining the saved track data. Old TongDa planning areas have a different size. The old route cache needs separate verification before reuse with the current planner. Use `--eidolon-ores` to transfer existing silver and lead ore palettes to the matching Eidolon Repraised IDs.

`migration/build_village_processors.py` uses the installed legacy CTOV 3.4.14 JAR to provide two processor lists referenced by old mountain village pieces. Put the ZIP in the migrated world's `datapacks` directory. `migration/measure_chunk_edges.py` compares boundary heights, local gradients, and surface biome changes on a migrated copy.
