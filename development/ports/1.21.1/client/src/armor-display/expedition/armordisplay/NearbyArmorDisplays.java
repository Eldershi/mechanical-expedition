package expedition.armordisplay;

import java.lang.ref.WeakReference;

import net.mcreator.protectionpixel.block.ArmorhangerBlock;
import net.mcreator.protectionpixel.block.ArmorloadplatformBlock;
import net.mcreator.protectionpixel.block.FoldedsteamectoskeletonBlock;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.entity.BlockEntity;

public final class NearbyArmorDisplays {
    private static Snapshot snapshot;

    private NearbyArmorDisplays() {}

    public static boolean contains(ClientLevel level, ChunkPos center, int radius) {
        long tick = level.getGameTime();
        var current = snapshot;
        if (current == null || current.level().get() != level || current.tick() != tick
            || !current.center().equals(center) || current.radius() != radius) {
            current = new Snapshot(new WeakReference<>(level), center, radius, tick,
                scan(level, center, radius));
            snapshot = current;
        }
        return current.present();
    }

    private static boolean scan(ClientLevel level, ChunkPos center, int radius) {
        for (int z = center.z - radius; z <= center.z + radius; z++) {
            for (int x = center.x - radius; x <= center.x + radius; x++) {
                var chunk = level.getChunk(x, z);
                if (chunk == null) continue;
                for (var entity : chunk.getBlockEntities().values()) {
                    if (isArmorDisplay(entity)) return true;
                }
            }
        }
        return false;
    }

    public static boolean isArmorDisplay(BlockEntity entity) {
        var block = entity.getBlockState().getBlock();
        return block instanceof ArmorhangerBlock || block instanceof ArmorloadplatformBlock
            || block instanceof FoldedsteamectoskeletonBlock;
    }

    public static void invalidate() {
        snapshot = null;
    }

    private record Snapshot(WeakReference<ClientLevel> level, ChunkPos center, int radius,
                            long tick, boolean present) {}
}
