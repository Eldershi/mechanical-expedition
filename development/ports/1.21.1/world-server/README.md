# Expedition world and server adapters

Build with Java 21 and an installed Minecraft 1.21.1 NeoForge 21.1.267 dedicated server.

```sh
python3 build.py --java /path/to/java --server /path/to/server \
  --output /path/to/output teleport motion-guard alpine
```

- `teleport` handles vanilla teleport commands while their destination chunks load. Install it on the server.
- `motion-guard` bounds invalid player movement and provides `/expeditiondiagnostics`. Install it on the server. It uses `config/expedition-diagnostics.json` when present.
- `alpine` applies the Expedition mountain temperature and surface rules. Its placement modifier can enforce the treeline on selected tree features.

Build the Alpine tree placement overlay from the candidate's installed mod JARs and the installed Minecraft server's `server-*-extra.jar` under `libraries/net/minecraft/server`.

```sh
python3 alpine/build_treeline_pack.py --vanilla-data /path/to/server-extra.jar \
  --mods /path/to/mods --output /path/to/expedition-alpine-treeline.zip
```

The script reports old feature IDs absent in the candidate. The Alpine JAR passed climate and treeline checks with Tectonic. Full-pack feature loading and terrain continuity on the save copy are pending.
