package expedition.engineering.mixin;

import blusunrize.immersiveengineering.api.multiblocks.blocks.component.IMultiblockComponent.CapabilityGetter;
import blusunrize.immersiveengineering.api.multiblocks.blocks.component.IMultiblockComponent.CapabilityRegistrar;
import blusunrize.immersiveengineering.common.blocks.multiblocks.logic.arcfurnace.ArcFurnaceLogic;
import expedition.engineering.ElectrodeHandler;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.neoforged.neoforge.capabilities.BlockCapability;
import net.neoforged.neoforge.items.IItemHandler;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(value = ArcFurnaceLogic.class, remap = false)
public abstract class ArcFurnaceElectrodeMixin {
    @Unique private static final BlockPos EXPEDITION_ELECTRODE_HATCH = new BlockPos(2, 4, 2);

    @Redirect(method = "registerCapabilities", at = @At(value = "INVOKE", ordinal = 1, target =
            "Lblusunrize/immersiveengineering/api/multiblocks/blocks/component/"
            + "IMultiblockComponent$CapabilityRegistrar;register(Lnet/neoforged/neoforge/capabilities/"
            + "BlockCapability;Lblusunrize/immersiveengineering/api/multiblocks/blocks/component/"
            + "IMultiblockComponent$CapabilityGetter;)V"))
    private void expedition$registerElectrodes(CapabilityRegistrar<ArcFurnaceLogic.State> registrar,
            BlockCapability<IItemHandler, Direction> itemCapability,
            CapabilityGetter<IItemHandler, ArcFurnaceLogic.State> original) {
        registrar.register(itemCapability, (state, position) -> {
            if (EXPEDITION_ELECTRODE_HATCH.equals(position.posInMultiblock())) {
                return new ElectrodeHandler(state.getInventory());
            }
            return original.getCapability(state, position);
        });
    }

}
