# Flight and pneumatic engineering

Use the NeoForge 1.21.1 files pinned in the [mod manifest](../community-mods.json). Install Crafted Beginning, Create Aeronautics, Sable, Aeronautics Compatibility and Jade Sable Compat on both sides. Sable supplies the physics runtime. Aeronautics Compatibility supplies the Citadel integration for moving structures. Jade Sable Compat exposes machine information on moving sublevels.

Build and install the storage-manager compatibility add-on on both sides.

```sh
python3 ../industrial/build.py flight-pneumatics-compat \
  --java /path/to/java --server /path/to/neo-server --output /path/to/mods
```

The storage manager's ordinary Create mixing and compacting planners exclude Crafted Beginning's chilled recipes. Chilled processing requires its dedicated machinery and still works through its own recipe manager.

After converting the FTB data, copy the two chapters under `quests/chapters` into `config/ftbquests/quests/chapters`. The chapters add optional pneumatic and flight branches. Install `ExpeditionPneumaticSealing.js`, `ExpeditionControlComponents.js` and `ExpeditionManufacturingContinuity.js` from [the industry overlay](../industry/kubejs/server_scripts) with the other server scripts.

The gas branch starts with airtight sheets, pipes and storage. A shaft-driven pump supplies the network. A pressure gauge and regulating pump support monitoring and control. The pressure exercise uses the regulator to fill a sealed tank and then evacuate it. The CMI sealing recipe uses an injection chamber two blocks above its basin. It requires 1.25 atm absolute pressure and consumes 1,000 units of natural air per unfinished mechanism. Forging and gas fractionation are parallel branches. Diesel Generators and Immersive Engineering supply the existing liquid fuel and plastics routes. AE2 and the integrated workstation handle circuit and component production.

The flight branch starts with a physics assembler. Make a propeller bearing and a portable engine to complete the propulsion task. Simulated's native dyeing recipe accepts the crafted red engine and white dye for the white engine requested by the task. A burner heats balloons, and Levitite can support a hovering frame. Climbing requires additional upward thrust. The gyroscopic bearing is the final stabilization task.
