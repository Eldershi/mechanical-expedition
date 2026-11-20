package expedition.vanillaenchanting.mixin;

import expedition.vanillaenchanting.VanillaEnchantingTablePack;
import java.util.List;
import java.util.Map;
import net.minecraft.client.Minecraft;
import net.minecraft.server.packs.PackResources;
import net.minecraft.server.packs.PackType;
import net.minecraft.server.packs.resources.FallbackResourceManager;
import net.minecraft.server.packs.resources.MultiPackResourceManager;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = MultiPackResourceManager.class, remap = false)
abstract class EnchantingTableResourceMixin {
    @Shadow @Final private Map<String, FallbackResourceManager> namespacedManagers;

    @Inject(method = "<init>", at = @At("TAIL"))
    private void expedition$restoreEnchantingTable(PackType type, List<PackResources> packs, CallbackInfo ci) {
        if (type != PackType.CLIENT_RESOURCES) return;
        var minecraft = namespacedManagers.get("minecraft");
        var client = Minecraft.getInstance();
        if (minecraft != null && client != null) {
            minecraft.push(new VanillaEnchantingTablePack(client.getVanillaPackResources()));
        }
    }
}
