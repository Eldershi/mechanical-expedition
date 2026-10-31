import java.io.IOException;
import java.io.OutputStream;
import java.lang.management.ManagementFactory;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.locks.ReentrantLock;

/** Small parent process. The unmodified upstream jar launches Forge in a child JVM. */
public final class ExpeditionBootstrap {
    private static final String UPSTREAM = "server-upstream-20261017.jar";
    private static final long STOP_GRACE_MS = boundedLong("expedition.bootstrap.stopGraceMs", 60_000);
    private static final long TERM_GRACE_MS = boundedLong("expedition.bootstrap.termGraceMs", 15_000);

    private static long boundedLong(String property, long defaultValue) {
        String value = System.getProperty(property);
        if (value == null) return defaultValue;
        long parsed = Long.parseLong(value);
        if (parsed < 100 || parsed > 300_000) {
            throw new IllegalArgumentException(property + " must be between 100 and 300000");
        }
        return parsed;
    }

    private static void log(String message) {
        System.err.println("[ExpeditionBootstrap] " + message);
    }

    private static void logCgroupMemory() {
        if (!System.getProperty("os.name").equals("Linux")) return;
        for (String name : List.of("/sys/fs/cgroup/memory.events", "/sys/fs/cgroup/memory.max",
                "/sys/fs/cgroup/memory.current", "/sys/fs/cgroup/memory.peak",
                "/sys/fs/cgroup/memory/memory.failcnt", "/sys/fs/cgroup/memory/memory.oom_control")) {
            Path file = Path.of(name);
            if (!Files.isRegularFile(file)) continue;
            try {
                String value = Files.readString(file, StandardCharsets.UTF_8);
                if (value.length() <= 4096) log(name + "=" + value.strip().replace("\n", "; "));
            } catch (IOException | SecurityException unavailable) {
                log(name + " unavailable");
            }
        }
    }

    public static void main(String[] args) throws Exception {
        Path ownJar = Path.of(ExpeditionBootstrap.class.getProtectionDomain()
                .getCodeSource().getLocation().toURI()).toRealPath();
        Path upstream = ownJar.getParent().resolve(UPSTREAM).toRealPath();
        if (!Files.isRegularFile(upstream) || Files.isSameFile(ownJar, upstream)) {
            throw new IOException("Missing or invalid upstream jar: " + UPSTREAM);
        }
        Path java = Path.of(System.getProperty("java.home"), "bin", "java").toRealPath();
        List<String> command = new ArrayList<>(List.of(java.toString(),
                "-Xms4G", "-Xmx12G", "-XX:+UseG1GC", "-XX:ActiveProcessorCount=6",
                "-XshowSettings:vm"));
        for (String argument : ManagementFactory.getRuntimeMXBean().getInputArguments()) {
            if (!argument.startsWith("-D") || argument.length() <= 2) continue;
            int equals = argument.indexOf('=', 2);
            String key = argument.substring(2, equals < 0 ? argument.length() : equals);
            if (key.equals("expedition.bootstrap") || key.startsWith("expedition.bootstrap.")) continue;
            command.add(argument);
        }
        command.add("-jar");
        command.add(upstream.toString());
        command.addAll(List.of(args));
        ProcessBuilder builder = new ProcessBuilder(command)
                .redirectOutput(ProcessBuilder.Redirect.INHERIT)
                .redirectError(ProcessBuilder.Redirect.INHERIT);
        // Keep the existing working directory, environment, and original application args.
        // Retain explicit -D properties (timezone, language, etc.), never parent -X/agents.
        // In particular, do not pass the parent's -Xmx18G through to the child.
        for (String name : List.of("_JAVA_OPTIONS", "JAVA_TOOL_OPTIONS", "JDK_JAVA_OPTIONS")) {
            if (builder.environment().containsKey(name)) {
                log("Inherited " + name + " is present; verify the child's actual heap below.");
            }
        }
        log("Starting " + UPSTREAM + " with -Xms4G -Xmx12G -XX:+UseG1GC "
                + "-XX:ActiveProcessorCount=6; applicationArgs=" + args.length);
        logCgroupMemory();

        AtomicReference<Process> childRef = new AtomicReference<>();
        AtomicReference<ChildInput> inputRef = new AtomicReference<>();
        AtomicBoolean shuttingDown = new AtomicBoolean();
        Object startupLock = new Object();
        Thread shutdown = new Thread(() -> {
            shuttingDown.set(true);
            Process child;
            ChildInput input;
            synchronized (startupLock) {
                child = childRef.get();
                input = inputRef.get();
            }
            if (child == null || !child.isAlive()) return;
            log("Parent shutdown requested; asking child to save and stop.");
            boolean wroteStop = input != null && input.requestStop();
            if (wroteStop && awaitExit(child, STOP_GRACE_MS)) {
                log("Child exited after stop; exitCode=" + child.exitValue());
                return;
            }
            log("Child still running or console unavailable; sending TERM.");
            child.destroy();
            if (awaitExit(child, TERM_GRACE_MS)) {
                log("Child exited after TERM; exitCode=" + child.exitValue());
                return;
            }
            log("Child exceeded shutdown deadline; sending KILL (save not guaranteed).");
            child.destroyForcibly();
            awaitExit(child, 5_000);
        }, "expedition-bootstrap-shutdown");
        Runtime.getRuntime().addShutdownHook(shutdown);

        Process child;
        ChildInput input;
        synchronized (startupLock) {
            if (shuttingDown.get()) return;
            child = builder.start();
            childRef.set(child);
            input = new ChildInput(child.getOutputStream());
            inputRef.set(input);
        }
        log("parentPid=" + ProcessHandle.current().pid() + "; childPid=" + child.pid());
        Thread console = new Thread(() -> input.forwardSystemInput(), "expedition-bootstrap-stdin");
        console.setDaemon(true);
        console.start();
        int status = child.waitFor();
        input.closeWhenAvailable();
        log("Child finished; exitCode=" + status);
        if (!shuttingDown.get()) {
            try {
                Runtime.getRuntime().removeShutdownHook(shutdown);
            } catch (IllegalStateException alreadyShuttingDown) {
                return;
            }
            System.exit(status);
        }
    }

