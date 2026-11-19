package expedition.space.mixin;

import expedition.space.LifeSupport;
import net.ty.createcraftedbeginning.api.canister.GasCanisterContainer;
import net.ty.createcraftedbeginning.api.gas.GasStack;
import net.ty.createcraftedbeginning.content.airtights.gascanister.container.CanisterContainerConsumers;
import net.ty.createcraftedbeginning.content.airtights.gascanisterpack.GasCanisterPackContainerContents;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(value = CanisterContainerConsumers.class, remap = false)
abstract class BreathingReserveMixin {
    @Redirect(method = {
        "findAffordableFuel(Lnet/minecraft/world/entity/player/Player;Ljava/util/function/ToDoubleFunction;)Ljava/util/Optional;",
        "findAffordableFuel(Lnet/minecraft/world/entity/player/Player;Lnet/ty/createcraftedbeginning/api/gas/Gas;Ljava/util/function/ToDoubleFunction;)Ljava/util/Optional;"
    }, at = @At(value = "INVOKE",
        target = "Lnet/ty/createcraftedbeginning/api/canister/GasCanisterContainer;getGasInTank(I)Lnet/ty/createcraftedbeginning/api/gas/GasStack;"),
        require = 2)
    private static GasStack excludeReserveFromSelection(GasCanisterContainer container, int tank) {
        return LifeSupport.reserve(container.getContainer(), tank) ? GasStack.EMPTY : container.getGasInTank(tank);
    }

    @Redirect(method = {"canCoverCost", "planPackDrain"}, at = @At(value = "INVOKE",
        target = "Lnet/ty/createcraftedbeginning/content/airtights/gascanisterpack/GasCanisterPackContainerContents;getGasInTank(I)Lnet/ty/createcraftedbeginning/api/gas/GasStack;"),
        require = 2)
    private static GasStack excludeReserveFromDrain(GasCanisterPackContainerContents container, int tank) {
        return LifeSupport.reserve(container.getContainer(), tank) ? GasStack.EMPTY : container.getGasInTank(tank);
    }
}
