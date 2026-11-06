# Maid Spell existing-world guard

Version 1.0.1 targets Maid Spell `1.9.3.2-forge+mc1.20.1`. The common Mixin cancels `StellarEndshoreFixedSpawn.onServerStarted` when the overworld game time is greater than zero. It supports dedicated and integrated servers. Worlds at time zero retain the original scheduling path.

```sh
python3 build.py --spell /path/to/touhou_little_maid_spell-1.9.3.2-forge+mc1.20.1-all.jar \
  --output-dir /path/to/output
```

The builder extracts the official nested runtime JAR for compilation and verification. It applies the actual Mixin transformer, verifies the transformed callback and the six unchanged methods, and checks scheduling behavior at zero, positive and negative game times. The official Maid Spell JAR is retained as a separate dependency.
