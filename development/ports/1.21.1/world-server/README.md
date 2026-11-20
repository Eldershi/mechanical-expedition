# Expedition world and server adapters

Build with Java 21 and an installed Minecraft 1.21.1 NeoForge 21.1.267 dedicated server.

```sh
python3 build.py --java /path/to/java --server /path/to/server \
  --mods /path/to/mods --output /path/to/output \
  teleport motion-guard world-rules curse-rules equipment guide-tome railway twilight alpine
```

- `teleport` handles vanilla teleport commands while their destination chunks load. Install it on the server.
- `motion-guard` bounds invalid player movement and provides `/expeditiondiagnostics`. Install it on the server. The dedicated-server overlay includes `current/server/config/expedition-diagnostics.json` as `config/expedition-diagnostics.json`. This configuration enables event logging, watchdog incidents, and Spark exports, with JFR disabled.
- `world-rules` handles player damage, selective Born in Chaos spawning, Biomes O’ Plenty tall grass, and cryotheum. Install it on a dedicated server. Install it on the client for local worlds and cryotheum particles.
- `curse-rules` fits the Ring of the Seven Curses into a free ring slot on login, permits sleeping, and disables the ring's proximity anger and Enderman attraction. It also disables evoker-summoned vexes, selected natural spawns, and Spawn's ambient fly effects. Install it on the dedicated server.
- `equipment` enforces Curios slot types, retains the unlockable slot bonuses, and reconciles misplaced equipment at login. Put the JAR and `equipment/config/curios-common.toml` on both sides.
- `guide-tome` gives each player an Eccentric Tome with installed Patchouli and GuideME books plus registered native manuals. The server retries on a later login if there is no room in the player's inventory.
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

`migration/repair_surface_continuity.py` takes the archived terrain, the deployed transition, the current region files, a chunk scope, and terrain settings. It uses a continuous height field for the coastline, keeps rooted trees on their original ground, and protects current structures and block entities. Each output region retains the current version of chunks outside the scope.

`migration/restore_clipboard_contents.py` converts plain-text Create clipboard pages from the source world to NeoForge item components. The generated commands restore only existing clipboard blocks with empty pages and retain text, checkbox states, and the last open page.

`migration/prepare_region_copy.py --track-spawners` transfers TongDa track spawner block IDs and block entity IDs while retaining the saved track data. Old TongDa planning areas have a different size. The old route cache needs separate verification before reuse with the current planner. Use `--eidolon-ores` to transfer existing silver and lead ore palettes to the matching Eidolon Repraised IDs.

Use `migration/prepare_region_copy.py --create-curves` before opening the source regions in Minecraft 1.21.1. It converts Create's stored curve endpoint offsets to the target format. Use `migration/prepare_create_railway.py --source path/to/legacy/create_tracks.dat --output path/to/migrated/create_tracks.dat` to convert the matching saved graph's curves and its station, observer, and signal coordinates. Include all regions along the route when checking station or train connectivity.

Use `migration/splice_overworld_island.py` to keep an island and specified bridges in a fresh Overworld. Stop both copies before running it. Supply the old and pre-generated fresh `region` folders with `--source-regions` and `--fresh-regions`, and a new folder with `--output-regions`. Use the target pack and intended seed to generate every chunk around the selected island and structures. The tool leaves full core chunks and fresh chunks beyond the transition intact. It resets lighting and structure metadata in the transitioned chunks for the next server load.

The `--config` JSON specifies an inclusive `core` as `[minX, minZ, maxX, maxZ]`, optional `corner_radius`, and `widths.inner`, `widths.water`, and `widths.outer` in blocks. Set `sea_level` to the first block above the open water and use `sea_depth` to set the water-band depth. To keep a bridge, add a `protected_structures` entry with inclusive `boxes` as `[minX, minY, minZ, maxX, maxY, maxZ]` and the exact block IDs to transfer under `blocks`. A protected chunk combined with new terrain needs current block-entity data. Use `--structure-regions` to supply an upgraded copy for these chunks. The result is the terrain region directory. The JSON report lists the source and transitioned chunks for aligning entity, POI, and railway data when assembling the world.

