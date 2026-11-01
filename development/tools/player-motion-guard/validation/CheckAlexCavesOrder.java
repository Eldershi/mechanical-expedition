import java.lang.reflect.Constructor;
import java.nio.file.*;
import java.util.jar.*;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.spongepowered.asm.launch.MixinBootstrap;
import org.spongepowered.asm.mixin.*;
import org.spongepowered.asm.mixin.transformer.IMixinTransformer;

/** Applies the unmodified Alex's Caves EntityMixin alongside this add-on. */
public final class CheckAlexCavesOrder {
    public static void main(String[] args) throws Exception {
        MixinBootstrap.init();
        MixinEnvironment environment = MixinEnvironment.getDefaultEnvironment();
        environment.setSide(MixinEnvironment.Side.SERVER);
        Mixins.addConfiguration("expedition-player-motion-guard.mixins.json");
        Mixins.addConfiguration("alexscaves-entity-order-test.mixins.json");
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
        Files.write(Path.of(args[1]), transformed);
        ClassNode after = new ClassNode();
        new ClassReader(transformed).accept(after, 0);
        MethodNode collide = after.methods.stream().filter(method -> method.name.equals("m_20272_")
                && method.desc.equals("(Lnet/minecraft/world/phys/Vec3;)Lnet/minecraft/world/phys/Vec3;"))
                .findFirst().orElseThrow();
        int index = 0, guard = -1, cancellation = -1, cancelledReturn = -1, alex = -1;
        for (AbstractInsnNode instruction : collide.instructions) {
            if (instruction instanceof MethodInsnNode call) {
                if (call.name.contains("expedition$checkCollision")) guard = index;
                if (guard >= 0 && cancellation < 0 && call.name.equals("isCancelled")) cancellation = index;
                if (call.name.contains("ac_collide")) alex = index;
            }
            if (cancellation >= 0 && cancelledReturn < 0 && instruction.getOpcode() == Opcodes.ARETURN)
                cancelledReturn = index;
            index++;
        }
        if (!(guard >= 0 && guard < cancellation && cancellation < cancelledReturn && cancelledReturn < alex))
            throw new AssertionError("Wrong collide injection order: " + guard + "/" + cancellation
                    + "/" + cancelledReturn + "/" + alex);
        System.out.println("ALEX_CAVES_ORDER_OK: player guard, cancellation check and early return precede original AC ac_collide HEAD callback");
    }
}
