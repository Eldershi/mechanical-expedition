# AuraTip event compatibility

AuraTip 1.1.1-beta uses OELib's client tick and input event types. With OELib 0.3.1, this patch subscribes its tick handler to `ClientTickEvent.Post` and its existing keyboard and mouse handlers to Forge's client input events. The handler bodies, assets and MIT license remain in the archive.

```sh
python3 build.py --input /path/to/auratip-forge-1.20.1-1.1.1-beta.jar \
  --output-dir /path/to/output --java-home /path/to/java17 \
  --asm-root /path/to/libraries/org/ow2/asm
```

The builder requires the official input SHA-256, uses ASM 9.8, and checks that only `ClientEventHandler.class` and `ClientInputHandler.class` change. The output manifest records both archive hashes. Install the resulting JAR in place of the original AuraTip JAR.
