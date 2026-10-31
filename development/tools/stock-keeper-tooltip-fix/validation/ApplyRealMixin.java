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
import org.spongepowered.asm.service.MixinService;

/** Apply the frozen production jar with the actual bundled Mixin transformer. */
public final class ApplyRealMixin {
    public static void main(String[] args) throws Exception {
        MixinBootstrap.init();
        MixinEnvironment environment = MixinEnvironment.getDefaultEnvironment();
        environment.setSide(MixinEnvironment.Side.CLIENT);
        Mixins.addConfiguration("expedition-stock-keeper-tooltip.mixins.json");
        Constructor<?> constructor = Class.forName("org.spongepowered.asm.mixin.transformer.MixinTransformer").getDeclaredConstructor();
        constructor.setAccessible(true);
        IMixinTransformer transformer = (IMixinTransformer)constructor.newInstance();
        String target = "com/simibubi/create/content/logistics/stockTicker/StockKeeperRequestScreen";
        byte[] original;
        try (JarFile create = new JarFile(args[0])) {
            original = create.getInputStream(create.getJarEntry(target + ".class")).readAllBytes();
        }
        byte[] transformed = transformer.transformClass(environment,target.replace('/','.'),original);
        if (Arrays.equals(original,transformed)) throw new AssertionError("Mixin did not transform target class");
        Files.write(Path.of(args[1]),transformed);
        ClassNode node = new ClassNode(); new ClassReader(transformed).accept(node,0);
        int redirects = 0, copies = 0, rawFields = 0;
        Set<String> handlers = new HashSet<>();
        for (MethodNode method : node.methods) {
            if (method.name.contains("tooltipCopy")) {
                handlers.add(method.name);
                for (AbstractInsnNode instruction : method.instructions) {
                    if (instruction instanceof MethodInsnNode call && call.owner.equals("net/minecraft/world/item/ItemStack")
                        && call.name.equals("m_41777_")) copies++;
                }
            }
            if (method.name.equals("renderForeground")) {
                for (AbstractInsnNode instruction : method.instructions) {
                    if (instruction instanceof MethodInsnNode call && call.owner.equals(target) && call.name.contains("tooltipCopy")) redirects++;
                    if (instruction instanceof FieldInsnNode field && field.owner.equals("com/simibubi/create/content/logistics/BigItemStack")
                        && field.name.equals("stack")) rawFields++;
                }
            }
            if (method.instructions.size() > 0)
                new Analyzer<BasicValue>(new BasicVerifier()).analyze(node.name,method);
        }
        if (redirects != 2 || copies != 1 || rawFields != 0 || handlers.size() != 1)
            throw new AssertionError("Unexpected applied mixin shape: " + redirects + "/" + copies + "/" + rawFields + "/" + handlers);
        System.out.println("REAL_MIXIN_TRANSFORM_OK");
        System.out.println("SERVICE=" + MixinService.getService().getName());
        System.out.println("2 tooltip fields replaced; 1 merged handler calls ItemStack.copy; 0 raw tooltip fields remain");
        System.out.println("ASM_BASIC_VERIFIER_ALL_METHODS_OK");
        System.out.println("MERGED_HANDLER=" + handlers.iterator().next());
    }
}
