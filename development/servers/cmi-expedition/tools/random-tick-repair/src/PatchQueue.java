import java.io.PrintWriter;
import java.io.StringWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.InsnNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.util.CheckClassAdapter;
import org.objectweb.asm.util.Textifier;
import org.objectweb.asm.util.TraceMethodVisitor;

/** Mutates one exact known scheduler method; does not load or run Minecraft. */
public final class PatchQueue {
    private static String text(MethodNode method) {
        Textifier textifier = new Textifier();
        method.accept(new TraceMethodVisitor(textifier));
        StringWriter output = new StringWriter();
        textifier.print(new PrintWriter(output));
        return method.access + ":" + method.name + method.desc + ":" + method.signature + "\n" + output;
    }

    public static void main(String[] args) throws Exception {
        Path input = Path.of(args[0]), output = Path.of(args[1]);
        String target = args[2];
        ClassReader reader = new ClassReader(Files.readAllBytes(input));
        ClassNode before = new ClassNode();
        reader.accept(before, 0);
        ClassNode after = new ClassNode();
        reader.accept(after, 0);
        List<MethodNode> matches = after.methods.stream().filter(method -> method.name.equals(target)
                && method.desc.equals("(Lnet/minecraft/core/BlockPos;)V")).toList();
        if (matches.size() != 1) throw new AssertionError("Expected exactly one scheduler method");
        MethodNode method = matches.get(0);
        String originalBody = text(method);
        if (!originalBody.contains("java/util/List.add") || !originalBody.contains("m_7949_")) {
            throw new AssertionError("Unexpected original scheduler implementation");
        }
        method.instructions.clear();
        method.instructions.add(new InsnNode(Opcodes.RETURN));
        method.tryCatchBlocks.clear();
        method.localVariables = null;
        method.visibleLocalVariableAnnotations = null;
        method.invisibleLocalVariableAnnotations = null;
        method.maxStack = 0;
        method.maxLocals = 2;
        ClassWriter writer = new ClassWriter(reader, 0);
        after.accept(writer);
        byte[] bytes = writer.toByteArray();
        ClassNode checked = new ClassNode();
        new ClassReader(bytes).accept(checked, 0);
        if (before.methods.size() != checked.methods.size()) throw new AssertionError("Method count changed");
        int unchanged = 0;
        for (int i = 0; i < before.methods.size(); i++) {
            MethodNode original = before.methods.get(i), result = checked.methods.get(i);
            if (!original.name.equals(target)) {
                if (!text(original).equals(text(result))) throw new AssertionError("Unrelated method changed: " + original.name);
                unchanged++;
            } else {
                int executable = 0;
                for (AbstractInsnNode instruction : result.instructions) {
                    if (instruction.getOpcode() >= 0) {
                        executable++;
                        if (instruction.getOpcode() != Opcodes.RETURN) throw new AssertionError("Not a no-op");
                    }
                }
                if (executable != 1) throw new AssertionError("Expected one RETURN instruction");
            }
        }
        StringWriter errors = new StringWriter();
        CheckClassAdapter.verify(new ClassReader(bytes), false, new PrintWriter(errors));
        if (!errors.toString().isBlank()) throw new AssertionError(errors.toString());
        Files.write(output, bytes);
        System.out.println("ASM_CHECK_OK " + before.name + "; noOpMethod=" + target
                + "; unchangedOtherMethods=" + unchanged);
    }
}
