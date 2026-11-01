import expedition.motionguard.diagnostics.JfrRecorder;
import java.nio.file.Path;
import java.util.Map;
import jdk.jfr.Event;
import jdk.jfr.Name;
import jdk.jfr.consumer.RecordingFile;

/** Standalone process fixture, including a real SIGKILL test driven by Python. */
public final class JfrDurabilityProbe {
    @Name("minecraft.ServerTickTime")
    static class TickEvent extends Event { float averageTickDuration = 0.002f; }

    public static void main(String[] args) throws Exception {
        if (args[0].equals("inspect")) {
            int ticks = 0, total = 0;
            try (RecordingFile recording = new RecordingFile(Path.of(args[1]))) {
                while (recording.hasMoreEvents()) {
                    var event = recording.readEvent();
                    total++;
                    if (event.getEventType().getName().equals("minecraft.ServerTickTime")) ticks++;
                }
            }
            if (ticks < 1 || total < 2) throw new AssertionError("Missing persisted events: " + ticks + "/" + total);
            System.out.println("JFR_DURABILITY_VALID ticks=" + ticks + " events=" + total);
            return;
        }
        JfrRecorder recorder = new JfrRecorder(Path.of(args[1]));
        recorder.start();
        if (args[0].equals("failures")) {
            long waitUntil = System.nanoTime()+20_000_000_000L;
            while (((Number)recorder.status().get("dumpCount")).longValue()<1 && System.nanoTime()<waitUntil) {
                new TickEvent().commit(); Thread.sleep(10);
            }
            String confirmed = (String)recorder.status().get("lastCompletedDump");
            if (confirmed.isEmpty()) throw new AssertionError("No initial forced snapshot");
            java.nio.file.Files.createDirectory(Path.of(args[1]).resolve("last-completed.json.partial"));
            var dump = JfrRecorder.class.getDeclaredMethod("dump",String.class);
            dump.setAccessible(true);
            for (int i=0;i<14;i++) { new TickEvent().commit(); dump.invoke(recorder,"failure"); }
            Map<String,Object> state = recorder.status();
            if (((Number)state.get("archiveFiles")).longValue()>8
                    || ((Number)state.get("archiveBytes")).longValue()>768L*1024*1024
                    || !confirmed.equals(state.get("lastCompletedDump"))
                    || !java.nio.file.Files.isRegularFile(Path.of(args[1]).resolve(confirmed)))
                throw new AssertionError(state);
            try (var files = java.nio.file.Files.list(Path.of(args[1]))) {
                if (files.anyMatch(path -> path.toString().endsWith(".jfr.partial")))
                    throw new AssertionError("Failed export left a partial snapshot");
            }
            recorder.close();
            Thread.sleep(50);
            if (Boolean.TRUE.equals(recorder.status().get("enabled"))) throw new AssertionError("Closed recorder enabled");
            JfrRecorder restarted = new JfrRecorder(Path.of(args[1]));
            restarted.start();
            long recoveredUntil = System.nanoTime()+5_000_000_000L;
            while (!Boolean.TRUE.equals(restarted.status().get("recording")) && System.nanoTime()<recoveredUntil) Thread.sleep(10);
            if (!confirmed.equals(restarted.status().get("lastCompletedDump"))
                    || !Boolean.TRUE.equals(restarted.status().get("recoveredPreviousReceipt"))
                    || !java.nio.file.Files.isRegularFile(Path.of(args[1]).resolve(confirmed)))
                throw new AssertionError("Previous receipt target lost during restart: "+restarted.status());
            restarted.close();
            System.out.println("JFR_FAILURE_RETENTION_VALID errors="+state.get("errors")+" files="+state.get("archiveFiles"));
            return;
        }
        boolean acknowledged = false;
        long deadline = System.nanoTime() + 30_000_000_000L;
        while (System.nanoTime() < deadline) {
            new TickEvent().commit();
            Map<String, Object> status = recorder.status();
            if (!acknowledged && ((Number) status.get("dumpCount")).longValue() >= 1) {
                if (!Boolean.TRUE.equals(status.get("recording"))) throw new AssertionError(status);
                System.out.println("JFR_DURABILITY_ACK " + status.get("lastCompletedDump"));
                System.out.flush();
                acknowledged = true;
            }
            Thread.sleep(10);
        }
        throw new AssertionError("Driver did not kill this fixture after acknowledgement");
    }
}