    private static boolean awaitExit(Process child, long timeoutMs) {
        try {
            return child.waitFor(timeoutMs, TimeUnit.MILLISECONDS);
        } catch (InterruptedException interrupted) {
            Thread.currentThread().interrupt();
            return !child.isAlive();
        }
    }

    private static final class ChildInput {
        private final OutputStream output;
        private final ReentrantLock lock = new ReentrantLock();
        private boolean closed;

        private ChildInput(OutputStream output) {
            this.output = output;
        }

        private void forwardSystemInput() {
            byte[] buffer = new byte[4096];
            try {
                int count;
                while ((count = System.in.read(buffer)) != -1) {
                    lock.lock();
                    try {
                        if (closed) return;
                        output.write(buffer, 0, count);
                        output.flush();
                    } finally {
                        lock.unlock();
                    }
                }
            } catch (IOException ended) {
                // Expected if the child exits while the console is still forwarding.
            } finally {
                closeWhenAvailable();
            }
        }

        private boolean requestStop() {
            AtomicBoolean wrote = new AtomicBoolean();
            CountDownLatch done = new CountDownLatch(1);
            Thread writer = new Thread(() -> {
                boolean locked = false;
                try {
                    locked = lock.tryLock(250, TimeUnit.MILLISECONDS);
                    if (!locked || closed) return;
                    output.write("\nstop\n".getBytes(StandardCharsets.UTF_8));
                    output.flush();
                    wrote.set(true);
                } catch (InterruptedException interrupted) {
                    Thread.currentThread().interrupt();
                } catch (IOException unavailable) {
                    // The child may have closed its console or already exited.
                } finally {
                    if (locked) lock.unlock();
                    done.countDown();
                }
            }, "expedition-bootstrap-stop-writer");
            writer.setDaemon(true);
            writer.start();
            try {
                // A full pipe can also block a new write after its lock is acquired.
                // Bound the whole write, then TERM the child to unblock that writer.
                return done.await(1_000, TimeUnit.MILLISECONDS) && wrote.get();
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                return false;
            }
        }

        private void closeWhenAvailable() {
            if (!lock.tryLock()) return;
            try {
                if (!closed) {
                    closed = true;
                    try { output.close(); } catch (IOException ignored) { }
                }
            } finally {
                lock.unlock();
            }
        }
    }
}
