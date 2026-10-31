package expedition.chunkfuture.mixin;

import expedition.chunkfuture.StructureChunkRequest;
import net.minecraft.server.level.DistanceManager;
import net.minecraft.server.level.ServerChunkCache;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.ChunkStatus;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/**
 * Do not let a locator's off-thread request enqueue a blocking getChunk on the
 * server thread. Vanilla getChunkFuture's external-thread branch only schedules
 * generation there and flattens the result; this caller then waits externally.
 */
@Mixin(value = ServerChunkCache.class, priority = 900, remap = false)
public abstract class OffThreadStructureChunkMixin {
    @Shadow @Final private Thread f_8330_;
    @Shadow @Final private ServerLevel f_8329_;
    @Shadow @Final private DistanceManager f_8327_;

    @Inject(
        method = "m_7587_(IILnet/minecraft/world/level/chunk/ChunkStatus;Z)Lnet/minecraft/world/level/chunk/ChunkAccess;",
        at = @At("HEAD"), cancellable = true, remap = false, require = 1
    )
    private void expedition$awaitStructureFutureExternally(
            int x, int z, ChunkStatus status, boolean create,
            CallbackInfoReturnable<ChunkAccess> cir) {
        if (!create || status != ChunkStatus.f_62315_
                || Thread.currentThread() == f_8330_) {
            return;
        }
        ServerChunkCache cache = (ServerChunkCache) (Object) this;
        cir.setReturnValue(StructureChunkRequest.load(cache, f_8329_, f_8327_, x, z, status));
    }
}
