package expedition.motionguard.diagnostics;

import com.google.gson.*;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Stream;

/** Single daemon writer. Producers never wait for disk or an unbounded queue. */
public final class DurableJsonLog implements AutoCloseable {
    public static final int MAX_LINE_BYTES = 32768;
    private final Path root, events, incidents;
    private final DiagnosticsConfig config;
    private final String bootId;
    private final Gson gson;
    private final ArrayBlockingQueue<Entry> queue;
    private final ArrayBlockingQueue<Incident> incidentQueue = new ArrayBlockingQueue<>(2);
    private final Object producerLock = new Object();
    private final AtomicLong accepted = new AtomicLong(), dropped = new AtomicLong(), oversized = new AtomicLong();
    private final AtomicLong forceRequested = new AtomicLong(), droppedIncidents = new AtomicLong();
    private final Thread worker;
    private volatile boolean closing;
    private volatile long processed, written, forced, forceHandled, firstLost, forceCount, writeFailures, lostWrites, markerFailures;
    private volatile long firstUnconfirmedClosedFileSequence, unconfirmedClosedFileRecords;
    private volatile long recoveredTailFiles, recoveredTailBytes, retainedBytes, retainedFiles;
    private volatile long incidentCount, incidentTruncations, previousForced, prunedFiles, prunedBytes;
    private volatile String previousBoot = "", lastError = "", lastForcedFile = "", lastWrittenFile="";
    private FileChannel channel;
    private Path current;
    private long bytes, fileNumber, lastForceNanos;
    private long channelWritten, channelUnconfirmedFirst, channelUnconfirmedRecords;
    private long lastWarningNanos;
    private record Entry(long sequence, byte[] encoded) {}
    public record Incident(String reason, Object context, List<PlayerSnapshot> snapshots) {}

    public DurableJsonLog(Path root, DiagnosticsConfig config, String bootId) throws IOException {
        this.root = root; this.events = root.resolve("events"); this.incidents = root.resolve("incidents");
        this.config = config; this.bootId = bootId;
        this.queue = new ArrayBlockingQueue<>(config.queueCapacity);
        JsonSerializer<Double> doubles = (value, type, context) -> Double.isFinite(value)
                ? new JsonPrimitive(value) : new JsonPrimitive(value.toString());
        JsonSerializer<Float> floats = (value, type, context) -> Float.isFinite(value)
                ? new JsonPrimitive(value) : new JsonPrimitive(value.toString());
        gson = new GsonBuilder().disableHtmlEscaping().registerTypeAdapter(Double.class, doubles)
                .registerTypeAdapter(double.class, doubles).registerTypeAdapter(Float.class, floats)
                .registerTypeAdapter(float.class, floats).create();
        Files.createDirectories(events); Files.createDirectories(incidents);
        recover(); prune(events, config.maxLogFiles, config.totalLogBytes, null);
        prune(incidents, config.maxIncidentFiles, config.maxIncidentBytes, null);
        open();
        worker = new Thread(this::run, "expedition-diagnostics-writer"); worker.setDaemon(true); worker.start();
    }

