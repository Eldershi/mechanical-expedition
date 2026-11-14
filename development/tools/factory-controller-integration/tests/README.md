# Factory Controller runtime probe

This probe runs only in an isolated Minecraft 1.20.1 Forge server. It creates and removes temporary Mechanical Crafter walls in the test world; do not install it in a production instance.

The verified dependency combination is Java 17, Forge 47.4.10, Create 6.0.8, Factory Controller 1.2.1 Forge, God Damn Repackager 0.5.1 Forge Alpha, Fluid Logistics 1.3.1, Additional Logistics 1.4.5, and Mobile Packages 0.6.1. Supply the matching Forge libraries and test-server mods directory to the builder. Embedded mod dependencies are extracted only into a temporary compilation directory.

## Coverage

- 5×5 crushing-wheel patterns: one craft and a batch of two crafts, using 21 ingredients per craft.
- Two separately sourced package fragments: completeness detection, ingredient conservation, one output package per craft, and preservation of all 25 pattern cells.
- Real connected 5×5 crafter inventories: simulated insertion preserves world inventories and original package NBT; actual insertion places one ingredient in every intended nonempty slot.
- A 3×3 chest pattern with eight ingredients provides the small-recipe regression check.
- Runtime availability of `ResourceLocation.fromNamespaceAndPath` is recorded in the result.

The probe supplies crafting contexts directly. It does not cover GUI configuration, end-to-end Stock Keeper orders, parallel repackager scheduling, or the final output of a powered kinetic crafting cycle.

## Build and run

```sh
python3 build_probe.py \
  --libraries /path/to/forge/libraries \
  --mods /path/to/isolated-server/mods \
  --output /path/to/isolated-server/mods/expedition-factorycontroller-runtime-probe.jar
```

Use `--javac /path/to/jdk17/bin/javac` if the default compiler is not Java 17. The builder requires an explicit output path and leaves no compiled dependencies beside the source.

Add this JVM option to the isolated server's normal Forge launch command:

```text
-Dexpedition.factorycontroller.probe=true
```

The probe runs once after five server ticks. It writes `factorycontroller-probe-result.json` in the server working directory and prints `FACTORY_CONTROLLER_PROBE_OK` or `FACTORY_CONTROLLER_PROBE_FAILED`. An optional `-Dexpedition.factorycontroller.probe.result=/path/to/result.json` selects another result file. The probe requires the explicit JVM opt-in and does not stop the server automatically. Remove its JAR after testing.
