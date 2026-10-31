package expedition.ponder;

import com.google.gson.GsonBuilder;
import com.p1nero.iss_ponder.client.ClientPreviewController;
import com.p1nero.iss_ponder.client.PreviewProjection;
import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import net.createmod.ponder.api.registration.StoryBoardEntry;
import net.createmod.ponder.foundation.PonderIndex;
import net.createmod.ponder.foundation.PonderScene;
import net.createmod.ponder.foundation.ui.PonderUI;
import net.minecraft.client.Minecraft;
import net.minecraft.client.Screenshot;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.fml.ModList;
import java.lang.reflect.Field;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/** Disposable integration exercise, installed only in the isolated test copy. */
public final class PonderProbe {
    private record Task(String kind, String key, StoryBoardEntry entry) {}
    private static final List<Task> TASKS = new ArrayList<>();
    private static final List<Map<String,Object>> RESULTS = new ArrayList<>();
    private static final List<String> ERRORS = new ArrayList<>();
    private static final Map<String,Integer> COUNTS = new TreeMap<>();
    private static final Map<String,Integer> SHOTS = new HashMap<>();
    private static int ticks, index, taskTicks, finishedAt = -1;
    private static boolean initialized, done, opened, projected, completed;
    private static float damage, progress;
    private static PonderScene scene;
    private static Map<String,Object> current;
    private static volatile int remainingSessions = -1;
    private static volatile String serverProbeError = "";
    private static final Path OUTPUT = Path.of("kubejs/exported");

    private PonderProbe() {}

    private static class SingleSceneUI extends PonderUI {
        SingleSceneUI(PonderScene scene) { super(List.of(scene)); }
    }

    private static void write(String file, Object value) {
        try {
            Files.createDirectories(OUTPUT);
            Files.writeString(OUTPUT.resolve(file),
                new GsonBuilder().setPrettyPrinting().create().toJson(value) + "\n");
        } catch (Exception error) { throw new RuntimeException(error); }
    }

    private static Object field(Class<?> type, Object owner, String name) throws Exception {
        Field field = type.getDeclaredField(name);
        field.setAccessible(true);
        return field.get(owner);
    }

    private static void initialize() {
        Map<String,StoryBoardEntry> unique = new LinkedHashMap<>();
        StoryBoardEntry create = null, cmi = null;
        for (var registered : PonderIndex.getSceneAccess().getRegisteredEntries()) {
            StoryBoardEntry entry = registered.getValue();
            String namespace = entry.getNamespace();
            COUNTS.merge(namespace, 1, Integer::sum);
            if (namespace.equals("mekanism_ponders") || namespace.equals("quark_ponders")) {
                String key = namespace + "/" + entry.getSchematicLocation() + "/"
                    + entry.getBoard().getClass().getName().split("/")[0];
                unique.putIfAbsent(key, entry);
            }
            if (namespace.equals("create") && create == null) create = entry;
            if (namespace.equals("cmi") && cmi == null) cmi = entry;
        }
        for (String required : List.of("mekanism_ponders", "quark_ponders"))
            if (!COUNTS.containsKey(required)) ERRORS.add("No scenes registered for " + required);
        unique.forEach((key, entry) -> TASKS.add(new Task("scene", key, entry)));
        if (create != null) TASKS.add(new Task("scene", "regression/create", create));
        else ERRORS.add("Missing original Create scenes");
        if (cmi != null) TASKS.add(new Task("scene", "regression/cmi", cmi));
        else ERRORS.add("Missing original CMI scenes");
        for (String item : List.of("mekanism:sps_casing", "quark:chute", "minecraft:piston"))
            TASKS.add(new Task("item", item, null));
        List<String> spells = SpellRegistry.getEnabledSpells().stream()
            .map(spell -> spell.getSpellId()).sorted().toList();
        for (String name : List.of("firebolt", "electrocute", "thunderstorm", "blood_slash", "healing_circle", "recall")) {
            String id = "irons_spellbooks:" + name;
            if (spells.contains(id)) TASKS.add(new Task("spell", id, null));
            else ERRORS.add("Required spell absent: " + id);
        }
        Map<String,String> versions = new TreeMap<>();
        for (String id : List.of("create", "ponder", "flywheel", "iss_ponder", "mekanism_ponders", "quark_ponders"))
            versions.put(id, ModList.get().getModContainerById(id).orElseThrow().getModInfo().getVersion().toString());
        write("ponder-compat-inventory.json", Map.of("registrations", COUNTS, "loadedVersions",versions,
            "uniqueAddedScenes", unique.size(), "enabledSpells", spells,
            "tasks", TASKS.stream().map(t -> Map.of("kind",t.kind(),"key",t.key(),
                "component",t.entry()==null?"":t.entry().getComponent().toString())).toList()));
        initialized = true;
    }

    private static void screenshot(Minecraft client, String name) {
        Screenshot.m_92295_(client.f_91069_, name + ".png", client.m_91385_(), ignored -> {});
    }

    private static void start(Task task, Minecraft client) {
        current = new LinkedHashMap<>();
        current.put("kind", task.kind()); current.put("key", task.key());
        current.put("startedAtMs", System.currentTimeMillis());
        opened = projected = completed = false; damage = progress = 0;
        if (!task.kind().equals("spell")) {
            PonderUI ui;
            if (task.kind().equals("scene")) {
                var scenes = PonderIndex.getSceneAccess().compile(List.of(task.entry()));
                if (scenes.size() != 1) throw new IllegalStateException("Expected one compiled storyboard");
                scene = scenes.get(0);
                ui = new SingleSceneUI(scene);
            } else {
                ui = PonderUI.of(new ResourceLocation(task.key()));
                if (ui == null) throw new IllegalStateException("No normal item Ponder entry");
                scene = ui.getActiveScene();
            }
            scene.setNextUpEnabled(false);
            current.put("namespace", scene.getNamespace());
            current.put("component", task.entry()==null?task.key():task.entry().getComponent().toString());
            current.put("sceneId", String.valueOf(scene.getId()));
            current.put("title", scene.getTitle());
            current.put("totalTicks", scene.getTotalTime());
            current.put("bounds", String.valueOf(scene.getBounds()));
            client.m_91152_(ui);
        } else {
            ClientPreviewController.request(new ResourceLocation(task.key()), 1);
        }
    }

