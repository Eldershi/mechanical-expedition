# Hosted server bootstrap

The bootstrap forwards the hosting console to the dedicated server and returns the child process's exit code. On shutdown it requests a Minecraft save and stop before escalating to process termination.

For a host that launches a JAR and runs Minecraft 1.21.1 with NeoForge, build with Java 21.

```sh
sh build.sh
python3 package.py build --neoforge expedition-neoforge 21.1.267
```

Place `build/server-neoforge.jar` next to the `expedition-neoforge` instance and select that JAR in the hosting panel. The instance contains the NeoForge installer output, the dedicated-server pack, its own `server.properties`, and its own save. The bootstrap runs NeoForge from that instance, using the argument file for the host operating system. Configure the instance to listen on the panel's game port.

The NeoForge launch sets default Java URL connection and read timeouts of 10 and 15 seconds. Mods that use the JVM defaults can fall back to local data when an external request stalls. Explicit JVM properties can override these defaults.

The default `server-bootstrap.jar` launches the adjacent Forge upstream JAR from the hosting working directory. Run `python3 tests/verify.py` to exercise console and shutdown behavior with the fake server.
