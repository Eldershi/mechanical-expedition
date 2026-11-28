package expedition.performance.client;

import dev.djefrey.colorwheel.instancing.ClrwlInstancedInstancer;
import dev.engine_room.flywheel.backend.engine.instancing.InstancedInstancer;
import dev.engine_room.flywheel.backend.gl.buffer.GlBuffer;
import dev.engine_room.flywheel.lib.memory.MemoryBlock;
import java.util.Arrays;
import org.lwjgl.system.Platform;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = {InstancedInstancer.class, ClrwlInstancedInstancer.class}, remap = false)
abstract class FlywheelUploadBatchMixin {
    @Shadow(remap = false) private GlBuffer vbo;

    @Unique private static final boolean expedition$batchUploads = Platform.get() == Platform.MACOSX;
    @Unique private static final long expedition$maxMirroredBuffer = 256L * 1024;
    @Unique private static final long expedition$mirrorBudget = 32L * 1024 * 1024;
    @Unique private static long expedition$allocatedMirrorBytes;

    @Unique private MemoryBlock expedition$mirror;
    @Unique private long[] expedition$ranges;
    @Unique private int expedition$rangeSize;
    @Unique private long expedition$dirtyBytes;

    @Redirect(
        method = "updateBuffer()V",
        at = @At(value = "INVOKE", target = "Ldev/engine_room/flywheel/backend/gl/buffer/GlBuffer;"
            + "upload(Ldev/engine_room/flywheel/lib/memory/MemoryBlock;)V")
    )
    private void expedition$uploadAndMirror(GlBuffer buffer, MemoryBlock data) {
        buffer.upload(data);
        expedition$releaseMirror();
        long size = data.size();
        if (expedition$batchUploads && size > 0 && size <= expedition$maxMirroredBuffer
            && expedition$allocatedMirrorBytes + size <= expedition$mirrorBudget) {
            expedition$mirror = MemoryBlock.malloc(size);
            data.copyTo(expedition$mirror);
            expedition$allocatedMirrorBytes += size;
        }
    }

    @Redirect(
        method = "lambda$writeChanged$0(II)V",
        at = @At(value = "INVOKE", target = "Ldev/engine_room/flywheel/backend/gl/buffer/GlBuffer;"
            + "uploadSpan(JLdev/engine_room/flywheel/lib/memory/MemoryBlock;)V")
    )
    private void expedition$queueUpload(GlBuffer buffer, long offset, MemoryBlock data) {
        if (expedition$mirror == null) {
            buffer.uploadSpan(offset, data);
            return;
        }

        data.copyTo(expedition$mirror.ptr() + offset);
        long bytes = data.size();
        expedition$dirtyBytes += bytes;
        if (expedition$ranges == null) {
            expedition$ranges = new long[16];
        } else if (expedition$rangeSize == expedition$ranges.length) {
            expedition$ranges = Arrays.copyOf(expedition$ranges, expedition$ranges.length * 2);
        }
        expedition$ranges[expedition$rangeSize++] = offset;
        expedition$ranges[expedition$rangeSize++] = offset + bytes;
    }

    @Inject(method = "writeChanged()V", at = @At("RETURN"))
    private void expedition$submitUploads(CallbackInfo callback) {
        if (expedition$rangeSize == 0) return;

        try {
            // Replacing densely updated storage lets the driver keep the previous storage in flight.
            if (expedition$dirtyBytes * 3 >= expedition$mirror.size() * 2) {
                vbo.upload(expedition$mirror);
                return;
            }

            // The retained bytes fill gaps between nearby dirty ranges.
            long start = expedition$ranges[0];
            long end = expedition$ranges[1];
            for (int index = 2; index < expedition$rangeSize; index += 2) {
                long nextStart = expedition$ranges[index];
                long nextEnd = expedition$ranges[index + 1];
                if (nextStart - end > 512 || nextEnd - start > 65536) {
                    vbo.uploadSpan(start, expedition$mirror.ptr() + start, end - start);
                    start = nextStart;
                }
                end = nextEnd;
            }
            vbo.uploadSpan(start, expedition$mirror.ptr() + start, end - start);
        } finally {
            expedition$rangeSize = 0;
            expedition$dirtyBytes = 0;
        }
    }

    @Inject(method = "delete()V", at = @At("HEAD"))
    private void expedition$releaseUploadStorage(CallbackInfo callback) {
        expedition$releaseMirror();
    }

    @Unique
    private void expedition$releaseMirror() {
        if (expedition$mirror != null) {
            expedition$allocatedMirrorBytes -= expedition$mirror.size();
            expedition$mirror.free();
            expedition$mirror = null;
        }
    }
}
