# Industrial compatibility for NeoForge 1.21.1

Install the scripts under `kubejs/server_scripts` alongside the CMI material registrations. The advanced spout and steam hammer have independent CMI recipes alongside the recipes shipped by Steam Letters. The CMI spout recipe uses a Create belt connector as the seal. Steam Letters supplies the fluids for the normal and superheated steam mixer recipes. Hexa supplies the casting table serializer for the three CMI mechanism basements, each of which accepts both reusable and single-use casts.

Build the Steam Letters migration adapter with Java 21 and an installed NeoForge 1.21.1 server. Install the resulting JAR on both the client and server.

```sh
python3 build.py --java /path/to/java --server /path/to/neoforge-server --output /path/to/output
```

The adapter resolves the old CMI advanced spout and steam hammer block, item and block entity IDs to their Steam Letters equivalents. It converts their old fluid payloads to the NeoForge fluid format and preserves their process data. Legacy Mekanism steam in the hammer becomes Steam Letters steam. Legacy fluid metadata that has no equivalent goes into `NeoForgeData.expedition:legacy_fluid_tanks` for inspection.
