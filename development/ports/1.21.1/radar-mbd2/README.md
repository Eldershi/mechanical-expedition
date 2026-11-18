# Radar antenna for NeoForge 1.21.1

The radar uses Multiblocked2 and LDLib2 for its 51-block structure, menu, item slots, and processing. The KubeJS tick hook in `../native-events/server_scripts/RadarEnergySlot.js` moves up to 1,000 FE per tick from an inserted battery through NeoForge's item energy capability.

## Installation

Run `python3 development/ports/1.21.1/radar-mbd2/convert_project.py pack/ldlib/assets/mbd2 /path/to/radar-output` from the repository root with `nbtlib` installed. Copy the generated `ldlib2` directory and both KubeJS startup scripts into the client and dedicated server. Copy `kubejs/client_scripts/RadarAcquisitionLanguage.js` to the client. Copy both KubeJS server scripts and the battery tick hook into the dedicated server or single-player instance. Use the CMI aviation disk item registrations and the radar and smart casing models and textures from `pack/kubejs/assets/cmi`.

The controller has item input, item output, FE storage, and a battery slot. Items and FE can also enter through adjacent automation. A processing tier consumes 1,000,000, 2,000,000, 5,000,000, or 10,000,000 FE and produces the corresponding CMI aviation disk.

## Survival acquisition

The NeoECOAE integrated working station makes the controller and five radar components. The controller consumes 16,000 AE and uses stainless steel plates, optical fiber, ferrite cores, an ME terminal, and a smart mechanism. The acquisition scripts use the pack's metallurgy, oil, silicone, and polymer recipes. The optical fiber insulation uses CMI silicone rubber.

Create makes the empty disk from an aluminum plate through two deployers, the Vintage Improvements laser, and the W-shaped curving head. The laser uses 4,000 FE. A heated Create basin produces the smart casing, engineering mechanism part, and smart mechanism augment before the integrated working station becomes available. The casing uses solid and liquid silicone rubber. The smart mechanism uses a six-step Create sequence. The aeronautic mechanism uses the integrated working station to combine its base, space parts, and structural plastic.

## Runtime verification

Compile `tests/RadarAcceptance.java` as a test-only NeoForge mod against the target loader, Multiblocked2, and LDLib2, using mod ID `expedition_radar_native_probe`. Copy `tests/assembly.tsv` to the test server as `radar-assembly.tsv`. Use a disposable world. The console command `expeditionradarproof` builds the reference layout near the origin, waits for normal formation, checks the menu bindings, inserts the empty disk through the NeoForge item capability, and waits for each actual recipe output. It also checks the battery transfer, missing-power behavior, and structure revalidation. The test passes when the server logs `EXPEDITION_RADAR_NATIVE_FULL_PASS`.

Compile `tests/RadarAcquisitionAcceptance.java` against the target loader, Create, Vintage Improvements, AE2, and NeoECOAE, using mod ID `expedition_radar_acquisition_probe`. In a disposable world, run `expeditionradaracquisition` once per server launch. The command exercises the empty disk and smart mechanism sequences through Create's recipe API, runs a heated mechanical press for the three early components, and supplies items, fluids, and AE to a working station for the nine later outputs. The test passes when the server logs `EXPEDITION_RADAR_ACQUISITION_PASS`.
