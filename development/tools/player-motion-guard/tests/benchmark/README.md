# Monitoring benchmark fixture

This local test harness compares identical, deterministic workloads in separate disposable Forge 47.4.10 runtimes. It never edits or launches an installed client or the online server. Run full Forge processes serially. `--prepare-only` compiles the fixture and prepares directories without starting a JVM server.

The workload uses at least ten ordinary `ServerPlayer` objects registered in the real level and player list. A test-only packet listener discards outgoing packets but retains the real server teleport method. Each real `ServerTickEvent` invokes each player's actual `ServerPlayer.doTick()`, which calls `Player.tick()` and emits Forge player tick callbacks. The fixture asserts the expected player START/END callback counts. It deliberately does not use `FakePlayer.tick()`, which is a no-op, or FakePlayer's no-op teleport override.

Each scenario has its own warmup, followed by a measured fixed number of server ticks. Multiple rounds use the same seed, arena, movement, teleports, equipment changes with 1 KiB test NBT, and genuine game-mode block place/break operations. `steady` measures ordinary activity. `incident` adds the same protected NaN attempts and one intentional 150 ms long tick to each mode; its maximum tick is not an ordinary-activity overhead statistic. The monitoring group additionally asserts `enabled=true`, at least ten tracked player rings, the expected snapshot count, changing equipment/event counters and actual writer progress. Both modes include Spark; baseline explicitly disables its background profiler and monitoring enables the Java engine at 20 ms intervals. The monitoring add-on supplies JFR and the bounded recorder.

Run from the project root with the built monitoring JAR:

```sh
python3 tools/player-motion-guard/tests/benchmark/run_benchmark.py \
  --output /path/to/new-disposable-results \
  --baseline-guard /path/to/protection-only-baseline.jar \
  --guard tools/player-motion-guard/dist/expedition-player-motion-guard-1.1.0.jar \
  --client "/path/to/read-only-client-instance" \
  --shared-mod /path/to/spark-1.10.53-forge.jar \
  --rounds 1 --warmup-ticks 200 --ticks 2400 --scenarios steady \
  --order baseline,monitor,monitor,baseline --require-exports
```

The formal command uses four independent runs, each with a warmup and 120-second steady measurement. This covers Spark's request at approximately 45 seconds and completed attribution/archive window around 105 seconds, plus JFR's periodic exports. `--require-exports` verifies confirmed Spark receipts and source deletion, at least two completed JFR dumps, and real persisted state batches; a requested export alone never passes. The independent ABBA warmups provide repetition even with one measured window per process.

Use `--order baseline,monitor --rounds 2 --warmup-ticks 40 --ticks 100` for a shorter initial acceptance run, then use the formal command for performance conclusions. Run the short `incident` scenario separately; intentional sleeping is not a normal overhead measure. Omit `--baseline-guard` to compare diagnostics enabled/disabled within the same new JAR. With Spark supplied, the difference includes its explicitly enabled background profiler; this is the final combined-monitoring overhead, not an isolated attribution to only the JSON writer or JFR. `--shared-mod` remains available for optional controlled integration comparisons, but no audit/logger mod is part of the final benchmark command.

`--monitor-config` merges an explicitly supplied configuration into the production defaults; only `enabled` differs automatically by mode. `--stall-ms` can test a longer main-thread pause. The default 150 ms exercises long-tick reporting, not the 10-second independent stall watchdog. Runtime directories must not already exist. `--libraries`, `--java` and `--javac` support a complete existing Forge library tree and Java 17 executables. The client input supplies only the three dependency JARs for Radium, Alex's Caves and Citadel and is read-only.

Each window records tick wall/main-thread CPU p50, p95, maximum and sum; process CPU; exact main-thread allocated bytes; approximate live-thread CPU/allocation totals; GC count/time and heap endpoints; actual player callbacks, teleports, equipment changes and block operations; and diagnostic writer/status counters. The parent runner samples OS process disk read/write counters at window markers and reports retained diagnostic file count/bytes separately. It uses `proc_pid_rusage(RUSAGE_INFO_V2)` on macOS and `/proc/PID/io` on Linux. These are OS-accounted I/O, not a promise that every buffered write has reached physical storage at that boundary. Net file size is never presented as write throughput.

Results are written to `comparison.json`, each runtime's `result.json`, `plan.json` with all input hashes, and private console/runtime files. No universal pass threshold is hidden in the tool: review repeated steady-state p95 and process CPU differences, allocations, writer drops/errors, disk growth and whether incident handling remains bounded. Startup, warmup and shutdown are excluded from the tick distributions. Endpoints of rotating files can understate cumulative writes, and all-thread allocation endpoints omit threads that exited during a window.

This is a real Forge tick and player-physics benchmark with a controlled dependency graph, not a ten-network-client or complete-modpack simulation. It does not measure real packet encode/send cost, client chunk rebuilding, Curios/CarryOn behavior without those mods, or full production world generation. A full-modpack compatibility clone, recorder retention/kill tests and online acceptance remain separate checks. All generated worlds, logs, databases and diagnostic files stay under the disposable output directory and must not enter the published repository. The fixture JAR is never a production dependency.

`kill_after_ack.py` runs a separate ten-player trajectory durability check. It reuses this real-tick fixture, warms 200 ticks and measures another 200, then waits for the on-disk contiguous force receipt to cover the final live status sequence with no loss and for a completed JFR receipt. It records those acknowledgements, sends only SIGKILL, and validates every acknowledged JSONL sequence, all ten players' persisted state batches and the actual JFR artifact using the existing `RecordingFile` inspector. Pending data and power loss are outside that guarantee. Run it separately from performance measurements:

```sh
python3 tools/player-motion-guard/tests/benchmark/kill_after_ack.py \
  --output /path/to/new-disposable-trajectory-results \
  --guard tools/player-motion-guard/dist/expedition-player-motion-guard-1.1.0.jar \
  --client "/path/to/read-only-client-instance" \
  --spark /path/to/spark-1.10.53-forge.jar
```
