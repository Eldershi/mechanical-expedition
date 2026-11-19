package expedition.refinery;

import java.util.List;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.TagKey;
import net.minecraft.world.level.material.Fluid;
import net.neoforged.neoforge.fluids.FluidStack;
import net.neoforged.neoforge.fluids.capability.templates.FluidTank;
import net.ty.createcraftedbeginning.api.gas.GasAction;
import net.ty.createcraftedbeginning.api.gas.GasStack;
import net.ty.createcraftedbeginning.api.gas.handler.GasTransferSnapshot;
import net.ty.createcraftedbeginning.api.gas.pressure.GasPressureBoundary;
import net.ty.createcraftedbeginning.registry.gas.CCBGases;

public final class RefinerySteamPort implements GasPressureBoundary {
    private static final TagKey<Fluid> STEAM = TagKey.create(Registries.FLUID,
        ResourceLocation.fromNamespaceAndPath("c", "steam"));
    private static final ResourceLocation INTERNAL_STEAM = ResourceLocation.fromNamespaceAndPath("mekanism", "steam");

    private final FluidTank leftInput;
    private final FluidTank rightInput;
    private final Runnable markDirty;

    public RefinerySteamPort(FluidTank leftInput, FluidTank rightInput, Runnable markDirty) {
        this.leftInput = leftInput;
        this.rightInput = rightInput;
        this.markDirty = markDirty;
    }

    @Override
    public int getTanks() {
        return 1;
    }

    @Override
    public GasStack getGasInTank(int tank) {
        return GasStack.EMPTY;
    }

    @Override
    public boolean isGasValid(int tank, GasStack stack) {
        return tank == 0 && stack.is(CCBGases.STEAM.get()) && stack.isComponentsPatchEmpty();
    }

    @Override
    public GasStack drain(GasStack stack, GasAction action) {
        return GasStack.EMPTY;
    }

    @Override
    public GasStack drain(long amount, GasAction action) {
        return GasStack.EMPTY;
    }

    @Override
    public long fill(GasStack stack, GasAction action) {
        if (stack.isEmpty() || !isGasValid(0, stack)) return 0;
        var tank = steamInput();
        if (tank == null) return 0;
        // Each gas unit supplies one mB of the refinery's existing steam ingredient.
        int amount = (int) Math.min(stack.getAmount(), tank.getCapacity() - tank.getFluidAmount());
        if (amount <= 0) return 0;
        var current = tank.getFluid();
        var ingredient = current.isEmpty()
            ? new FluidStack(BuiltInRegistries.FLUID.get(INTERNAL_STEAM), amount)
            : current.copyWithAmount(amount);
        int filled = tank.fill(ingredient, action.toFluidAction());
        if (action.execute() && filled > 0) markDirty.run();
        return filled;
    }

    @Override
    public AtomicFillResult tryFillAtomically(List<GasStack> stacks, GasAction action) {
        long total = 0;
        GasStack steam = GasStack.EMPTY;
        for (var stack : stacks) {
            if (stack == null || stack.isEmpty()) continue;
            if (!isGasValid(0, stack) || stack.getAmount() > Integer.MAX_VALUE - total) {
                return AtomicFillResult.REJECTED;
            }
            total += stack.getAmount();
            steam = stack;
        }
        if (total == 0) return AtomicFillResult.SUCCESS;
        var batch = steam.copyWithAmount(total);
        if (fill(batch, GasAction.SIMULATE) != total) return AtomicFillResult.REJECTED;
        if (action.execute()) fill(batch, GasAction.EXECUTE);
        return AtomicFillResult.SUCCESS;
    }

    @Override
    public AtomicFillResult tryFillAtomicallyFromPressure(List<GasStack> stacks, long pressurePa, GasAction action) {
        return tryFillAtomically(stacks, action);
    }

    @Override
    public GasTransferSnapshot captureTransferSnapshot() {
        var left = leftInput.getFluid().copy();
        var right = rightInput.getFluid().copy();
        return () -> {
            leftInput.setFluid(left.copy());
            rightInput.setFluid(right.copy());
            markDirty.run();
        };
    }

    private FluidTank steamInput() {
        if (rightInput.getFluid().is(STEAM)) return rightInput;
        if (leftInput.getFluid().is(STEAM)) return leftInput;
        if (rightInput.isEmpty()) return rightInput;
        if (leftInput.isEmpty()) return leftInput;
        return null;
    }
}
