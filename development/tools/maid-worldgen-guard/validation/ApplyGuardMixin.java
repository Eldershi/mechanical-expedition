import java.lang.reflect.Constructor;
import java.nio.file.*;
import java.io.*;
import java.util.*;
import java.util.jar.*;
import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.tree.analysis.*;
import org.objectweb.asm.util.*;
import org.spongepowered.asm.launch.MixinBootstrap;
import org.spongepowered.asm.mixin.*;
import org.spongepowered.asm.mixin.transformer.IMixinTransformer;

/** Real Mixin application and exact transformed callback scheduling fixture. */
public final class ApplyGuardMixin {
    private static int position(LabelNode label,Map<AbstractInsnNode,Integer> positions) {
        AbstractInsnNode node=label;while(node!=null&&node.getOpcode()<0)node=node.getNext();
        return node==null?-1:positions.get(node);
    }
    private static String text(MethodNode method) {
        Map<AbstractInsnNode,Integer> positions=new IdentityHashMap<>();int index=0;
        for(AbstractInsnNode node:method.instructions)if(node.getOpcode()>=0)positions.put(node,index++);
        StringBuilder result=new StringBuilder();
        for(AbstractInsnNode node:method.instructions) {
            if(node.getOpcode()<0)continue;
            result.append(node.getOpcode()).append(':');
            if(node instanceof FieldInsnNode n)result.append(n.owner).append(n.name).append(n.desc);
            else if(node instanceof MethodInsnNode n)result.append(n.owner).append(n.name).append(n.desc).append(n.itf);
            else if(node instanceof TypeInsnNode n)result.append(n.desc);
            else if(node instanceof LdcInsnNode n)result.append(n.cst);
            else if(node instanceof InvokeDynamicInsnNode n)result.append(n.name).append(n.desc).append(n.bsm).append(Arrays.toString(n.bsmArgs));
            else if(node instanceof VarInsnNode n)result.append(n.var);
            else if(node instanceof JumpInsnNode n)result.append(position(n.label,positions));
            else if(node instanceof IntInsnNode n)result.append(n.operand);
            else if(node instanceof IincInsnNode n)result.append(n.var).append('/').append(n.incr);
            else if(node instanceof TableSwitchInsnNode n) {result.append(n.min).append('/').append(n.max).append('/').append(position(n.dflt,positions));for(LabelNode label:n.labels)result.append('/').append(position(label,positions));}
            else if(node instanceof LookupSwitchInsnNode n) {result.append(n.keys).append('/').append(position(n.dflt,positions));for(LabelNode label:n.labels)result.append('/').append(position(label,positions));}
            else if(node instanceof MultiANewArrayInsnNode n)result.append(n.desc).append(n.dims);
            result.append('\n');
        }
        for(TryCatchBlockNode block:method.tryCatchBlocks)result.append("TRY").append(position(block.start,positions)).append('/').append(position(block.end,positions)).append('/').append(position(block.handler,positions)).append('/').append(block.type);
        return result.toString();
    }
    public static void main(String[] args)throws Exception {
        MixinBootstrap.init();
        MixinEnvironment environment=MixinEnvironment.getDefaultEnvironment();
        environment.setSide(MixinEnvironment.Side.SERVER);
        Mixins.addConfiguration("expedition-maid-worldgen-guard.mixins.json");
        Constructor<?> constructor=Class.forName("org.spongepowered.asm.mixin.transformer.MixinTransformer").getDeclaredConstructor();
        constructor.setAccessible(true);IMixinTransformer transformer=(IMixinTransformer)constructor.newInstance();
        String target="com/github/yimeng261/maidspell/worldgen/StellarEndshoreFixedSpawn";
        byte[] original;
        try(JarFile jar=new JarFile(args[0])) {original=jar.getInputStream(jar.getJarEntry(target+".class")).readAllBytes();}
        byte[] transformed=transformer.transformClass(environment,target.replace('/','.'),original);
        if(Arrays.equals(original,transformed))throw new AssertionError("Mixin not applied");
        Files.write(Path.of(args[1]),transformed);
        ClassNode before=new ClassNode(),after=new ClassNode();
        new ClassReader(original).accept(before,0);new ClassReader(transformed).accept(after,0);
        int unchanged=0,guards=0,cancelCalls=0,originalSchedules=0;
        MethodNode callback=null;
        for(MethodNode method:after.methods) {
            if(method.instructions.size()>0)new Analyzer<BasicValue>(new BasicVerifier()).analyze(after.name,method);
            if(method.name.contains("protectExistingWorld")) {
                guards++;
                for(AbstractInsnNode instruction:method.instructions)
                    if(instruction instanceof MethodInsnNode call && call.owner.equals("org/spongepowered/asm/mixin/injection/callback/CallbackInfo")&&call.name.equals("cancel"))cancelCalls++;
            }
            if(method.name.equals("onServerStarted")) {
                callback=method;
                boolean firstGuard=false;
                for(AbstractInsnNode instruction:method.instructions)if(instruction instanceof MethodInsnNode call) {
                    if(call.name.contains("protectExistingWorld"))firstGuard=true;
                    if(call.name.equals("execute")&&call.owner.equals("net/minecraft/server/MinecraftServer")) {
                        if(!firstGuard)throw new AssertionError("Scheduling precedes guard");originalSchedules++;
                    }
                }
            }
        }
        for(MethodNode old:before.methods) {
            if(old.name.equals("onServerStarted"))continue;
            MethodNode current=after.methods.stream().filter(m->m.name.equals(old.name)&&m.desc.equals(old.desc)).findFirst().orElseThrow();
            if(!text(old).equals(text(current)))throw new AssertionError("Unexpected edit: "+old.name);
            unchanged++;
        }
        if(callback==null||guards!=1||cancelCalls!=1||originalSchedules!=1)throw new AssertionError("Wrong interception shape");
        ClassNode shell=new ClassNode();shell.version=Opcodes.V17;shell.access=Opcodes.ACC_PUBLIC;shell.name=target;shell.superName="java/lang/Object";
        shell.fields.add(new FieldNode(Opcodes.ACC_PUBLIC|Opcodes.ACC_STATIC,"testPlacements","I",null,null));
        for(MethodNode method:after.methods)
            if(method.name.equals("onServerStarted")||method.name.contains("protectExistingWorld")||method.name.equals("lambda$onServerStarted$0"))shell.methods.add(method);
        if(shell.methods.size()!=3)throw new AssertionError("Extraction drift");
        MethodNode place=new MethodNode(Opcodes.ACC_PRIVATE|Opcodes.ACC_STATIC,"placeIfNeeded","(Lnet/minecraft/server/MinecraftServer;)V",null,null);
        place.instructions.add(new FieldInsnNode(Opcodes.GETSTATIC,target,"testPlacements","I"));
        place.instructions.add(new InsnNode(Opcodes.ICONST_1));place.instructions.add(new InsnNode(Opcodes.IADD));
        place.instructions.add(new FieldInsnNode(Opcodes.PUTSTATIC,target,"testPlacements","I"));place.instructions.add(new InsnNode(Opcodes.RETURN));
        shell.methods.add(place);
        ClassWriter writer=new ClassWriter(ClassWriter.COMPUTE_MAXS);shell.accept(writer);
        Path output=Path.of(args[2],target+".class");Files.createDirectories(output.getParent());Files.write(output,writer.toByteArray());
        System.out.println("REAL_MIXIN_GUARD_APPLY_OK: one cancellable HEAD guard; original scheduling path retained; "+unchanged+" other original methods unchanged; ASM verifier passed");
    }
}
