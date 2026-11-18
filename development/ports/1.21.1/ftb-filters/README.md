# Expedition quest data for NeoForge 1.21.1

Generate a new FTB Quests tree from the 1.20.1 quest directory using Java 21 and the libraries of the installed NeoForge test server.

```sh
python3 convert.py --java /path/to/java --server /path/to/neoforge-server \
  --mapping expedition-mappings.snbt /path/to/old/quests /path/to/new/quests
```

Install the generated tree at `config/ftbquests/quests`. Copy the KubeJS startup script to both sides and the server scripts to the logical server. Install the starter kit model and merge the language entries into the client resource pack.

The converter keeps quest and reward IDs and the IDs of all retained tasks. Old item filters become FTB Filter System smart filters. The mapping also reconciles direct item stacks in tasks, rewards and icons. Ender IO conduit tasks use strict matching against the conduit type component. The alternate seawater quest checks the solution produced by the Create mixer. The oil chapter checks obtainable fractions, and the refinery tasks use Immersive Engineering's multiblock formation advancement.
