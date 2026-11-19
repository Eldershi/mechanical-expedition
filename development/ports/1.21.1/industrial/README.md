# Storage and engineering adjustments

Build these add-ons with Java 21 and a NeoForge 1.21.1 server that has Functional Storage, Sophisticated Core, Titanium, and Immersive Engineering. Install the compiled JARs on the client and server.

```sh
python3 build.py storage-adjustments --java /path/to/java --server /path/to/neoforge-server --output /path/to/output
python3 build.py engineering-adjustments --java /path/to/java --server /path/to/neoforge-server --output /path/to/output
```

Storage capacity upgrades sum their multipliers in Sophisticated storage and Functional Storage drawers. Drawer storage upgrades require a single tier. Removing or replacing a Sophisticated upgrade checks the projected capacity against the items already stored.

The top hatch of the Immersive Engineering Arc Furnace exposes its three graphite electrode slots for item automation.
