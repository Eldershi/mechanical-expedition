package expedition.iemachines.mixin;

import blusunrize.immersiveengineering.api.crafting.CokeOvenRecipe;
import blusunrize.immersiveengineering.api.multiblocks.blocks.env.IMultiblockContext;
import blusunrize.immersiveengineering.common.blocks.multiblocks.logic.CokeOvenLogic;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

@Mixin(value = CokeOvenLogic.class, remap = false)
abstract class CokeOvenCapacityMixin {
    @Shadow
    public abstract CokeOvenRecipe getRecipe(IMultiblockContext<CokeOvenLogic.State> context);

    @ModifyVariable(method = "tickServer(Lblusunrize/immersiveengineering/api/multiblocks/blocks/env/IMultiblockContext;)V",
        at = @At("STORE"), name = "itemSpace", require = 1)
    private int expedition$freeOutputSpace(int previous, IMultiblockContext<CokeOvenLogic.State> context) {
        var inventory = context.getState().getInventory();
        var stored = inventory.getStackInSlot(CokeOvenLogic.OUTPUT_SLOT);
        var recipe = getRecipe(context);
        if (recipe == null) return 0;
        var result = recipe.output.get();
        int max = Math.min(result.getMaxStackSize(), inventory.getSlotLimit(CokeOvenLogic.OUTPUT_SLOT));
        return Math.max(0, max - stored.getCount());
    }
}
