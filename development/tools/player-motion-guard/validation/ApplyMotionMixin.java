import java.lang.reflect.Constructor;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.tree.analysis.*;
import org.spongepowered.asm.launch.MixinBootstrap;
import org.spongepowered.asm.mixin.*;
import org.spongepowered.asm.mixin.transformer.IMixinTransformer;

/** Checks the real Minecraft target, not a replacement Entity implementation. */
public final class ApplyMotionMixin {
    private static List<String> instructions(MethodNode method) {
        List<String> result = new ArrayList<>();
        for (AbstractInsnNode instruction : method.instructions) {
            if (instruction.getOpcode() < 0) continue;
            String value = "" + instruction.getOpcode();
            if (instruction instanceof MethodInsnNode call)
                value += ":" + call.owner + ":" + call.name + call.desc;
            else if (instruction instanceof FieldInsnNode field)
                value += ":" + field.owner + ":" + field.name + field.desc;
            else if (instruction instanceof VarInsnNode variable) value += ":" + variable.var;
            else if (instruction instanceof LdcInsnNode constant) value += ":" + constant.cst;
            else if (instruction instanceof TypeInsnNode type) value += ":" + type.desc;
            else if (instruction instanceof IntInsnNode integer) value += ":" + integer.operand;
            else if (instruction instanceof IincInsnNode increment)
                value += ":" + increment.var + ":" + increment.incr;
            result.add(value);
        }
        return result;
    }
    public static void main(String[] args) throws Exception {
        MixinBootstrap.init();
        MixinEnvironment environment = MixinEnvironment.getDefaultEnvironment();
        environment.setSide(MixinEnvironment.Side.SERVER);
        Mixins.addConfiguration("expedition-player-motion-guard.mixins.json");
        Constructor<?> constructor = Class.forName("org.spongepowered.asm.mixin.transformer.MixinTransformer")
                .getDeclaredConstructor();
        constructor.setAccessible(true);
        IMixinTransformer transformer = (IMixinTransformer) constructor.newInstance();
        String target = "net/minecraft/world/entity/Entity";
        byte[] original;
        try (JarFile jar = new JarFile(args[0])) {
            original = jar.getInputStream(jar.getJarEntry(target + ".class")).readAllBytes();
        }
        byte[] transformed = transformer.transformClass(environment, target.replace('/', '.'), original);
        if (Arrays.equals(original, transformed)) throw new AssertionError("Mixin not applied");
        Files.write(Path.of(args[1]), transformed);
        ClassNode before = new ClassNode(), after = new ClassNode();
        new ClassReader(original).accept(before, 0);
        new ClassReader(transformed).accept(after, 0);
        int guards = 0, untouched = 0;
        for (MethodNode method : after.methods) {
            if (method.instructions.size() > 0)
                new Analyzer<BasicValue>(new BasicVerifier()).analyze(after.name, method);
            if (method.name.equals("m_20256_") && method.desc.equals("(Lnet/minecraft/world/phys/Vec3;)V")
                    || method.name.equals("m_6478_")
                    && method.desc.equals("(Lnet/minecraft/world/entity/MoverType;Lnet/minecraft/world/phys/Vec3;)V")
                    || method.name.equals("m_20272_")
                    && method.desc.equals("(Lnet/minecraft/world/phys/Vec3;)Lnet/minecraft/world/phys/Vec3;")) {
                MethodInsnNode firstCall = null;
                for (AbstractInsnNode instruction : method.instructions) {
                    if (instruction instanceof MethodInsnNode call) { firstCall = call; break; }
                }
                // CallbackInfo construction precedes the merged callback invocation.
                boolean sawGuard = false, sawCancellation = false;
                for (AbstractInsnNode instruction : method.instructions) {
                    if (instruction instanceof MethodInsnNode call && call.name.contains("expedition$check"))
                        sawGuard = true;
                    if (instruction instanceof MethodInsnNode call && call.name.equals("isCancelled")) {
                        if (!sawGuard) throw new AssertionError("Cancellation before guard");
                        sawCancellation = true;
                        break;
                    }
                    if (instruction instanceof FieldInsnNode field && field.getOpcode() == Opcodes.PUTFIELD)
                        throw new AssertionError("Field write precedes guard: " + field.name);
                }
                if (firstCall == null || !sawGuard || !sawCancellation)
                    throw new AssertionError("Missing cancellable HEAD guard: " + method.name);
                guards++;
            }
        }
        for (MethodNode old : before.methods) {
            if (old.name.equals("<clinit>")
                    || old.name.equals("m_20256_") && old.desc.equals("(Lnet/minecraft/world/phys/Vec3;)V")
                    || old.name.equals("m_6478_")
                    && old.desc.equals("(Lnet/minecraft/world/entity/MoverType;Lnet/minecraft/world/phys/Vec3;)V")
                    || old.name.equals("m_20272_")
                    && old.desc.equals("(Lnet/minecraft/world/phys/Vec3;)Lnet/minecraft/world/phys/Vec3;")) continue;
            MethodNode current = after.methods.stream()
                    .filter(method -> method.name.equals(old.name) && method.desc.equals(old.desc))
                    .findFirst().orElseThrow();
            if (!instructions(old).equals(instructions(current)))
                throw new AssertionError("Unexpected edit: " + old.name + old.desc);
            untouched++;
        }
        if (guards != 3) throw new AssertionError("Expected exactly three guarded methods");
        MethodNode tripleSetter = before.methods.stream().filter(method -> method.name.equals("m_20334_")
                && method.desc.equals("(DDD)V")).findFirst().orElseThrow();
        if (instructions(tripleSetter).stream().noneMatch(value -> value.contains(":m_20256_(Lnet/minecraft/world/phys/Vec3;)V")))
            throw new AssertionError("DDD setter no longer delegates to Vec3 setter");
        System.out.println("REAL_MOTION_MIXIN_OK: three cancellable HEAD guards, DDD delegation checked, "
                + untouched + " other original methods retained; ASM verifier passed");
    }
}
