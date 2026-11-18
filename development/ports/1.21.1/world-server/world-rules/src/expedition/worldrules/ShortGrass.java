package expedition.worldrules;

import java.util.Collections;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.Semaphore;
import java.util.concurrent.atomic.AtomicBoolean;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.ImposterProtoChunk;
import net.minecraft.world.level.chunk.LevelChunk;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.level.ChunkDataEvent;
import net.neoforged.neoforge.event.level.ChunkEvent;
import net.neoforged.neoforge.event.level.block.CropGrowEvent;
import net.neoforged.neoforge.event.server.ServerStoppedEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import org.slf4j.LoggerFactory;

final class ShortGrass {
    private static final String MARKER = "expedition_short_grass";
    private static final int VERSION = 1;
    private static final int MAX_PENDING = 4096;
    private static final ResourceLocation HEAD = ResourceLocation.parse("biomesoplenty:high_grass");
    private static final ResourceLocation PLANT = ResourceLocation.parse("biomesoplenty:high_grass_plant");

    private final Map<LevelChunk, Integer> versions = Collections.synchronizedMap(new WeakHashMap<>());
    private final Set<Key> pending = ConcurrentHashMap.newKeySet();
    private final Semaphore capacity = new Semaphore(MAX_PENDING);
    private final ConcurrentLinkedQueue<Job> jobs = new ConcurrentLinkedQueue<>();
    private final AtomicBoolean warned = new AtomicBoolean();
    private Job current;
    private Block head;
    private Block plant;

    void register() {
        NeoForge.EVENT_BUS.addListener(this::readVersion);
        NeoForge.EVENT_BUS.addListener(this::writeVersion);
        NeoForge.EVENT_BUS.addListener(this::queueChunk);
        NeoForge.EVENT_BUS.addListener(this::stopGrowth);
        NeoForge.EVENT_BUS.addListener(this::tick);
        NeoForge.EVENT_BUS.addListener(this::clear);
    }

    private LevelChunk levelChunk(ChunkAccess chunk) {
        if (chunk instanceof ImposterProtoChunk imposter) {
            return imposter.getWrapped();
        }
        return chunk instanceof LevelChunk loaded ? loaded : null;
    }

    private void readVersion(ChunkDataEvent.Load event) {
        var chunk = levelChunk(event.getChunk());
        if (chunk != null) {
            versions.put(chunk, event.getData().getInt(MARKER));
        }
    }

    private void writeVersion(ChunkDataEvent.Save event) {
        var chunk = levelChunk(event.getChunk());
        if (chunk != null && versions.getOrDefault(chunk, 0) >= VERSION) {
            event.getData().putInt(MARKER, VERSION);
        }
    }

    private void queueChunk(ChunkEvent.Load event) {
        if (!(event.getLevel() instanceof ServerLevel level) || !(event.getChunk() instanceof LevelChunk chunk)
                || versions.getOrDefault(chunk, 0) >= VERSION) {
            return;
        }
        var key = new Key(level, chunk.getPos());
        if (!capacity.tryAcquire()) {
            if (warned.compareAndSet(false, true)) {
                LoggerFactory.getLogger(ShortGrass.class).warn("High grass queue full. Deferred chunks retry on load.");
            }
            return;
        }
        if (pending.add(key)) {
            jobs.add(new Job(key));
        } else {
            capacity.release();
        }
    }

    private void stopGrowth(CropGrowEvent.Pre event) {
        if (event.getLevel().getBlockState(event.getPos().below()).is(BuiltInRegistries.BLOCK.get(HEAD))) {
            event.setResult(CropGrowEvent.Pre.Result.DO_NOT_GROW);
        }
    }

    private boolean isHighGrass(BlockState state) {
        return state.is(head) || state.is(plant);
    }

    private void tick(ServerTickEvent.Post ignored) {
        if (head == null) {
            head = BuiltInRegistries.BLOCK.get(HEAD);
            plant = BuiltInRegistries.BLOCK.get(PLANT);
            if (head == Blocks.AIR || plant == Blocks.AIR) {
                return;
            }
        } else if (head == Blocks.AIR || plant == Blocks.AIR) {
            return;
        }
        int cells = 4096;
        int sections = 32;
        int remainingJobs = 32;
        var position = new BlockPos.MutableBlockPos();
        while (cells > 0 && sections > 0 && remainingJobs > 0) {
            if (current == null) {
                current = jobs.poll();
                if (current == null) {
                    return;
                }
                remainingJobs--;
            }
            var key = current.key;
            var level = key.level;
            var chunk = level.getChunkSource().getChunkNow(key.position.x, key.position.z);
            if (chunk == null || versions.getOrDefault(chunk, 0) >= VERSION) {
                finish();
                continue;
            }
            var worldSections = chunk.getSections();
            if (current.section == Integer.MAX_VALUE) {
                current.section = worldSections.length - 1;
            }
            while (current.section >= 0 && cells > 0 && sections > 0) {
                var section = worldSections[current.section];
                if (current.cell < 0) {
                    sections--;
                    if (section.hasOnlyAir() || !section.maybeHas(this::isHighGrass)) {
                        current.section--;
                        continue;
                    }
                    current.cell = 4095;
                }
                while (current.cell >= 0 && cells > 0) {
                    int index = current.cell--;
                    cells--;
                    int x = index & 15;
                    int z = (index >> 4) & 15;
                    int y = index >> 8;
                    if (isHighGrass(section.getBlockState(x, y, z))) {
                        position.set(key.position.getMinBlockX() + x,
                            chunk.getMinBuildHeight() + current.section * 16 + y, key.position.getMinBlockZ() + z);
                        var shortGrass = Blocks.SHORT_GRASS.defaultBlockState();
                        var replacement = !isHighGrass(level.getBlockState(position.below()))
                            && shortGrass.canSurvive(level, position) ? shortGrass : Blocks.AIR.defaultBlockState();
                        level.setBlock(position, replacement, Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE);
                    }
                }
                if (current.cell < 0) {
                    current.section--;
                }
            }
            if (current.section < 0) {
                versions.put(chunk, VERSION);
                chunk.setUnsaved(true);
                finish();
            }
        }
    }

    private void finish() {
        pending.remove(current.key);
        capacity.release();
        current = null;
    }

    private void clear(ServerStoppedEvent ignored) {
        jobs.clear();
        pending.clear();
        versions.clear();
        capacity.drainPermits();
        capacity.release(MAX_PENDING);
        warned.set(false);
        current = null;
    }

    private record Key(ServerLevel level, ChunkPos position) {}

    private static final class Job {
        private final Key key;
        private int section = Integer.MAX_VALUE;
        private int cell = -1;

        Job(Key key) {
            this.key = key;
        }
    }
}