Use `migration/merge_island_auxiliary.py` with the same closed worlds and a JSON chunk plan. Set `core` to `source_chunks` and `transition` to `transition_chunks` from the terrain report. The output supplies the Overworld's original entity and POI records for retained chunks and the fresh world's records outside the transition. Use the fresh Overworld generator definition in the assembled copy so future chunks match the generated exterior.

Build the optional `island-rail` module with the same build command. In the assembled copy, place `rail-blocks.json` in `config/expedition-island-rail/`. Its `rail_blocks` array contains the retained Create track blocks as objects with `id` and `pos` fields. After loading their chunks, run `expeditionislandrail` to drop one-ended curve references and build graphs from the actual tracks. This operation supports transfer copies without active trains, functional stations, or signals.

To reconnect an existing bridge and extend it straight to a new shore, provide `bridge-route.json` in the same configuration directory. The `origin`, `existingTrackEnd`, and `landTrackEnd` objects specify Create graph coordinates with `x`, `y`, and `z`. The `gapAnchors` and `shoreAnchors` arrays give ordered rail block coordinates, with Create shape names in `gapShape` and `shoreShape`. Supply both ends of each original curve as `first` and `second` in `retainedCurves`. Define the pier tops, deck width, landing blocks and stairs using `piers`, `deckHalfWidth`, `landingDeck`, and `landingStairs`. Each stair contains a `position` and an `ascent` direction. The `rockWitnesses` list gives solid blocks below and above the waterline at the new landing.

Load the bridge chunks and run `expeditionrailbridge build`, `expeditionrailbridge check`, `expeditionrailbridge land`, and `expeditionrailbridge check-land` in order. The checks traverse Create's graph in both directions. Save the copy after the checks pass and remove the transfer module before normal play.

