# Spark archive circuit breaker tests

Run with Java 17 and Gson 2.10:

```sh
python3 tools/player-motion-guard/tests/spark/run_tests.py --output /path/to/new-output-directory
```

Use `--gson`, `--java`, and `--javac` to supply dependencies outside the existing local Forge libraries. The runner compiles production `SparkArchive.java` with test-only command and mod-presence boundaries. It starts no Minecraft server, socket, JFR recording, or Spark profiler.

The tests control private observation clocks and exercise real local filesystem operations. They verify the 256 MiB source preflight, 512-entry scan limit, refusal to resume over budget, blocking after ambiguous/oversized outputs or archive failure, and successful unique export with 190 MiB of untouched historical source data. Every failed issued cycle must prevent another automatic command. Sparse files provide oversized inputs without writing their full logical size. Runtime files and results belong outside the source tree.