    private static boolean exerciseScene(Task task, Minecraft client) {
        if (!(client.f_91080_ instanceof PonderUI))
            throw new IllegalStateException("Ponder scene screen did not remain open");
        if (taskTicks == 20) scene.seekToTime(scene.getTotalTime() / 2);
        if (taskTicks == 32) {
            int count = SHOTS.merge(scene.getNamespace(),1,Integer::sum);
            if (count <= 2) screenshot(client, "ponder-" + scene.getNamespace() + "-" + count);
        }
        if (taskTicks == 40) scene.seekToTime(Math.max(0,scene.getTotalTime()-1));
        if (taskTicks < 55) return false;
        current.put("finalTick", scene.getCurrentTime());
        current.put("finished", scene.isFinished());
        current.put("passed", scene.getTotalTime() > 0 && scene.getCurrentTime() >= scene.getTotalTime()-1);
        return true;
    }

    private static boolean exerciseSpell(Task task, Minecraft client) throws Exception {
        Screen screen = client.f_91080_;
        if (screen != null && screen.getClass().getName().endsWith(".SpellPreviewScreen")) {
            opened = true;
            projected |= PreviewProjection.isActive();
            damage = Math.max(damage, PreviewProjection.observedDamage());
            progress = Math.max(progress, PreviewProjection.castProgress());
            completed |= (Boolean)field(screen.getClass(),screen,"previewComplete");
            boolean allowed = (Boolean)field(screen.getClass(),screen,"simulationAllowed");
            current.put("simulationAllowed",allowed);
            if (taskTicks == 95) screenshot(client, "spell-" + task.key().split(":")[1]);
            if (!allowed && taskTicks >= 120) return finishSpell(task);
        }
        if (taskTicks >= 140 && completed || taskTicks >= 420) return finishSpell(task);
        return false;
    }

    private static boolean finishSpell(Task task) {
        current.put("screenOpened", opened); current.put("projectionActive", projected);
        current.put("previewCompleted", completed); current.put("maxObservedDamage", damage);
        current.put("maxCastProgress", progress);
        current.put("status", ClientPreviewController.getStatus().getString());
        boolean info = Boolean.FALSE.equals(current.get("simulationAllowed"));
        current.put("passed", opened && (info || projected && completed));
        return true;
    }

    private static void snapshotSessions(Minecraft client) {
        var server = client.m_91092_();
        server.execute(() -> {
            try {
                Class<?> manager = Class.forName("com.p1nero.iss_ponder.server.PreviewSessionManager");
                Map<?,?> sessions = (Map<?,?>)field(manager,null,"SESSIONS");
                remainingSessions = sessions.size();
            } catch (Exception error) { serverProbeError = error.toString(); }
        });
    }

    public static void tick() {
        Minecraft client = Minecraft.m_91087_();
        if (done || client.f_91073_ == null || client.f_91074_ == null || client.m_91092_() == null) return;
        if (++ticks < 160) return;
        try {
            if (!initialized) initialize();
            if (index >= TASKS.size()) {
                if (finishedAt < 0) {
                    client.m_91152_(null); finishedAt = ticks;
                }
                if (ticks - finishedAt == 60) snapshotSessions(client);
                if (ticks - finishedAt < 100) return;
                if (remainingSessions != 0) ERRORS.add("Preview sessions remaining after close: " + remainingSessions);
                if (!serverProbeError.isEmpty()) ERRORS.add(serverProbeError);
                boolean passed = ERRORS.isEmpty() && RESULTS.stream().allMatch(r -> Boolean.TRUE.equals(r.get("passed")));
                write("ponder-compat-result.json", Map.of("passed",passed,"results",RESULTS,
                    "errors",ERRORS,"registrations",COUNTS,"sessionsAfterClose",remainingSessions,
                    "scope","Full scene compilation, rendered beginning/middle/end and complete instruction seek; six spell previews in a local integrated server; no dedicated-server test"));
                done = true;
                client.m_91394_();
                return;
            }
            Task task = TASKS.get(index);
            if (taskTicks == 0) start(task,client);
            taskTicks++;
            boolean finished = task.kind().equals("spell") ? exerciseSpell(task,client) : exerciseScene(task,client);
            if (finished) {
                current.put("elapsedTicks",taskTicks);
                RESULTS.add(current);
                client.m_91152_(null); scene = null;
                index++; taskTicks = 0;
            }
            if (ticks % 20 == 0) write("ponder-compat-status.json",Map.of(
                "index",index,"total",TASKS.size(),"current",task.key(),"taskTicks",taskTicks,
                "results",RESULTS,"errors",ERRORS));
        } catch (Throwable error) {
            error.printStackTrace();
            ERRORS.add((index<TASKS.size()?TASKS.get(index).key():"setup") + ": " + error);
            if (current != null) {current.put("passed",false);current.put("error",error.toString());RESULTS.add(current);}
            client.m_91152_(null); scene = null; index++; taskTicks = 0;
            write("ponder-compat-status.json",Map.of("index",index,"total",TASKS.size(),"results",RESULTS,"errors",ERRORS));
        }
    }
}