To connect the shore rail to an adjoining Create line, use `through-route.json` with ordered `knots`. Each knot specifies a rail block with `x`, `y`, `z` and its forward horizontal heading with `dx`, `dz`. The first and last knots must match the approach shape of existing tracks. Set `factoryEnd` and `adjoiningEnd` to graph positions on the two retained lines and `minimumDistance` to the minimum through journey in blocks. The route uses [TongDa Railway 1.1.6](https://github.com/Hello-LuckyHuang/TongDaRailway/releases/tag/v1.1.6-NeoForge) for straight segments and eased curves. It adds a track bed and founded piers along the curved spans. Set `clearNaturalLogs` to true where the new corridor crosses undeveloped forest.

Load the entire connector, including neighboring blocks needed for the track bed. Run `expeditionrailthrough plan` to validate the geometry and affected terrain. Run `expeditionrailthrough build` to lay the connector, then `expeditionrailthrough check` to advance a native Create travelling point from the factory to the adjoining line and back. Repeat the check after saving and reopening the copy.

Run the [Create inventory converter](create-inventory-migration/README.md) on a closed source region copy before opening it with 1.21.1. Use its output for the remaining region transformations.

For a closed 1.21.1 migration copy containing Steam Letters contents, run `migration/replace_steam_letters_contents.py <world-copy> <new-output-directory>` with `nbtlib`. It exports only changed region and player files. Bronze casings become Create copper casings, stored steam becomes Mekanism steam at the saved volume, and retired recipe-book entries are removed. Overlay the output on the closed copy after checking the reported totals.

With `nbtlib==2.0.4` and NumPy, run `migration/migrate_quartz_and_peat.py <prepared-1.21.1-world> <new-world-copy>` before starting the server with the retired item registrations removed. Include the converted player inventories and backpack saved data in the prepared world. The script maps both CMI ordinary quartz ores to vanilla Nether quartz ore at the same positions and replaces placed CMI peat with mud. Stored ore, peat, peat blocks and enriched silicon become Nether quartz ore, charcoal, coal coke and single crystal silicon, respectively. The report counts blocks and stored items, and ME cells combine equivalent item keys while retaining their summed quantities. Keep the source archive and any separate inventory recovery files for review.

Stored copies of the strange parchment and its two fragments become individually named paper. Frost cake and its base become individually named pumpkin pies, which can hold the original stack sizes. The migration preserves counts and existing names, and removes the parchment-specific advancement records and obsolete recipe book entries from the copied world.

Run `migration/restore_legacy_deposits.py <closed-legacy-archive> <closed-prepared-copy> <new-overlay-directory>` with the same dependencies. Apply the reported region overlay to the prepared copy before starting the server. It restores supported deposit blocks, registered structure starts and references, and pending Rock & Stone mining records at matching bearings. It stops if a deposit would overwrite a different placed block or a mining record has no matching bearing. The space compatibility module keeps a pending process in the saved bearing data while the native miner waits to initialize it.

Build the optional `block-catalog` module and start it in a disposable server with the target pack. It exports `block-catalog.json` to the server directory. Run `migration/audit_block_palettes.py <closed-world> <block-catalog.json> <new-report-directory> --discovery` with nbtlib and NumPy. If the audit produces `legacy-block-states.jsonl`, copy it to the catalog server directory and restart the server to resolve saved block states through native data fixes and registry aliases. Run the audit again with the updated catalog, a new report directory, and no discovery flag. The summary counts occupied blocks and native conversions. Each row of `positions.tsv.gz` gives an inclusive X range at the stated dimension, Y and Z. Optional `--areas` entries specify a `dimension`, inclusive XYZ `min` and `max`, ID `prefixes`, and a `kind` of `industrial` or `generated_structure`.

Run `migration/remap_retired_blocks.py <closed-world> <block-catalog.json> <new-world-copy>` to apply `retired_block_mappings.json`. The converter requires matching state properties and rejects replacements involving saved block entities. Loose Seared Bricks migrate to Modern Foundry only in the native state that needs no block entity. The converter writes a new world copy and reports exact changed counts and sample coordinates. Verify the report against the audit and check the sample coordinates after saving and restarting a disposable copy of the result.

Run `migration/remove_legacy_rock_generators.py <closed-world> <new-world-copy>` to remove retired Thermal rock generators and their saved items. It replaces placed devices with air, removes their matching block entities, and clears saved item stacks and dropped items using the same ID. It checks the copied save for unsupported references before publishing the output and retains historical player statistics.

Run `migration/apply_residual_block_policy.py <closed-world> <block-catalog.json> <target-loot-tables.json> <new-world-copy>` to apply `residual_block_policy.json`. Export the installed target loot table IDs as a JSON array. The policy uses compatible rock for retired ores, removes retired vegetation, and preserves the states of compatible shaped construction blocks. It migrates unopened Quark warped and prismarine Lootr trapped chests to their current IDs while preserving the chest identity, state, loot table and seed. Chests with prior opener or per-player inventory data need a compatible inventory conversion. The converter checks destination schemas, writes a new copy, and reports counts and sample positions.

The remaining Terramity and Malum fixtures in the policy become air. The converter removes matching scheduled Prism Solution ticks and verifies that the retired containers and ritual core have no stored items or active ritual state before removing their block entities.

The space installer builds the Rock & Stone deposit data and registers the saved CMI mineral nodes. New CMI mineral nodes generate for vanadium in the Nether. Its mining recipe uses the native mining bearing and four shattering resonators. The ore roll is 30% with lava overclock enabled at 20 mB per cycle. Mining the resulting ore with a suitable pickaxe yields raw vanadium. Expended deposits use the native depleted deposit block. Stored deposit dust keeps its item ID.

`migration/build_village_processors.py` uses the installed legacy CTOV 3.4.14 JAR to provide two processor lists referenced by old mountain village pieces. Put the ZIP in the migrated world's `datapacks` directory. `migration/measure_chunk_edges.py` compares boundary heights, local gradients, and surface biome changes on a migrated copy.
