package expedition.clientinterface.mixin;

import com.google.common.collect.ImmutableMap;
import net.p3pp3rf1y.sophisticatedcore.settings.StorageSettingsTabControlBase.ISettingsTabFactory;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(targets = "com.sighs.sophisticatedsorter.client.settings.ContainerSettingsTabControl", remap = false)
abstract class SorterSettingsMixin {
    // These factories belong to the sorter's local registry, separate from Core's global registry.
    @Redirect(method = "<clinit>", at = @At(value = "INVOKE", target =
        "Lcom/sighs/sophisticatedsorter/client/settings/ContainerSettingsTabControl;addFactory("
        + "Lcom/google/common/collect/ImmutableMap$Builder;Ljava/lang/String;"
        + "Lnet/p3pp3rf1y/sophisticatedcore/settings/StorageSettingsTabControlBase$ISettingsTabFactory;)V"),
        require = 4, allow = 4)
    private static void expedition$registerSorterTab(ImmutableMap.Builder<String, ISettingsTabFactory<?, ?>> tabs,
                                                    String category, ISettingsTabFactory<?, ?> factory) {
        tabs.put(category, factory);
    }
}
