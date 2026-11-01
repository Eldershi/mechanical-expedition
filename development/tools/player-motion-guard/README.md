# Player motion guard

This optional server-side Forge 1.20.1 add-on rejects unsafe collision queries for `ServerPlayer` instances. It does not change equipment, attributes, other entities or teleport implementations. Installing the JAR on the dedicated server does not require clients to install it.

Three cancellable HEAD injections guard `Entity.setDeltaMovement(Vec3)`, `Entity.move(MoverType, Vec3)` and `Entity.collide(Vec3)`. Mixin application priority is 500: applying after Alex's Caves' priority-1000 mixin places this guard and its cancellation check before the existing AC HEAD callback. The build verifies this order by applying both real mixins to Entity. The double-coordinate setter delegates to the Vec3 setter. The final collision check also covers argument changes inside `move`, including stuck-speed multiplication and edge handling.

A query is rejected if its motion or original/swept bounding box contains a non-finite value, the original box is inverted, the swept box exceeds horizontal coordinates ±30,000,000, its vertical bounds cannot be converted safely to the original integer collision cursor, or its conservative three-dimensional section count reaches 4096. The query bounds include X/Z ±2 blocks plus epsilon and Y −4/+2 blocks plus epsilon, covering both vanilla entity-section lookup and block-collision cursor margins. Section products saturate at 4096 using division before multiplication to avoid overflow. The threshold bounds computational work; it is not a blocks-per-tick speed setting. A long narrow movement can pass while a shorter three-dimensional sweep can exceed the budget. Small movements at very high but safely representable Y coordinates pass; world build height is not a rejection boundary.

Rejection clears the player's velocity through the shadowed field without recursively calling its setter. `move` is cancelled, and `collide` returns zero movement. An already-invalid bounding box is left in place while unsafe movement is blocked; this guard does not invent a recovery position or automatically teleport the player. A valid server teleport uses position/teleport methods rather than collision movement and remains available for recovery.

Warnings include the entry point and mover type when available, entity ID, dimension, attempted/current motion, position, original/swept boxes, section counts, base/attribute step height and a caller stack. They omit player names, IP addresses and authentication data. Warnings are limited to one per player entity every 20 seconds. Normal queries allocate no diagnostic objects and produce no log output.

Run `python3 tools/player-motion-guard/build.py` from the project root. It builds a deterministic JAR under `dist`, tests policy boundaries and applies the real Mixin transformer to the actual Minecraft Entity class, checks the three HEAD guards, confirms double-setter delegation, verifies retained original method instructions and runs ASM verification. A second real transform includes the unmodified Alex's Caves EntityMixin and checks that this guard can cancel before AC's collision callback. Build inputs use the project's existing Forge libraries and the launcher library cache. No installed instance is edited.

The current JAR passes 20 policy boundaries and 18 real Forge FakePlayer assertions with Forge 47.4.10, Alex's Caves 2.0.2, Citadel 2.6.3 and Radium 0.12.4 with its movement collision optimization disabled. The Forge fixture covers all three entry points, invalid original boxes, ordinary/high-speed movement, distant position changes, wall/floor collisions and non-player behavior. Run it in a new disposable directory:

```sh
python3 tools/player-motion-guard/tests/forge/run_motion_probe.py \
  --runtime-root /path/to/new-disposable-runtime \
  --client /path/to/client-instance
```

The client directory supplies only the three dependency JARs and is read-only. `--libraries` selects an existing complete Forge libraries directory; its default is the project's server instance libraries. `--guard`, `--java` and `--javac` override the built JAR and Java 17 executables. The fixture binds to loopback, creates its own flat world and test-only probe mod, and stores its result, logs and generated files entirely under `--runtime-root`. It refuses an existing runtime directory. Keep that generated directory outside published source files; the probe JAR is never a deployment dependency.
