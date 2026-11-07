# FTB Teams client compatibility

Client-only Forge 1.20.1 add-on for FTB Teams 2001.3.2. Team self lookup uses the current connection's server-accepted GameProfile UUID. This supports servers whose accepted UUID differs from the launcher's session UUID. The launcher identity is retained only when there is no active connection.

The party creation invitation list sorts KnownClientPlayer records by case-insensitive name and UUID instead of requiring Comparable. The original FTB Teams jar, network protocol, server authentication settings, permissions, team membership, claims and quest progress are unchanged.

Run `python3 build.py --instance /path/to/client --libraries /path/to/libraries --java-home /path/to/jdk17`. The build checks both redirects with the bundled Mixin transformer and verifies transformed bytecode. Install the resulting jar from `build/` into the client `mods/` directory, then restart Minecraft. No server installation is required.
