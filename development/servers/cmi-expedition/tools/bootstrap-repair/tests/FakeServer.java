import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.lang.management.ManagementFactory;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Arrays;
import java.util.Locale;
import java.util.TimeZone;

/** A fake console process: no Minecraft, ports, network, app access, or world files. */
public final class FakeServer {
    private static Path events;

    private static synchronized void event(String value) {
        try {
            Files.writeString(events, value + "\n", StandardCharsets.UTF_8,
                    StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (Exception error) {
            throw new RuntimeException(error);
        }
    }

    public static void main(String[] args) throws Exception {
        events = Path.of("events.txt");
        String mode = args[0];
        event("pid=" + ProcessHandle.current().pid());
        event("cwd=" + Path.of("").toAbsolutePath().normalize());
        event("args=" + Arrays.toString(args));
        event("heapMax=" + Runtime.getRuntime().maxMemory());
        event("processors=" + Runtime.getRuntime().availableProcessors());
        event("timezone=" + TimeZone.getDefault().getID());
        event("language=" + Locale.getDefault().getLanguage());
        event("customProperty=" + System.getProperty("expedition.test.unicode"));
        event("jvm=" + ManagementFactory.getRuntimeMXBean().getInputArguments());
        Runtime.getRuntime().addShutdownHook(new Thread(() -> event("shutdown-hook-saved")));
        System.out.println("FAKE_READY " + ProcessHandle.current().pid());
        System.err.println("FAKE_STDERR");
        System.out.flush();
        System.err.flush();
        if (mode.equals("exit23")) System.exit(23);
        if (mode.equals("ignore-input")) {
            Thread.sleep(300_000);
            return;
        }
        BufferedReader reader = new BufferedReader(new InputStreamReader(System.in, StandardCharsets.UTF_8));
        String line;
        while ((line = reader.readLine()) != null) {
            event("stdin=" + line);
            if (line.equals("stop") && !mode.equals("ignore-stop")) {
                event("console-stop-saved");
                return;
            }
        }
        event("stdin-eof");
    }
}
