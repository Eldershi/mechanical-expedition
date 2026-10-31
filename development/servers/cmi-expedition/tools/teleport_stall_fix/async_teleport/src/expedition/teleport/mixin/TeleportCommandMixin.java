package expedition.teleport.mixin;

import expedition.teleport.AsyncTeleportPreparation;
import java.util.Collection;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.arguments.coordinates.Coordinates;
import net.minecraft.server.commands.TeleportCommand;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Coerce;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = TeleportCommand.class, remap = false)
public abstract class TeleportCommandMixin {
    @Inject(method = "m_139032_", at = @At("HEAD"), remap = false, require = 1)
    private static void expedition$cancelOldPreparation(CommandSourceStack source,
            Collection<? extends Entity> targets, Entity destination, CallbackInfoReturnable<Integer> cir) {
        // Entity destinations already exist in loaded chunks. Even this warm
        // path must supersede a previously queued cold coordinate teleport.
        AsyncTeleportPreparation.cancelFor(targets);
    }

    @Inject(method = "m_139025_", at = @At("HEAD"), cancellable = true, remap = false, require = 1)
    private static void expedition$prepareDestination(CommandSourceStack source,
            Collection<? extends Entity> targets, ServerLevel level, Coordinates position,
            Coordinates rotation, @Coerce Object facing, CallbackInfoReturnable<Integer> cir) {
        if (AsyncTeleportPreparation.defer(source, targets, level, position, rotation, facing)) {
            // The command accepted these targets; success feedback is emitted
            // by vanilla only after the asynchronous preparation completes.
            cir.setReturnValue(targets.size());
        }
    }
}
