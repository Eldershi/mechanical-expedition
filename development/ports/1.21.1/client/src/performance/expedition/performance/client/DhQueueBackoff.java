package expedition.performance.client;

import com.seibel.distanthorizons.core.api.internal.chunkUpdating.ChunkPosQueue;
import com.seibel.distanthorizons.core.api.internal.chunkUpdating.ChunkUpdateData;
import com.seibel.distanthorizons.core.pos.DhChunkPos;
import java.util.concurrent.locks.LockSupport;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/** Yield after failed dispatch when the pre-update queue has no work. */
@Mixin(targets = "com.seibel.distanthorizons.core.api.internal.chunkUpdating.ChunkUpdateQueueManager", remap = false)
abstract class DhQueueBackoff {
    @Shadow @Final public ChunkPosQueue preUpdateQueue;

    @Redirect(method = "tryDispatchReadyChunkUpdate()V", at = @At(value = "INVOKE",
        target = "Lcom/seibel/distanthorizons/core/api/internal/chunkUpdating/ChunkPosQueue;"
            + "addItem(Lcom/seibel/distanthorizons/core/pos/DhChunkPos;"
            + "Lcom/seibel/distanthorizons/core/api/internal/chunkUpdating/ChunkUpdateData;)V"),
        require = 3, allow = 3)
    private void expedition$waitAfterRequeue(ChunkPosQueue queue, DhChunkPos position, ChunkUpdateData data) {
        queue.addItem(position, data);
        if (preUpdateQueue.isEmpty() && !Thread.currentThread().isInterrupted()) {
            LockSupport.parkNanos(250_000L);
        }
    }
}
