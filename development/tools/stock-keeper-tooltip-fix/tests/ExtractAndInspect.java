import java.nio.file.*;
import java.util.*;
import java.util.jar.*;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;

/** Extract the installed UUID-generating methods unchanged, avoiding mod bootstrap. */
public class ExtractAndInspect {
    public static void main(String[] args) throws Exception {
        try (JarFile apoth = new JarFile(args[0]); JarFile create = new JarFile(args[1])) {
            String original = "dev/shadowsoffire/apotheosis/adventure/socket/gem/GemItem";
            ClassNode source = new ClassNode();
            new ClassReader(apoth.getInputStream(apoth.getJarEntry(original + ".class"))).accept(source, 0);
            ClassNode target = new ClassNode();
            target.version = Opcodes.V17; target.access = Opcodes.ACC_PUBLIC;
            target.name = "InstalledGemUuidMethods"; target.superName = "java/lang/Object";
            for (MethodNode method : source.methods) {
                if (!Set.of("getOrCreateUUIDs", "generateAndSave").contains(method.name)) continue;
                // Only the owner of the call between the two extracted methods changes.
                for (AbstractInsnNode instruction : method.instructions) {
                    if (instruction instanceof MethodInsnNode call && call.owner.equals(original))
                        call.owner = target.name;
                }
                target.methods.add(method);
            }
            if (target.methods.size() != 2) throw new AssertionError("UUID method signature drift");
            ClassWriter writer = new ClassWriter(0); target.accept(writer);
            Files.write(Path.of(args[2], target.name + ".class"), writer.toByteArray());

            ClassNode screen = new ClassNode();
            new ClassReader(create.getInputStream(create.getJarEntry(
                "com/simibubi/create/content/logistics/stockTicker/StockKeeperRequestScreen.class"))).accept(screen, 0);
            int reads = 0, tooltipCalls = 0;
            for (MethodNode method : screen.methods) {
                if (!method.name.equals("renderForeground")) continue;
                for (AbstractInsnNode instruction : method.instructions) {
                    if (instruction instanceof FieldInsnNode field && field.getOpcode() == Opcodes.GETFIELD
                        && field.owner.equals("com/simibubi/create/content/logistics/BigItemStack")
                        && field.name.equals("stack")) reads++;
                    if (instruction instanceof MethodInsnNode call && Set.of("m_41651_", "m_280153_").contains(call.name))
                        tooltipCalls++;
                }
            }
            if (reads != 2 || tooltipCalls != 2) throw new AssertionError("Tooltip target drift: " + reads + "/" + tooltipCalls);
            System.out.println("EXACT_TARGETS_OK: 2 stack reads, 2 tooltip paths");
            System.out.println("INSTALLED_APOTHEOSIS_UUID_BYTECODE_EXTRACTED");
        }
    }
}
