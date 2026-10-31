package expedition.ponderui.mixin;

import net.createmod.ponder.foundation.PonderTag;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** Preserve the real scroll item renderer, including school-specific NBT models. */
@Mixin(value=PonderTag.class,remap=false)
public interface PonderTagIconAccess {
    @Accessor("itemIcon") ItemStack expedition$itemIcon();
}