    public boolean offer(String type, Object pureValues) {
        synchronized (producerLock) {
            if (closing || queue.remainingCapacity() == 0) { dropped.incrementAndGet(); return false; }
            long sequence=accepted.get()+1;
            byte[] encoded=line(Map.of("bootId",bootId,"sequence",sequence,"timeMillis",System.currentTimeMillis(),"type",type,"data",pureValues));
            if(encoded.length>MAX_LINE_BYTES) {oversized.incrementAndGet();return false;}
            accepted.incrementAndGet();queue.add(new Entry(sequence,encoded));
            return true;
        }
    }
    public long requestForce() {
        long target = accepted.get(); forceRequested.accumulateAndGet(target, Math::max);
        // A zero-record request still needs an observable initial marker.
        return target;
    }
    public boolean incident(Incident incident) {
        synchronized(producerLock) {
            if (closing || !incidentQueue.offer(incident)) { droppedIncidents.incrementAndGet(); return false; }
            return true;
        }
    }
    public Map<String,Object> status() {
        Map<String,Object> state = new LinkedHashMap<>();
        state.put("bootId", bootId); state.put("lastAcceptedSequence", accepted.get());
        state.put("lastWrittenSequence", written); state.put("lastForcedSequence", forced);
        state.put("lastProcessedSequence",processed);state.put("lastSuccessfullyWrittenSequence",written);
        state.put("lastForceRequestProcessedSequence",forceHandled);state.put("firstLostSequence",firstLost);
        state.put("firstUnconfirmedClosedFileSequence",firstUnconfirmedClosedFileSequence);
        state.put("lastContiguousForcedSequence",contiguous(forced));
        state.put("lastForcedFile", lastForcedFile); state.put("forceCount", forceCount);
        state.put("queueDepth", queue.size()); state.put("queueCapacity", config.queueCapacity);
        state.put("droppedQueueRecords", dropped.get()); state.put("droppedOversizeRecords", oversized.get());
        state.put("writeFailures", writeFailures); state.put("lostWriteRecords", lostWrites);
        state.put("unconfirmedClosedFileRecords",unconfirmedClosedFileRecords);
        state.put("markerFailures", markerFailures); state.put("lastError", lastError);
        state.put("retainedEventBytes", retainedBytes); state.put("retainedEventFiles", retainedFiles);
        state.put("incidentCount", incidentCount); state.put("droppedIncidents", droppedIncidents.get());
        state.put("truncatedIncidents", incidentTruncations);
        state.put("recoveredIncompleteTailFiles", recoveredTailFiles);
        state.put("recoveredIncompleteTailBytes", recoveredTailBytes);
        state.put("previousBootId", previousBoot); state.put("previousForcedSequence", previousForced);
        state.put("retentionDeletedFiles",prunedFiles); state.put("retentionDeletedBytes",prunedBytes);
        state.put("writerAlive",worker.isAlive());state.put("closing",closing);
        return state;
    }
    private void run() {
        lastForceNanos = System.nanoTime();
        while (!closing || !queue.isEmpty() || !incidentQueue.isEmpty()) {
            try {
                Entry entry = queue.poll(config.flushIntervalMillis, TimeUnit.MILLISECONDS);
                if (entry != null) writeEntry(entry);
                for (int i=0; i<255 && (entry=queue.poll())!=null; i++) writeEntry(entry);
                Incident incident = incidentQueue.poll();
                if (incident != null) { force(); writeIncident(incident); }
                if (System.nanoTime()-lastForceNanos >= TimeUnit.MILLISECONDS.toNanos(config.forceIntervalMillis)
                        || forceRequested.get()>forceHandled && processed>=forceRequested.get()
                        || forceCount==0) force();
            } catch (InterruptedException ignored) {
                // Wake for an explicit flush or incident; do not interrupt FileChannel I/O.
            } catch (Exception problem) { failure(problem); }
        }
        try { force(); if (channel!=null) channel.close(); } catch (Exception problem) { failure(problem); }
    }
    private void writeEntry(Entry entry) {
        try {
            byte[] line=entry.encoded;
            if(channel==null) open();
            if (bytes+line.length>config.eventFileBytes) { force(); channel.close(); open(); prune(events,config.maxLogFiles,config.totalLogBytes,current); }
            write(channel,line); bytes+=line.length; retainedBytes+=line.length; written=entry.sequence;
            channelWritten=entry.sequence;
            if(channelUnconfirmedFirst==0)channelUnconfirmedFirst=entry.sequence;
            channelUnconfirmedRecords++;
            processed=entry.sequence;lastWrittenFile=current.getFileName().toString();
        } catch (Exception problem) {
            // A later channel cannot force this file's previously buffered prefix.
            // Conservatively expose that prefix as unconfirmed before abandoning it.
            if(channelUnconfirmedFirst!=0) {
                if(firstUnconfirmedClosedFileSequence==0 || channelUnconfirmedFirst<firstUnconfirmedClosedFileSequence)
                    firstUnconfirmedClosedFileSequence=channelUnconfirmedFirst;
                unconfirmedClosedFileRecords+=channelUnconfirmedRecords;
                channelUnconfirmedFirst=channelUnconfirmedRecords=0;
            }
            lost(entry.sequence); failure(problem);
            try {if(channel!=null)channel.close();} catch(IOException ignored) {}
            channel=null;
        }
    }
    private void gap(long sequence) {if(firstLost==0 || sequence<firstLost)firstLost=sequence;}
    private void lost(long sequence) {lostWrites++;processed=sequence;gap(sequence);}
    private long contiguous(long candidate) {
        if(firstLost!=0)candidate=Math.min(candidate,firstLost-1);
        if(firstUnconfirmedClosedFileSequence!=0)candidate=Math.min(candidate,firstUnconfirmedClosedFileSequence-1);
        return candidate;
    }
    private void open() throws IOException {
        prune(events,config.maxLogFiles-1,config.totalLogBytes-config.eventFileBytes,null);
        current=events.resolve("events-"+bootId+"-"+(++fileNumber)+".jsonl");
        channel=FileChannel.open(current,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);
        bytes=0;channelWritten=channelUnconfirmedFirst=channelUnconfirmedRecords=0;retainedFiles++;
    }
    private void force() throws IOException {
        if(channel==null)open();
        channel.force(true);
        long confirmed=Math.max(forced,channelWritten);
        String confirmedFile=channelWritten>forced?current.getFileName().toString():lastForcedFile;
        Map<String,Object> marker=new LinkedHashMap<>(status());
        marker.put("lastForcedSequence",confirmed); marker.put("lastForcedFile",confirmedFile);
        marker.put("lastContiguousForcedSequence",contiguous(confirmed));
        marker.put("lastForceRequestProcessedSequence",processed);
        marker.put("forceCount",forceCount+1); marker.put("confirmedAtMillis",System.currentTimeMillis());
        Path temporary=root.resolve("state.json.pending");
        try (FileChannel output=FileChannel.open(temporary,StandardOpenOption.CREATE,StandardOpenOption.TRUNCATE_EXISTING,StandardOpenOption.WRITE)) {
            write(output,line(marker)); output.force(true);
        }
        try { Files.move(temporary,root.resolve("state.json"),StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING); }
        catch(IOException problem) {markerFailures++;throw problem;}
        forceDirectory(root);
        forced=confirmed;forceHandled=processed;lastForcedFile=confirmedFile;
        channelUnconfirmedFirst=channelUnconfirmedRecords=0;
        forceCount++;lastForceNanos=System.nanoTime();
    }
    private void writeIncident(Incident incident) throws IOException {
        long limit=Math.max(MAX_LINE_BYTES,config.maxIncidentBytes/2), size=0;
        prune(incidents,config.maxIncidentFiles-1,config.maxIncidentBytes-limit,null);
        Path path=incidents.resolve("incident-"+bootId+"-"+(++incidentCount)+".jsonl");
        try (FileChannel output=FileChannel.open(path,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE)) {
            Map<String,Object> context=new LinkedHashMap<>();List<?> threads=List.of();
            if(incident.context instanceof Map<?,?> source) {
                for(var entry:source.entrySet()) {
                    if(entry.getKey().equals("threads") && entry.getValue() instanceof List<?> list)threads=list;
                    else context.put(String.valueOf(entry.getKey()),entry.getValue());
                }
            }
            byte[] header=line(Map.of("bootId",bootId,"type","incident","reason",incident.reason,
                    "timeMillis",System.currentTimeMillis(),"context",context,"forcedEventSequence",forced));
            if (header.length>MAX_LINE_BYTES) { header=line(Map.of("bootId",bootId,"reason",incident.reason,"contextTruncated",true)); incidentTruncations++; }
            write(output,header); size+=header.length;
            boolean truncated=false;
            for(Object thread:threads) {
                byte[] row=line(Map.of("type","thread","data",thread));
                if(row.length>MAX_LINE_BYTES || size+row.length+256>limit) {truncated=true;break;}
                write(output,row);size+=row.length;
            }
            for (PlayerSnapshot snapshot:incident.snapshots) {
                byte[] row=line(Map.of("bootId",bootId,"type","recent_player_state","state",snapshot));
                if (size+row.length+256>limit) { truncated=true; break; }
                write(output,row); size+=row.length;
            }
            if (truncated) incidentTruncations++;
            write(output,line(Map.of("type","incident_complete","ringTruncated",truncated)));
            output.force(true);
        }
        forceDirectory(incidents);
        prune(incidents,config.maxIncidentFiles,config.maxIncidentBytes,null);
    }
    private void recover() throws IOException {
        Path marker=root.resolve("state.json");
        if (Files.isRegularFile(marker) && Files.size(marker)<=MAX_LINE_BYTES) {
            try {
                JsonObject old=JsonParser.parseString(Files.readString(marker)).getAsJsonObject();
                previousBoot=old.get("bootId").getAsString(); previousForced=old.get("lastForcedSequence").getAsLong();
            } catch (RuntimeException ignored) { markerFailures++; }
        }
        for (Path directory:List.of(events,incidents)) {
            for (Path path:files(directory)) {
                long length=Files.size(path); if (length==0) continue;
                try (FileChannel input=FileChannel.open(path,StandardOpenOption.READ)) {
                    int tail=(int)Math.min(MAX_LINE_BYTES,length); ByteBuffer buffer=ByteBuffer.allocate(tail);
                    input.position(length-tail); while(buffer.hasRemaining() && input.read(buffer)>0) {}
                    byte[] content=buffer.array();
                    if (content[tail-1]!='\n') {
                        int last=tail-1; while(last>=0 && content[last]!='\n') last--;
                        recoveredTailFiles++; recoveredTailBytes+=tail-last-1;
                    }
                }
            }
        }
    }
    private void prune(Path directory,int countLimit,long byteLimit,Path protectedFile) throws IOException {
        List<Path> files=files(directory);
        files.sort(Comparator.comparingLong(path->{ try{return Files.getLastModifiedTime(path).toMillis();}catch(IOException e){return 0;} }));
        long total=0; for(Path path:files) total+=Files.size(path);
        int count=files.size();
        for(Path path:files) {
            if(count<=countLimit && total<=byteLimit) break;
            if(path.equals(protectedFile)) continue;
            long length=Files.size(path); Files.delete(path); total-=length; count--; prunedFiles++; prunedBytes+=length;
        }
        if(directory.equals(events)) { retainedBytes=total; retainedFiles=count; }
    }
    private List<Path> files(Path directory) throws IOException {
        try(Stream<Path> stream=Files.list(directory)) {
            return new ArrayList<>(stream.filter(path->Files.isRegularFile(path,LinkOption.NOFOLLOW_LINKS)
                    && path.getFileName().toString().matches("(?:events|incident)-[0-9a-f-]+-[0-9]+\\.jsonl")).toList());
        }
    }
    private byte[] line(Object value) { return (gson.toJson(value)+"\n").getBytes(StandardCharsets.UTF_8); }
    private static void write(FileChannel output,byte[] data) throws IOException { ByteBuffer buffer=ByteBuffer.wrap(data); while(buffer.hasRemaining()) output.write(buffer); }
    private static void forceDirectory(Path directory) {
        try(FileChannel handle=FileChannel.open(directory,StandardOpenOption.READ)) { handle.force(true); }
        catch(IOException|UnsupportedOperationException ignored) { /* Data and marker files have already been forced. */ }
    }
    private void failure(Exception problem) {
        writeFailures++;lastError=problem.getClass().getSimpleName();
        long now=System.nanoTime();
        if(lastWarningNanos==0 || now-lastWarningNanos>TimeUnit.SECONDS.toNanos(20)) {
            lastWarningNanos=now;
            System.err.println("[ExpeditionDiagnostics] durable writer failure="+lastError+" failures="+writeFailures+" lostWriteRecords="+lostWrites+"; inspect state/status before assuming persistence.");
        }
    }
    @Override public void close() {
        synchronized(producerLock) {closing=true;}
        try {worker.join(6000);}catch(InterruptedException e){Thread.currentThread().interrupt();}
        if(worker.isAlive()) {
            lastError="shutdown_timeout_with_unconfirmed_work";
            System.err.println("[ExpeditionDiagnostics] writer shutdown timed out; queued="+queue.size()+" incidentQueue="+incidentQueue.size()+" lastForcedSequence="+forced);
        }
    }
}
