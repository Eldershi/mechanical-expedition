package expedition.questlines;

import java.util.List;
import java.util.Set;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.IntInsnNode;
import org.objectweb.asm.tree.LdcInsnNode;
import org.objectweb.asm.tree.MethodInsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.VarInsnNode;
import org.spongepowered.asm.mixin.extensibility.IMixinConfigPlugin;
import org.spongepowered.asm.mixin.extensibility.IMixinInfo;

public final class QuestLinesMixinPlugin implements IMixinConfigPlugin {
    private static final String CALLBACK = "org/spongepowered/asm/mixin/injection/callback/CallbackInfo";
    private static final String DRAW_HANDLER = "(Lnet/minecraft/client/gui/GuiGraphics;"
            + "Ldev/ftb/mods/ftblibrary/ui/Theme;IIIIL" + CALLBACK + ";)V";
    private static final String QUEST_ENHANCE_TEXTURE = "quest_enhance:textures/gui/decorative_line.png";
    private static final String DEPENDENCY_TEXTURE = "ftbquests:textures/gui/dependency.png";
    private static final int DEPENDENCY_TINT = 0xB4CCA3A3;
    private static final float DECORATIVE_HALF_WIDTH_SCALE = 1.6f;

    @Override
    public void postApply(String targetName, ClassNode target, String mixinName, IMixinInfo mixin) {
        MethodNode background = findHandler(target, "onDrawOffscreenBackground");
        MethodNode decorativeLines = findHandler(target, "quest_enhance$draw_decorative_dependency_line");
        useDependencyAppearance(target, decorativeLines);

        // CQA cancels drawOffsetBackground at HEAD after drawing the normal lines.
        // Run Quest Enhance's existing TAIL handler on that replacement path as well.
        for (var instruction : background.instructions) {
            if (instruction instanceof MethodInsnNode call && call.owner.equals(CALLBACK)
                    && call.name.equals("cancel") && call.desc.equals("()V")) {
                InsnList draw = new InsnList();
                draw.add(new VarInsnNode(Opcodes.ALOAD, 0));
                draw.add(new VarInsnNode(Opcodes.ALOAD, 1));
                draw.add(new VarInsnNode(Opcodes.ALOAD, 2));
                for (int slot = 3; slot <= 6; slot++) {
                    draw.add(new VarInsnNode(Opcodes.ILOAD, slot));
                }
                draw.add(new VarInsnNode(Opcodes.ALOAD, 7));
                draw.add(new MethodInsnNode(Opcodes.INVOKESPECIAL, target.name, decorativeLines.name,
                        DRAW_HANDLER, false));
                background.instructions.insert(call, draw);
                return;
            }
        }
        throw new IllegalStateException("Could not find Certain Questing Additions' background cancellation");
    }

    private static void useDependencyAppearance(ClassNode target, MethodNode decorativeLines) {
        MethodNode initializer = target.methods.stream().filter(method -> method.name.equals("<clinit>"))
                .findFirst().orElseThrow();
        findConstant(initializer, QUEST_ENHANCE_TEXTURE).cst = DEPENDENCY_TEXTURE;
        findConstant(decorativeLines, 3.0f).cst = DECORATIVE_HALF_WIDTH_SCALE;

        // Match the pack's uncompleted dependency tint with a finer stroke for dense decorative trees.
        for (var instruction : decorativeLines.instructions) {
            if (instruction instanceof MethodInsnNode call && call.owner.equals(target.name)
                    && call.name.contains("quest_enhance$draw_textured_line")) {
                AbstractInsnNode alpha = call.getPrevious();
                AbstractInsnNode blue = alpha.getPrevious();
                AbstractInsnNode green = blue.getPrevious();
                AbstractInsnNode red = green.getPrevious();
                if (!isConstant(alpha, 255) || !isConstant(blue, 180) || !isConstant(green, 180)
                        || red.getOpcode() != Opcodes.ICONST_0) {
                    throw new IllegalStateException("Unexpected Quest Enhance decorative line tint");
                }
                decorativeLines.instructions.set(red, channel(DEPENDENCY_TINT, 16));
                decorativeLines.instructions.set(green, channel(DEPENDENCY_TINT, 8));
                decorativeLines.instructions.set(blue, channel(DEPENDENCY_TINT, 0));
                decorativeLines.instructions.set(alpha, channel(DEPENDENCY_TINT, 24));
                return;
            }
        }
        throw new IllegalStateException("Could not find Quest Enhance's decorative line draw call");
    }

    private static LdcInsnNode findConstant(MethodNode method, Object value) {
        for (var instruction : method.instructions) {
            if (instruction instanceof LdcInsnNode load && value.equals(load.cst)) {
                return load;
            }
        }
        throw new IllegalStateException("Could not find decorative line constant " + value);
    }

    private static boolean isConstant(AbstractInsnNode instruction, int value) {
        return instruction instanceof IntInsnNode load && load.operand == value;
    }

    private static IntInsnNode channel(int argb, int shift) {
        return new IntInsnNode(Opcodes.SIPUSH, (argb >>> shift) & 0xFF);
    }

    private static MethodNode findHandler(ClassNode target, String name) {
        return target.methods.stream()
                .filter(method -> method.name.endsWith("$" + name) && method.desc.equals(DRAW_HANDLER))
                .findFirst()
                .orElseThrow(() -> new IllegalStateException("Could not find quest background handler " + name));
    }

    @Override public void onLoad(String mixinPackage) {}
    @Override public String getRefMapperConfig() { return null; }
    @Override public boolean shouldApplyMixin(String targetName, String mixinName) { return true; }
    @Override public void acceptTargets(Set<String> myTargets, Set<String> otherTargets) {}
    @Override public List<String> getMixins() { return List.of(); }
    @Override public void preApply(String targetName, ClassNode target, String mixinName, IMixinInfo mixin) {}
}
