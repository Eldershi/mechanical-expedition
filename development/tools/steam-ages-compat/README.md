# Steam Ages and Steam Letters compatibility

Steam Ages shares its boiler registry with Steam Letters 2.0.1. Its compatibility build disables the duplicate `BoilerDataMixin` and requires that Steam Letters version. All other client classes, assets and data remain intact.

The dedicated-server variant additionally omits the two client render suppliers in fluid registration. Fluid, bucket and tag registrations remain present. Use the client artifact on clients and the artifact under `server/` on dedicated servers.

```sh
python3 build.py --input /path/to/Create-Steam-Ages-1.0.jar \
  --output-dir /path/to/output --java-home /path/to/java17 \
  --asm-root /path/to/libraries/org/ow2/asm
```

The builder checks the original archive hash, verifies the changed archive members, and writes the client and server hashes to `manifest.json`.
