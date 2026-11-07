import java.lang.reflect.*;
import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import java.util.stream.*;
import com.mojang.authlib.GameProfile;
import dev.ftb.mods.ftbteams.api.client.KnownClientPlayer;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientPacketListener;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.tree.analysis.*;
import org.spongepowered.asm.launch.MixinBootstrap;
import org.spongepowered.asm.mixin.*;
import org.spongepowered.asm.mixin.transformer.IMixinTransformer;

/** Apply production Mixins to installed FTB bytecode, then execute the merged handlers. */
public class VerifyTeamMixins {
    static class Loader extends ClassLoader {
        Class<?> load(byte[] bytes) { return defineClass(null, bytes, 0, bytes.length); }
    }
    public static void main(String[] args) throws Exception {
        MixinBootstrap.init();
        MixinEnvironment env = MixinEnvironment.getDefaultEnvironment();
        env.setSide(MixinEnvironment.Side.CLIENT);
        Mixins.addConfiguration("expedition-ftb-teams-client-compat.mixins.json");
        Constructor<?> ctor = Class.forName("org.spongepowered.asm.mixin.transformer.MixinTransformer").getDeclaredConstructor();
        ctor.setAccessible(true);
        IMixinTransformer transformer = (IMixinTransformer) ctor.newInstance();
        ClassNode harness = new ClassNode();
        harness.version = Opcodes.V17; harness.access = Opcodes.ACC_PUBLIC;
        harness.name = "MergedTeamHandlers"; harness.superName = "java/lang/Object";
        String[] targets = {"dev/ftb/mods/ftbteams/data/ClientTeamManagerImpl",
            "dev/ftb/mods/ftbteams/client/gui/CreatePartyScreen$InvitePanel"};
        String[] methods = {"initSelfDetails", "addWidgets"};
        String[] handlers = {"connectedIdentity", "sortInvitations"};
        try (JarFile jar = new JarFile(args[0])) {
            for (int i = 0; i < targets.length; i++) {
                byte[] original = jar.getInputStream(jar.getJarEntry(targets[i] + ".class")).readAllBytes();
                byte[] changed = transformer.transformClass(env, targets[i].replace('/', '.'), original);
                if (Arrays.equals(original, changed)) throw new AssertionError("Unchanged target " + targets[i]);
                Files.write(Path.of(args[1], "transformed-" + i + ".class"), changed);
                ClassNode node = new ClassNode(); new ClassReader(changed).accept(node, 0);
                int redirected = 0, merged = 0;
                for (MethodNode method : node.methods) {
                    if (method.instructions.size() > 0)
                        new Analyzer<BasicValue>(new BasicVerifier()).analyze(node.name, method);
                    if (method.name.equals(methods[i])) {
                        for (AbstractInsnNode insn : method.instructions) {
                            if (insn instanceof MethodInsnNode call) {
                                if (call.owner.equals(targets[i]) && call.name.contains(handlers[i])) redirected++;
                                if (i == 0 && call.owner.equals("com/mojang/authlib/GameProfile") && call.name.equals("getId"))
                                    throw new AssertionError("Unredirected launcher UUID");
                                if (i == 1 && call.owner.equals("java/util/stream/Stream") && call.name.equals("sorted") && call.desc.startsWith("()"))
                                    throw new AssertionError("Unredirected natural ordering");
                            }
                        }
                    }
                    if (method.name.contains(handlers[i])) {
                        merged++;
                        method.access = Opcodes.ACC_PUBLIC | Opcodes.ACC_STATIC;
                        method.name = handlers[i];
                        method.desc = "(Ljava/lang/Object;" + method.desc.substring(1);
                        method.signature = null;
                        harness.methods.add(method);
                    }
                }
                if (redirected != 1 || merged != 1) throw new AssertionError("Redirect shape " + redirected + "/" + merged);
            }
        }
        ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS);
        harness.accept(writer);
        Class<?> executed = new Loader().load(writer.toByteArray());
        Method identity = executed.getMethod("connectedIdentity", Object.class, GameProfile.class);
        UUID launcherId = UUID.fromString("12121212-3434-5656-7878-909090909090");
        UUID acceptedId = UUID.fromString("98989898-7676-5454-3232-101010101010");
        GameProfile launcher = new GameProfile(launcherId, "Player");
        Minecraft.INSTANCE.connection = new ClientPacketListener(new GameProfile(acceptedId, "Player"));
        if (!acceptedId.equals(identity.invoke(null, null, launcher))) throw new AssertionError("Server UUID must win");
        Minecraft.INSTANCE.connection = new ClientPacketListener(launcher);
        if (!launcherId.equals(identity.invoke(null, null, launcher))) throw new AssertionError("Online UUID regression");
        Minecraft.INSTANCE.connection = null;
        if (!launcherId.equals(identity.invoke(null, null, launcher))) throw new AssertionError("No-connection fallback");
        Method sort = executed.getMethod("sortInvitations", Object.class, Stream.class);
        UUID a = new UUID(0, 1), b = new UUID(0, 2), c = new UUID(0, 3);
        var one = new KnownClientPlayer(a, "alpha", true, a, new GameProfile(a, "alpha"), null);
        var two = new KnownClientPlayer(b, "ALPHA", true, b, new GameProfile(b, "ALPHA"), null);
        var three = new KnownClientPlayer(c, "Zulu", true, c, new GameProfile(c, "Zulu"), null);
        @SuppressWarnings("unchecked")
        List<KnownClientPlayer> ordered = ((Stream<KnownClientPlayer>) sort.invoke(null, null, Stream.of(three, two, one))).toList();
        if (!ordered.equals(List.of(one, two, three))) throw new AssertionError("Invitation ordering");
        if (((Stream<?>) sort.invoke(null, null, Stream.empty())).count() != 0) throw new AssertionError("Empty invitations");
        System.out.println("REAL_MIXIN_TRANSFORM_OK targets=2 redirects=2 bytecode-verifier=passed");
        System.out.println("MERGED_HANDLER_REGRESSIONS_OK mismatched-uuid online-uuid disconnected-fallback multiple-invitees name-tie empty-list");
    }
}
