# Industrial compatibility for NeoForge 1.21.1

Install the `kubejs` scripts and data alongside the CMI material registrations. The recipes provide the copper, railway, Nether, precision, and coil mechanism lines. They also restore the cast iron and steel processes, seawater and lithium processing, and the Hexa casting and remelting routes for CMI mechanism bases and molds.

The advanced spout and steam hammer have independent CMI recipes alongside the recipes shipped by Steam Letters. The CMI spout recipe uses a Create belt connector as the seal. Steam Letters supplies the normal and superheated fluids for steam mixing. The Steam Letters KubeJS builders register the CMI cast iron and steel steam tiers.

Build the Steam Letters migration adapter with Java 21 and an installed NeoForge 1.21.1 server. Install the resulting JAR on both the client and server.

```sh
python3 build.py --java /path/to/java --server /path/to/neoforge-server --output /path/to/output
```

The adapter resolves the old CMI advanced spout, steam hammer, bronze solar boiler, and bronze fluid burner to their Steam Letters equivalents. It converts saved fluid payloads for these machines, the cast iron and steel steam tiers, and Create tanks. Saved Mekanism steam in a steam tank becomes Steam Letters steam. Create Steam Ages fluids and buckets resolve to the normal and superheated equivalents. Placeable steam fluid blocks require a separate world conversion if present. Legacy fluid metadata that has no equivalent goes into `NeoForgeData.expedition:legacy_fluid_tanks` for inspection.

The Steam Letters archive provides the bronze device sprites. Expose those sprites to the cast iron and steel models using the client's existing Steam Letters archive and KubeJS assets directory.

```sh
python3 build_steam_texture_aliases.py --steam-letters /path/to/Steam-Letters.jar --assets /path/to/kubejs/assets
```
