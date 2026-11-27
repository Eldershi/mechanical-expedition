# Client adapters for NeoForge 1.21.1

Build the spell Ponder adapter with `build.py --adapter spells` and install the resulting JAR on the client. Both the client and dedicated server need Iron's Spells 'n Spellbooks and Iron's Spells 'n Spellbooks Ponder. The client adapter uses the Ponder API provided by the spell preview mod.

The native Ponder index shows enabled spell schools as school-specific scrolls. Each school opens a paginated grid with spell icons. In the preview, the bottom-left spell icon opens the school index, the projection fills the scene area, and the right-hand panel shows casting parameters.

The preview controls read Minecraft's active button sprites. For the Expedition layout, fetch the original Create MC GUI archive from the launcher reference in `create-mcgui.json` and enable the entry in the client's Paxi resource-pack load order.

Build the resource compatibility packs with `build_visual_overlays.py compatibility <output-zip> --source <ae2-jar>`. The compatibility pack supplies the original 64×64 AE2 charger texture for the active charger model. Keep the compatibility pack above the AE2 resource packs in Paxi.

Distant Horizons 3.3.3 uses a 64-chunk LOD radius and four worker threads on the client. Build its Chunky compatibility adapter with `build.py --adapter chunky` and its client queue adapter with `build.py --adapter performance`. The dedicated server uses the Chunky adapter and a separate Distant Horizons configuration with two worker threads and LOD generation from existing chunks.

The client performance adapter uses Sodium 0.8.13's horizontal terrain radius for all elevations. Client builds exclude Better FPS Render Distance, which would apply a second distance check to terrain and entities.

Build the accessory panel with `build.py --adapter accessory-entry` and install the same JAR on the client and dedicated server. It uses native Curios and Accessories item slots, including the Aether slots registered with Accessories. The two sections, equipment visibility, cosmetics, armor and crafting share one menu.

Build the quest lines adapter with `build.py --adapter quest-lines` and install the JAR on the client. It draws Quest Enhance's decorative connections after Certain Questing Additions draws the quest background. Decorative connections use the pack's dependency-line texture and muted tint with a finer stroke for dense chapters.
