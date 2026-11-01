package expedition.motionguard.diagnostics;

import expedition.motionguard.MotionPolicy;
import java.lang.management.*;
import java.nio.file.Path;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;

/** Main-thread capture of pure values; independent watchdog and bounded disk writer. */
public final class DiagnosticsService implements AutoCloseable {
    private static volatile DiagnosticsService current;
    private final DiagnosticsConfig config;
    private final String bootId=UUID.randomUUID().toString();
    private final Path root=Path.of("expedition-diagnostics").toAbsolutePath();
    private final LinkedHashMap<String,History> players=new LinkedHashMap<>(16,.75f,true);
    private final AtomicLong ticks=new AtomicLong(), snapshots=new AtomicLong(), equipmentChanges=new AtomicLong();
    private final AtomicLong events=new AtomicLong(), anomalies=new AtomicLong(), captureErrors=new AtomicLong();
    private final AtomicLong watchdogIncidents=new AtomicLong(), historyEvictions=new AtomicLong();
    private final AtomicLong lastCaptureNanos=new AtomicLong(), suppressedIncidentCaptures=new AtomicLong();
    private final AtomicLong droppedStateSamples=new AtomicLong();
    private volatile long heartbeatNanos=System.nanoTime(), mainThreadId, lastIncidentNanos;
    private volatile boolean stopping;
    private volatile String startupError="";
    private DurableJsonLog writer;
    private EquipmentCapture equipment;
    private JfrRecorder jfr;
    private SparkArchive spark;
    private ScheduledExecutorService watchdog;
    private static final class History {
        final BoundedRing<PlayerSnapshot> ring;
        final List<PlayerSnapshot> pendingStates=new ArrayList<>(10);
        volatile PlayerSnapshot last;
        volatile Map<String,Object> equipment=Map.of();
        long version, lastEquipmentTick=Long.MIN_VALUE, lastPersistTick=Long.MIN_VALUE, lastIdentityTick=Long.MIN_VALUE;
        long firstAnomalyNanos, anomalyCount;
        History(int capacity) { ring=new BoundedRing<>(capacity); }
    }

