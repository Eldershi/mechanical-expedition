# Client adapters for NeoForge 1.21.1

Build the spell Ponder adapter with `build.py --adapter spells` and install the resulting JAR on the client. Both the client and dedicated server need Iron's Spells 'n Spellbooks and Iron's Spells 'n Spellbooks Ponder. The client adapter uses the Ponder API provided by the spell preview mod.

The native Ponder index shows enabled spell schools as school-specific scrolls. Each school opens a paginated grid with spell icons. In the preview, the bottom-left spell icon opens the school index, the projection fills the scene area, and the right-hand panel shows casting parameters.

The preview controls read Minecraft's active button sprites. For the Expedition layout, fetch the original Create MC GUI archive from the launcher reference in `create-mcgui.json` and enable the entry in the client's Paxi resource-pack load order.

Build the resource compatibility packs with `build_visual_overlays.py compatibility <output-zip> --source <ae2-jar>`. The compatibility pack supplies the original 64×64 AE2 charger texture for the active charger model. Keep the compatibility pack above the AE2 resource packs in Paxi.
