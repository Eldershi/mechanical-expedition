package expedition.refinery;

import java.util.List;

import net.neoforged.neoforge.fluids.FluidStack;
import net.neoforged.neoforge.fluids.capability.templates.FluidTank;
import net.ty.createcraftedbeginning.api.gas.GasAction;
import net.ty.createcraftedbeginning.api.gas.GasStack;
import net.ty.createcraftedbeginning.api.gas.handler.GasTransferSnapshot;
import net.ty.createcraftedbeginning.api.gas.pressure.GasPressureBoundary;
import net.ty.createcraftedbeginning.api.gas.GasRegistries;

public final class RefinerySteamPort implements GasPressureBoundary {
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
        return tank == 0 && input(stack) != null;
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
        var input = input(stack);
        if (input == null) return 0;
        var tank = inputTank(input);
        if (tank == null) return 0;
        int amount = (int) Math.min(stack.getAmount(), tank.getCapacity() - tank.getFluidAmount());
        if (amount <= 0) return 0;
        var current = tank.getFluid();
        FluidStack ingredient = current.isEmpty() ? input.stack(amount) : current.copyWithAmount(amount);
        int filled = tank.fill(ingredient, action.toFluidAction());
        if (action.execute() && filled > 0) markDirty.run();
        return filled;
    }

    @Override
    public AtomicFillResult tryFillAtomically(List<GasStack> stacks, GasAction action) {
        long total = 0;
        GasStack gas = GasStack.EMPTY;
        for (var stack : stacks) {
            if (stack == null || stack.isEmpty()) continue;
            if (!isGasValid(0, stack) || stack.getAmount() > Integer.MAX_VALUE - total
                || (!gas.isEmpty() && !GasStack.isSameGasSameComponents(gas, stack))) {
                return AtomicFillResult.REJECTED;
            }
            total += stack.getAmount();
            gas = stack;
        }
        if (total == 0) return AtomicFillResult.SUCCESS;
        var batch = gas.copyWithAmount(total);
        if (fill(batch, GasAction.SIMULATE) != total) return AtomicFillResult.REJECTED;
        if (action.execute()) {
            var snapshot = captureTransferSnapshot();
            if (fill(batch, GasAction.EXECUTE) != total) {
                snapshot.restore();
                return AtomicFillResult.REJECTED;
            }
        }
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

    private static RefineryGasInputs.Input input(GasStack stack) {
        if (stack.isEmpty() || !stack.isComponentsPatchEmpty()) return null;
        return RefineryGasInputs.byGas(GasRegistries.GAS_REGISTRY.getKey(stack.getGasType())).orElse(null);
    }

    private FluidTank inputTank(RefineryGasInputs.Input input) {
        if (input.matches(rightInput.getFluid())) return rightInput;
        if (input.matches(leftInput.getFluid())) return leftInput;
        if (rightInput.isEmpty()) return rightInput;
        if (leftInput.isEmpty()) return leftInput;
        return null;
    }
}
