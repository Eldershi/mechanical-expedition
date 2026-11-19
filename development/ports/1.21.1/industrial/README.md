# Storage and engineering compatibility

Build these add-ons with Java 21 against the NeoForge 1.21.1 test server. Install the compiled JARs on the client and server.

```sh
python3 build.py storage-adjustments --java /path/to/java --server /path/to/neoforge-server --output /path/to/output
python3 build.py engineering-adjustments --java /path/to/java --server /path/to/neoforge-server --output /path/to/output
python3 build.py refinery-steam-compat --java /path/to/java --server /path/to/neoforge-server --output /path/to/output
python3 build.py liquefied-gases --java /path/to/java --server /path/to/neoforge-server --output /path/to/output
```

Storage capacity upgrades sum their multipliers in Sophisticated storage and Functional Storage drawers. Drawer storage upgrades require a single tier. Removing or replacing a Sophisticated upgrade checks the projected capacity against the items already stored.

The top hatch of the Immersive Engineering Arc Furnace exposes its three graphite electrode slots for item automation.

Connect a Create Crafted Beginning airtight pipe to either of the Immersive Engineering Refinery’s original fluid inlets. Pressurized steam enters the existing input tank at one millibucket per gas unit. The other tank can receive fuel through a fluid pipe. This add-on uses Mekanism steam internally and pairs with the gasoline and diesel cracking recipes in the [industry overlay](../industry).

Fluids tagged `expedition:piped_liquefied_gases` use ordinary fluid pipes, machine tanks and storage tanks. Bucket pickup, filling, draining and pouring are disabled for those fluids. The industry overlay supplies the tag and the natural-air fractionation recipe.
