package expedition.armordisplay.mixin;

import expedition.armordisplay.NearbyArmorDisplays;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.world.level.LevelAccessor;
import net.neoforged.bus.api.Event;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets = "net.mcreator.protectionpixel.procedures.ArmorrenderProcedure", remap = false)
abstract class ArmorRenderMixin {
    @Inject(method = "execute(Lnet/neoforged/bus/api/Event;Lnet/minecraft/world/level/LevelAccessor;)V",
        at = @At("HEAD"), cancellable = true)
    private static void expedition$skipEmptyArea(Event event, LevelAccessor world, CallbackInfo callback) {
        if (!(world instanceof ClientLevel level)) return;
        var client = Minecraft.getInstance();
        if (client.player == null || !NearbyArmorDisplays.contains(level, client.player.chunkPosition(),
            client.options.getEffectiveRenderDistance())) {
            callback.cancel();
        }
    }
}
