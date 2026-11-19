package expedition.space.cooling;

import java.util.List;
import java.util.Set;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.InsnNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.VarInsnNode;
import org.spongepowered.asm.mixin.extensibility.IMixinConfigPlugin;
import org.spongepowered.asm.mixin.extensibility.IMixinInfo;

public final class CoolingMixinPlugin implements IMixinConfigPlugin {
    private static final String BASIN_MIXIN = "expedition.space.mixin.FluidLogisticsBasinMixin";
    private static final String BASIN = "Lcom/simibubi/create/content/processing/basin/BasinBlockEntity;";
    private static final String RECIPE = "Lnet/minecraft/world/item/crafting/Recipe;";
    private static final String RETURN = "Lorg/spongepowered/asm/mixin/injection/callback/CallbackInfoReturnable;";

    @Override
    public void postApply(String targetName, ClassNode target, String mixinName, IMixinInfo info) {
        if (!mixinName.equals(BASIN_MIXIN)) return;
        // Fluid Logistics installs a cancellable callback on BasinRecipe.apply.
        var gate = target.methods.stream().filter(method -> method.name.endsWith("$fluidlogistics$requireRegularCooling"))
            .filter(method -> method.desc.equals("(" + BASIN + RECIPE + "Z" + RETURN + ")V"))
            .findFirst().orElseThrow(() -> new IllegalStateException("Missing Fluid Logistics basin cooling callback"));
        gate.instructions.clear();
        gate.tryCatchBlocks.clear();
        gate.localVariables = null;
        gate.instructions.add(new VarInsnNode(Opcodes.ALOAD, 0));
        gate.instructions.add(new VarInsnNode(Opcodes.ALOAD, 1));
        gate.instructions.add(new VarInsnNode(Opcodes.ALOAD, 3));
        gate.instructions.add(new MethodInsnNode(Opcodes.INVOKESTATIC, "expedition/space/cooling/CoolingSources",
            "requireBasinCooling", "(" + BASIN + RECIPE + RETURN + ")V", false));
        gate.instructions.add(new InsnNode(Opcodes.RETURN));
        gate.maxStack = 3;
    }

    @Override public void onLoad(String mixinPackage) {}
    @Override public String getRefMapperConfig() { return null; }
    @Override public boolean shouldApplyMixin(String targetName, String mixinName) { return true; }
    @Override public void acceptTargets(Set<String> myTargets, Set<String> otherTargets) {}
    @Override public List<String> getMixins() { return null; }
    @Override public void preApply(String targetName, ClassNode target, String mixinName, IMixinInfo info) {}
}
