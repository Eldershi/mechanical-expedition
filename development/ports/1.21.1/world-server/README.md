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
- `twilight` controls nine Twilight Forest landmark placements. Install it on both sides for its placement registry. Copy `development/servers/cmi-expedition/deployment/config/expedition-boss-density.json` to the server's `config` directory. The native structure search still finds saved starts after the placement density changes.
- `alpine` applies the Expedition mountain temperature and surface rules. Its placement modifier can enforce the treeline on selected tree features.

Compile `twilight/tests/TwilightIntegrationProbe.java` as test-only mod `expedition_twilight_integration_probe` against the target loader, Twilight Forest, and the Twilight adapter. In a disposable copy, run `expeditionspecialboss generate`, then save and stop. Set the Naga courtyard frequency to `1e-12` in that copy's config and restart. Run `expeditionspecialboss reopen` to check that the saved courtyard still resolves through native structure search from an unloaded chunk. Each command reports `EXPEDITION_SPECIAL_BOSS_PASS` on success.

Build the Alpine tree placement overlay from the candidate's installed mod JARs and the installed Minecraft server's `server-*-extra.jar` under `libraries/net/minecraft/server`.

```sh
python3 alpine/build_treeline_pack.py --vanilla-data /path/to/server-extra.jar \
  --mods /path/to/mods --output /path/to/expedition-alpine-treeline.zip
```

Place the generated ZIP in the world's `datapacks` directory and enable it. The overlay loaded 40 current tree placements with Tectonic, Terralith, Biomes O’ Plenty, Regions Unexplored, Biomes We've Gone, and Geophilic.

`migration/migrate_level_metadata.py` uses `nbtlib` to write a candidate `level.dat` from the source world and a fresh world made with the target pack. It retains the source seed and converts the saved Overworld generator. Lithostitched wraps the migrated biome source, and the target pack applies its current generation rules. A full Overworld transfer includes the partially generated region data that continues the old biomes near explored terrain.

`migration/prepare_region_copy.py --track-spawners` transfers TongDa track spawner block IDs and block entity IDs while retaining the saved track data. Old TongDa planning areas have a different size. The old route cache needs separate verification before reuse with the current planner. Use `--eidolon-ores` to transfer existing silver and lead ore palettes to the matching Eidolon Repraised IDs.

Use `migration/prepare_region_copy.py --create-curves` before opening the source regions in Minecraft 1.21.1. It converts Create's stored curve endpoint offsets to the target format. Use `migration/prepare_create_railway.py --source path/to/legacy/create_tracks.dat --output path/to/migrated/create_tracks.dat` to convert the matching saved graph's curves and its station, observer, and signal coordinates. Include all regions along the route when checking station or train connectivity.

Use `migration/splice_overworld_island.py` to keep an island and specified bridges in a fresh Overworld. Stop both copies before running it. Supply the old and pre-generated fresh `region` folders with `--source-regions` and `--fresh-regions`, and a new folder with `--output-regions`. Use the target pack and intended seed to generate every chunk around the selected island and structures. The tool leaves full core chunks and fresh chunks beyond the transition intact. It resets lighting and structure metadata in the transitioned chunks for the next server load.

The `--config` JSON specifies an inclusive `core` as `[minX, minZ, maxX, maxZ]`, optional `corner_radius`, and `widths.inner`, `widths.water`, and `widths.outer` in blocks. Set `sea_level` to the first block above the open water and use `sea_depth` to set the water-band depth. To keep a bridge, add a `protected_structures` entry with inclusive `boxes` as `[minX, minY, minZ, maxX, maxY, maxZ]` and the exact block IDs to transfer under `blocks`. A protected chunk combined with new terrain needs current block-entity data. Use `--structure-regions` to supply an upgraded copy for these chunks. The result is the terrain region directory. The JSON report lists the source and transitioned chunks for aligning entity, POI, and railway data when assembling the world.

Use `migration/merge_island_auxiliary.py` with the same closed worlds and a JSON chunk plan. Set `core` to `source_chunks` and `transition` to `transition_chunks` from the terrain report. The output supplies the Overworld's original entity and POI records for retained chunks and the fresh world's records outside the transition. Use the fresh Overworld generator definition in the assembled copy so future chunks match the generated exterior.

Build the optional `island-rail` module with the same build command. In the assembled copy, place `rail-blocks.json` in `config/expedition-island-rail/`. Its `rail_blocks` array contains the retained Create track blocks as objects with `id` and `pos` fields. After loading their chunks, run `expeditionislandrail` to drop one-ended curve references and build graphs from the actual tracks. This operation supports transfer copies without active trains, functional stations, or signals.

To reconnect an existing bridge and extend it straight to a new shore, provide `bridge-route.json` in the same configuration directory. The `origin`, `existingTrackEnd`, and `landTrackEnd` objects specify Create graph coordinates with `x`, `y`, and `z`. The `gapAnchors` and `shoreAnchors` arrays give ordered rail block coordinates, with Create shape names in `gapShape` and `shoreShape`. Supply both ends of each original curve as `first` and `second` in `retainedCurves`. Define the pier tops, deck width, landing blocks and stairs using `piers`, `deckHalfWidth`, `landingDeck`, and `landingStairs`. Each stair contains a `position` and an `ascent` direction. The `rockWitnesses` list gives solid blocks below and above the waterline at the new landing.

Load the bridge chunks and run `expeditionrailbridge build`, `expeditionrailbridge check`, `expeditionrailbridge land`, and `expeditionrailbridge check-land` in order. The checks traverse Create's graph in both directions. Save the copy after the checks pass and remove the transfer module before normal play.

Run the [Create inventory converter](create-inventory-migration/README.md) on a closed source region copy before opening it with 1.21.1. Use its output for the remaining region transformations.

For a closed 1.21.1 migration copy containing Steam Letters contents, run `migration/replace_steam_letters_contents.py <world-copy> <new-output-directory>` with `nbtlib`. It exports only changed region and player files. Bronze casings become Create copper casings, stored steam becomes Mekanism steam at the saved volume, and retired recipe-book entries are removed. Overlay the output on the closed copy after checking the reported totals.

`migration/build_village_processors.py` uses the installed legacy CTOV 3.4.14 JAR to provide two processor lists referenced by old mountain village pieces. Put the ZIP in the migrated world's `datapacks` directory. `migration/measure_chunk_edges.py` compares boundary heights, local gradients, and surface biome changes on a migrated copy.
