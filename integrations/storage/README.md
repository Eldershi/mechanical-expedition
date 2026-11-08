# Display-only Stockpile Switch

For Create 6.0.8 on Minecraft 1.20.1, a Stockpile Switch used only as a display source uses an upper threshold of 1 item, a lower threshold of 0 items, and inverted output. The item filter remains empty so the switch measures the whole attached inventory.

A nonempty inventory produces no redstone signal. An empty inventory produces a signal until items arrive. This keeps an adjacent Stock Link available whenever the inventory contains items. Stock measurement and display links remain active. This preset is unsuitable for switches that control production using other thresholds.

`display-only-stockpile-switch.json` contains the persistent settings. The accompanying function applies them to the block at the execution position and forces the switch to recalculate its output on its next inventory update. It preserves the inventory, filter, orientation, and display connections.

To use the function, copy it to `data/expedition/functions/storage/display_only_stockpile_switch.mcfunction` in an enabled datapack, reload datapacks, and run `execute positioned <x> <y> <z> run function expedition:storage/display_only_stockpile_switch` in the target dimension. The function is an explicit administrator action; it is not a tick or load function and does not configure other switches automatically.