    public static DiagnosticsService get() { return current; }
    public static DiagnosticsService start() {
        DiagnosticsService service=new DiagnosticsService(DiagnosticsConfig.load(Path.of("config/expedition-diagnostics.json")));
        current=service; return service;
    }
    private DiagnosticsService(DiagnosticsConfig config) {
        this.config=config;
        if(!config.enabled) return;
        try {
            writer=new DurableJsonLog(root,config,bootId); equipment=new EquipmentCapture();
            writer.offer("boot",Map.of("schemaVersion",1,"guardVersion","1.1.0","configuration",config));
            if(config.jfrEnabled) { jfr=new JfrRecorder(root.resolve("jfr")); jfr.start(); }
            if(config.sparkExportEnabled)spark=new SparkArchive(root.resolve("spark"));
            if(config.watchdogEnabled) {
                watchdog=Executors.newSingleThreadScheduledExecutor(task->{Thread thread=new Thread(task,"expedition-diagnostics-watchdog");thread.setDaemon(true);return thread;});
                watchdog.scheduleWithFixedDelay(this::checkProgress,1,1,TimeUnit.SECONDS);
            }
        } catch(Exception|LinkageError problem) { startupError=problem.getClass().getSimpleName(); }
    }
    public void serverTick(net.minecraft.server.MinecraftServer server) {
        if(!config.enabled) return;
        mainThreadId=Thread.currentThread().getId(); heartbeatNanos=System.nanoTime(); ticks.incrementAndGet();
        if(spark!=null)spark.serverTick(server);
    }
    public void playerTick(ServerPlayer player) {
        if(!active()) return;
        try {
            long tick=ticks.get();
            if(tick%config.stateSampleEveryTicks!=0) return;
            History history=history(player);
            if(history.lastIdentityTick==Long.MIN_VALUE || tick-history.lastIdentityTick>=6000) {identity(player);history.lastIdentityTick=tick;}
            if(history.lastEquipmentTick==Long.MIN_VALUE || tick-history.lastEquipmentTick>=config.equipmentCheckEveryTicks)
                captureEquipment(player,history,tick,false);
            PlayerSnapshot state=snapshot(player,history,tick);
            PlayerSnapshot previous=history.last;
            history.ring.add(state); history.last=state; snapshots.incrementAndGet();
            history.pendingStates.add(state);
            if(previous!=null && (state.dimension().equals(previous.dimension()) && distanceSquared(state,previous)>1024.0))
                offer("position_jump_observed",Map.of("before",previous,"after",state));
            if(history.pendingStates.size()>=10 || history.lastPersistTick==Long.MIN_VALUE
                    || tick-history.lastPersistTick>=config.statePersistEveryTicks)flushStates(history);
        } catch(RuntimeException|LinkageError problem) { captureErrors.incrementAndGet(); }
    }
    public void playerEvent(String kind,ServerPlayer player,Map<String,Object> details) {
        if(!active()) return;
        try {
            History history=history(player); captureEquipment(player,history,ticks.get(),true);
            if(kind.equals("player_login"))identity(player);
            if(kind.equals("player_logout"))flushStates(history);
            PlayerSnapshot state=snapshot(player,history,ticks.get()); history.ring.add(state);history.last=state;
            offer(kind,Map.of("state",state,"details",details));
        } catch(RuntimeException|LinkageError problem) { captureErrors.incrementAndGet(); }
    }
    public void playerAction(String kind,ServerPlayer player,Map<String,Object> details,boolean captureCarry) {
        if(!active())return;
        try {
            History history=history(player);
            if(history.lastEquipmentTick==Long.MIN_VALUE)captureEquipment(player,history,ticks.get(),false);
            PlayerSnapshot state=snapshot(player,history,ticks.get());
            Map<String,Object> values=new LinkedHashMap<>(details);
            if(captureCarry)values.put("carryOnAtEvent",equipment.captureCarry(player));
            offer(kind,Map.of("state",state,"details",Collections.unmodifiableMap(values)));
        } catch(RuntimeException|LinkageError problem){captureErrors.incrementAndGet();}
    }
    public static void teleport(ServerPlayer player,double x,double y,double z,float yaw,float pitch,Object relativeFlags) {
        DiagnosticsService service=current;
        if(service!=null) service.playerEvent("teleport_request",player,
                Map.of("targetX",x,"targetY",y,"targetZ",z,"yaw",yaw,"pitch",pitch,
                        "relativeFlags",String.valueOf(relativeFlags),"caller",callerStack(24)));
    }
    public static void unsafe(ServerPlayer player,String source,Vec3 motion,MotionPolicy.Rejection rejection) {
        DiagnosticsService service=current;
        if(service==null || !service.active()) return;
        service.anomalies.incrementAndGet();
        try {
            History history=service.history(player); history.anomalyCount++;
            long now=System.nanoTime();
            if(history.firstAnomalyNanos!=0 && now-history.firstAnomalyNanos<TimeUnit.SECONDS.toNanos(20)) return;
            history.firstAnomalyNanos=now;
            service.captureEquipment(player,history,service.ticks.get(),true);
            Map<String,Object> data=new LinkedHashMap<>();
            data.put("source",source); data.put("playerId",player.m_20148_().toString());
            data.put("anomalyCount",history.anomalyCount); data.put("motion",new double[]{motion.f_82479_,motion.f_82480_,motion.f_82481_});
            data.put("rejection",rejection); data.put("state",service.snapshot(player,history,service.ticks.get()));
            data.put("equipmentVersion",history.version);data.put("equipmentCapturedTick",history.lastEquipmentTick);
            data.put("caller",callerStack(48));
            service.offer("unsafe_motion",Collections.unmodifiableMap(data));
            service.incident("unsafe_motion/"+source,Map.of("playerId",player.m_20148_().toString(),"anomalyCount",history.anomalyCount));
        } catch(RuntimeException|LinkageError problem) { service.captureErrors.incrementAndGet(); }
    }
    private History history(ServerPlayer player) {
        String id=player.m_20148_().toString();
        synchronized(players) {
            History history=players.get(id);
            if(history==null) {
                if(players.size()>=config.maxTrackedPlayers) { String old=players.keySet().iterator().next();flushStates(players.get(old));players.remove(old);historyEvictions.incrementAndGet(); }
                history=new History(config.ringSamplesPerPlayer); players.put(id,history);identity(player);history.lastIdentityTick=ticks.get();
            }
            return history;
        }
    }
    private void flushStates(History history) {
        if(history.pendingStates.isEmpty())return;
        List<PlayerSnapshot> batch=List.copyOf(history.pendingStates);
        if(!offer("state_batch",Map.of("playerId",batch.get(0).playerId(),"firstTick",batch.get(0).tick(),
                "lastTick",batch.get(batch.size()-1).tick(),"anomalyCount",history.anomalyCount,"states",batch)))droppedStateSamples.addAndGet(batch.size());
        history.pendingStates.clear();history.lastPersistTick=ticks.get();
    }
    private void identity(ServerPlayer player) {
        offer("player_identity",Map.of("playerId",player.m_20148_().toString(),"playerName",player.m_36316_().getName(),
                "entityId",player.m_19879_(),"dimension",player.m_9236_().m_46472_().m_135782_().toString(),"tick",ticks.get()));
    }
    private void captureEquipment(ServerPlayer player,History history,long tick,boolean keyEvent) {
        Map<String,Object> captured=equipment.capture(player); history.lastEquipmentTick=tick;
        if(!captured.equals(history.equipment)) {
            history.equipment=captured; history.version++; equipmentChanges.incrementAndGet();
            offer("equipment_changed",Map.of("playerId",player.m_20148_().toString(),"equipmentVersion",history.version,"capturedTick",tick,"snapshot",captured));
        } else if(keyEvent) {
            offer("equipment_at_event",Map.of("playerId",player.m_20148_().toString(),"equipmentVersion",history.version,"capturedTick",tick,"snapshot",captured));
        }
    }
    private PlayerSnapshot snapshot(ServerPlayer player,History history,long tick) {
        AABB box=player.m_20191_(); Vec3 motion=player.m_20184_();
        int flags=(player.m_20096_()?1:0)|(player.m_21255_()?2:0)|(player.m_20142_()?4:0)
                |(player.m_20162_()?8:0)|(player.m_20072_()?16:0)|(player.m_20159_()?32:0)
                |(player.m_6084_()?64:0)|(player.m_6117_()?128:0);
        return new PlayerSnapshot(tick,System.currentTimeMillis(),player.m_20148_().toString(),player.m_19879_(),
                player.m_9236_().m_46472_().m_135782_().toString(),player.m_20185_(),player.m_20186_(),player.m_20189_(),
                motion.f_82479_,motion.f_82480_,motion.f_82481_,box.f_82288_,box.f_82289_,box.f_82290_,
                box.f_82291_,box.f_82292_,box.f_82293_,player.m_146908_(),player.m_146909_(),player.m_20089_().name(),flags,player.f_19789_,history.version,history.lastEquipmentTick);
    }
    private static double distanceSquared(PlayerSnapshot first,PlayerSnapshot second) {
        double x=first.x()-second.x(),y=first.y()-second.y(),z=first.z()-second.z(); return x*x+y*y+z*z;
    }
    private boolean active() { return config.enabled && writer!=null; }
    private boolean offer(String type,Object data) { boolean accepted=writer.offer(type,data);if(accepted)events.incrementAndGet();return accepted; }
    private void checkProgress() {
        if(stopping || mainThreadId==0 || !active()) return;
        long now=System.nanoTime();
        if(now-heartbeatNanos<TimeUnit.MILLISECONDS.toNanos(config.watchdogStallMillis)
                || lastIncidentNanos!=0 && now-lastIncidentNanos<TimeUnit.MILLISECONDS.toNanos(config.watchdogRepeatMillis)) return;
        lastIncidentNanos=now;watchdogIncidents.incrementAndGet();
        try { incident("main_thread_stall",Map.of("stalledMillis",TimeUnit.NANOSECONDS.toMillis(now-heartbeatNanos),"mainThreadId",mainThreadId,"tick",ticks.get())); }
        catch(RuntimeException problem) { captureErrors.incrementAndGet(); }
    }
    public boolean incident(String reason,Map<String,Object> details) {
        if(!active()) return false;
        long now=System.nanoTime(),previous=lastCaptureNanos.get();
        if(previous!=0 && now-previous<TimeUnit.SECONDS.toNanos(10) || !lastCaptureNanos.compareAndSet(previous,now)) {
            suppressedIncidentCaptures.incrementAndGet();return false;
        }
        Map<String,Object> context=new LinkedHashMap<>(details);
        context.putAll(threadSnapshot(false,mainThreadId)); context.put("tick",ticks.get()); context.put("anomalyCount",anomalies.get());
        context.put("ringOrder","affected_player_first; each_player_newest_first");
        List<PlayerSnapshot> recent=new ArrayList<>();
        synchronized(players) {
            Object affected=details.get("playerId");History first=affected instanceof String id?players.get(id):null;
            List<History> ordered=new ArrayList<>();if(first!=null)ordered.add(first);
            for(History history:players.values())if(history!=first)ordered.add(history);
            for(History history:ordered) {List<PlayerSnapshot> states=new ArrayList<>(history.ring.snapshot());Collections.reverse(states);recent.addAll(states);}
        }
        offer("incident_requested",Map.of("reason",reason,"tick",ticks.get(),"recentSnapshots",recent.size()));
        boolean accepted=writer.incident(new DurableJsonLog.Incident(reason,Collections.unmodifiableMap(context),List.copyOf(recent)));
        if(jfr!=null) jfr.requestIncident(reason);
        return accepted;
    }
    public void shutdownSnapshot(String phase) {
        stopping=true;
        if(!active()) return;
        synchronized(players){for(History history:players.values())flushStates(history);}
        Map<String,Object> context=threadSnapshot(true,mainThreadId);
        offer(phase,Map.of("nonDaemonCount",context.get("selectedThreadCount"),"tick",ticks.get()));
        writer.incident(new DurableJsonLog.Incident(phase,context,List.of()));
        writer.requestForce();
    }
    public long requestForce() { return writer==null?0:writer.requestForce(); }
    public void pauseSpark(int minutes) {if(spark!=null)spark.pauseForMinutes(minutes);}
    public Map<String,Object> status() {
        Map<String,Object> state=new LinkedHashMap<>();
        state.put("enabled",config.enabled); state.put("bootId",bootId);state.put("tick",ticks.get());
        synchronized(players) { state.put("trackedPlayers",players.size()); }
        state.put("totalSnapshots",snapshots.get());state.put("equipmentChanges",equipmentChanges.get());
        state.put("eventCount",events.get());state.put("anomalyCount",anomalies.get());
        state.put("watchdogIncidents",watchdogIncidents.get());state.put("captureErrors",captureErrors.get());
        state.put("suppressedIncidentCaptures",suppressedIncidentCaptures.get());
        state.put("droppedStateSamples",droppedStateSamples.get());
        state.put("historyEvictions",historyEvictions.get());state.put("integrationErrors",equipment==null?0:equipment.errors.get());
        state.put("configurationError",config.configurationError);state.put("startupError",startupError);
        state.put("captureReady",active()&&startupError.isEmpty());
        state.put("writer",writer==null?Map.of():writer.status());state.put("jfr",jfr==null?Map.of():jfr.status());
        state.put("spark",spark==null?Map.of():spark.status());
        return state;
    }
    private static List<String> callerStack(int limit) {
        StackTraceElement[] stack=Thread.currentThread().getStackTrace();List<String> result=new ArrayList<>();
        for(int i=2;i<Math.min(stack.length,limit+2);i++) { String text=stack[i].toString();result.add(text.length()>384?text.substring(0,384):text); }
        return List.copyOf(result);
    }
    private static Map<String,Object> threadSnapshot(boolean nonDaemonOnly,long preferredThread) {
        ThreadMXBean bean=ManagementFactory.getThreadMXBean();long[] all=bean.getAllThreadIds();
        long[] scanned=Arrays.copyOf(all,Math.min(all.length,4096));
        ThreadInfo[] shallow=bean.getThreadInfo(scanned,0);List<Long> selected=new ArrayList<>();
        int matching=0;
        ThreadInfo preferred=preferredThread>0?bean.getThreadInfo(preferredThread,0):null;
        if(preferred!=null && (!nonDaemonOnly || !preferred.isDaemon()))selected.add(preferredThread);
        for(ThreadInfo info:shallow) if(info!=null && (!nonDaemonOnly || !info.isDaemon())) {
            matching++;if(selected.size()<128 && info.getThreadId()!=preferredThread) selected.add(info.getThreadId());
        }
        long[] ids=selected.stream().mapToLong(Long::longValue).toArray(); List<Object> descriptions=new ArrayList<>();
        long truncatedFrames=0;
        for(ThreadInfo info:bean.getThreadInfo(ids,65)) if(info!=null) {
            StackTraceElement[] stack=info.getStackTrace();List<String> frames=new ArrayList<>();
            for(int i=0;i<Math.min(64,stack.length);i++) {String text=stack[i].toString();frames.add(text.length()>384?text.substring(0,384):text);}
            if(stack.length>64) truncatedFrames++;
            String name=info.getThreadName(); if(name.length()>192)name=name.substring(0,192);
            descriptions.add(Map.of("id",info.getThreadId(),"name",name,"state",info.getThreadState().name(),"daemon",info.isDaemon(),"stack",List.copyOf(frames)));
        }
        return Map.of("threads",List.copyOf(descriptions),"selectedThreadCount",descriptions.size(),
                "threadsOutsideScanBudget",Math.max(0,all.length-scanned.length),"matchingThreadsTruncated",Math.max(0,matching-128),"stacksTruncated",truncatedFrames);
    }
    @Override public void close() {
        stopping=true;if(watchdog!=null)watchdog.shutdown();
        if(spark!=null)spark.close();
        if(jfr!=null)jfr.close();if(writer!=null)writer.close();
    }
}
