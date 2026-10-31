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

/** Apply the exact candidate hook/accessor without initializing Forge or Minecraft. */
public final class ApplyJeiMixin {
    public static void main(String[] args) throws Exception {
        MixinBootstrap.init();
        MixinEnvironment environment = MixinEnvironment.getDefaultEnvironment();
        environment.setSide(MixinEnvironment.Side.CLIENT);
        Mixins.addConfiguration("maid-jei-validation.mixins.json");
        Constructor<?> constructor = Class.forName("org.spongepowered.asm.mixin.transformer.MixinTransformer").getDeclaredConstructor();
        constructor.setAccessible(true);
        IMixinTransformer transformer = (IMixinTransformer)constructor.newInstance();
        Map<String,Integer> results = new LinkedHashMap<>();
        try (JarFile jei = new JarFile(args[0])) {
            for (String target : List.of("mezz/jei/gui/elements/GuiIconToggleButton", "mezz/jei/gui/recipes/RecipeTransferButton")) {
                byte[] original = jei.getInputStream(jei.getJarEntry(target + ".class")).readAllBytes();
                byte[] transformed = transformer.transformClass(environment,target.replace('/','.'),original);
                if (Arrays.equals(original,transformed)) throw new AssertionError("Mixin did not transform " + target);
                Files.write(Path.of(args[1],target.substring(target.lastIndexOf('/')+1)+".transformed.class"),transformed);
                ClassNode node = new ClassNode(); new ClassReader(transformed).accept(node,0);
                int handlers=0, injectedCalls=0;
                Set<String> accessors = new HashSet<>();
                for (MethodNode method : node.methods) {
                    if (method.name.contains("handler$") || method.name.contains("redirect$")) {
                        handlers++;
                        System.out.println("MERGED_HANDLER=" + method.name + method.desc);
                    }
                    if (List.of("getArea","getOnIcon","getOffIcon").contains(method.name)) accessors.add(method.name);
                    for (AbstractInsnNode instruction : method.instructions) {
                        if (instruction instanceof MethodInsnNode call && call.owner.equals(target)
                            && (call.name.contains("handler$") || call.name.contains("redirect$"))) {
                            injectedCalls++;
                            System.out.println("INJECTION_CALL=" + method.name + method.desc + " -> " + call.name);
                        }
                    }
                    if (method.instructions.size()>0)
                        new Analyzer<BasicValue>(new BasicVerifier()).analyze(node.name,method);
                }
                if (target.endsWith("RecipeTransferButton") && (handlers!=3 || injectedCalls!=3))
                    throw new AssertionError("Expected 3 production hooks/calls, got " + handlers + "/" + injectedCalls);
                if (target.endsWith("GuiIconToggleButton") && (accessors.size()!=3 || !node.interfaces.contains("studio/fantasyit/maid_storage_manager/api/mixin/IJEIButtonGetter")))
                    throw new AssertionError("Expected 3 accessors and IJEIButtonGetter: " + accessors + "/" + node.interfaces);
                results.put(target,handlers);
            }
        }
        System.out.println("REAL_MIXIN_TRANSFORM_OK="+results);
        System.out.println("ASM_BASIC_VERIFIER_ALL_METHODS_OK");
    }
}
