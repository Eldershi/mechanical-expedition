package expedition.performance.client;

import com.seibel.distanthorizons.core.api.internal.chunkUpdating.ChunkPosQueue;
import com.seibel.distanthorizons.core.api.internal.chunkUpdating.ChunkUpdateData;
import com.seibel.distanthorizons.core.pos.DhChunkPos;
import expedition.performance.policy.ChunkQueuePolicy;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** DH 3.3.3 spins while its nearest item is debounced or its executor unavailable. */
@Pseudo
@Mixin(targets = "com.seibel.distanthorizons.core.api.internal.chunkUpdating.ChunkUpdateQueueManager", remap = false)
public abstract class DhQueueBackoff {
    @Shadow @Final public ChunkPosQueue preUpdateQueue;

    @Redirect(method = "tryDispatchReadyChunkUpdate", at = @At(value = "INVOKE", target =
        "Lcom/seibel/distanthorizons/core/api/internal/chunkUpdating/ChunkPosQueue;addItem(Lcom/seibel/distanthorizons/core/pos/DhChunkPos;Lcom/seibel/distanthorizons/core/api/internal/chunkUpdating/ChunkUpdateData;)V", remap = false), require = 3)
    private void expedition$waitAfterRequeue(ChunkPosQueue queue, DhChunkPos position, ChunkUpdateData data) {
        queue.addItem(position, data); // Preserve the original item, timestamp, ordering and queue limit.
        ChunkQueuePolicy.requeued.increment();
        if (preUpdateQueue.isEmpty()) ChunkQueuePolicy.backoff();
    }

    @Inject(method = "tryDispatchReadyChunkUpdate", at = @At(value = "INVOKE", target =
        "Ljava/util/concurrent/AbstractExecutorService;execute(Ljava/lang/Runnable;)V", shift = At.Shift.AFTER, remap = false), require = 1)
    private void expedition$dispatched(CallbackInfo ci) {
        ChunkQueuePolicy.dispatched.increment();
    }
}
