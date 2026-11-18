# Expedition events on NeoForge 1.21.1

The player notices use KubeJS. Install `server_scripts/ExpeditionPlayerNotices.js` in `kubejs/server_scripts` on the server and in the client instance for integrated worlds. Merge `client_assets` into `kubejs/assets` for the translated messages. The dragon completion notice keeps the player's `dragon_death` stage and uses the CMI sound already present in the client assets.

Build the optional JEI output labels with `client/build.py --adapter recipe-routes`. Install the resulting JAR on the client alongside JEI 19.64.0.455. The output labels cover Expedition recipe routes and KubeJS recipes. `kubejs/config/expedition-recipe-labels.json` can provide `original` and `modified` lists of exact recipe IDs for additional routes.
