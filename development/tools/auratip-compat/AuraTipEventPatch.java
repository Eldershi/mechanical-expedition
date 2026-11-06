import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import org.objectweb.asm.commons.*;
import java.util.*;
import java.nio.file.*;
import java.util.zip.*;

/** Adapt AuraTip's end-of-client-tick listener to OELib's Post event. */
public final class AuraTipEventPatch {
    public static void main(String[] args) throws Exception {
        int changed=0;
        try(var input=new ZipFile(args[0]);var output=new ZipOutputStream(Files.newOutputStream(Path.of(args[1])))) {
            for(var it=input.entries();it.hasMoreElements();) {
                var entry=it.nextElement();byte[] data=input.getInputStream(entry).readAllBytes();
                if(entry.getName().equals("cc/sighs/auratip/handler/ClientEventHandler.class")) {
                    var node=new ClassNode();new ClassReader(data).accept(node,0);
                    for(var method:node.methods)if(method.name.equals("onClientTick")) {
                        if(!method.desc.equals("(Lcc/sighs/oelib/event/events/TickEvent$ClientTickEvent;)V"))throw new IllegalStateException("Unexpected listener");
                        var branch=method.instructions.getFirst();
                        while(!(branch instanceof JumpInsnNode))branch=branch.getNext();
                        if(branch.getOpcode()!=Opcodes.IF_ACMPEQ)throw new IllegalStateException("Unexpected phase guard");
                        var start=((JumpInsnNode)branch).label;
                        while(method.instructions.getFirst()!=start)method.instructions.remove(method.instructions.getFirst());
                        method.instructions.insert(start,new InsnNode(Opcodes.NOP));
                        for(var instruction=method.instructions.getFirst();instruction!=null;) {
                            var next=instruction.getNext();if(instruction instanceof FrameNode)method.instructions.remove(instruction);instruction=next;
                        }
                        method.localVariables=null;
                        method.desc="(Lcc/sighs/oelib/event/events/ClientTickEvent$Post;)V";
                        changed++;
                    }
                    var writer=new ClassWriter(ClassWriter.COMPUTE_FRAMES|ClassWriter.COMPUTE_MAXS) {
                        protected String getCommonSuperClass(String a,String b){return "java/lang/Object";}
                    };
                    node.accept(writer);data=writer.toByteArray();
                } else if(entry.getName().equals("cc/sighs/auratip/handler/ClientInputHandler.class")) {
                    var node=new ClassNode();new ClassReader(data).accept(node,0);
                    for(var method:node.methods)if(method.visibleAnnotations!=null)
                        for(var annotation:method.visibleAnnotations)if(annotation.desc.equals("Lcc/sighs/oelib/event/Subscribe;"))
                            annotation.desc="Lnet/minecraftforge/eventbus/api/SubscribeEvent;";
                    if(node.visibleAnnotations==null)node.visibleAnnotations=new ArrayList<>();
                    var subscriber=new AnnotationNode("Lnet/minecraftforge/fml/common/Mod$EventBusSubscriber;");
                    subscriber.values=new ArrayList<>(List.of("modid","auratip","value",Collections.singletonList(new String[]{"Lnet/minecraftforge/api/distmarker/Dist;","CLIENT"})));
                    node.visibleAnnotations.add(subscriber);
                    var mapping=Map.of(
                        "cc/sighs/oelib/event/events/InputEvent","net/minecraftforge/client/event/InputEvent",
                        "cc/sighs/oelib/event/events/InputEvent$Key","net/minecraftforge/client/event/InputEvent$Key",
                        "cc/sighs/oelib/event/events/InputEvent$MouseButton","net/minecraftforge/client/event/InputEvent$MouseButton",
                        "cc/sighs/oelib/event/events/InputEvent$MouseButton$Pre","net/minecraftforge/client/event/InputEvent$MouseButton$Pre");
                    var writer=new ClassWriter(0);node.accept(new ClassRemapper(writer,new SimpleRemapper(mapping)));data=writer.toByteArray();changed++;
                }
                output.putNextEntry(new ZipEntry(entry.getName()));output.write(data);output.closeEntry();
            }
        }
        if(changed!=2)throw new IllegalStateException("Expected tick and input handlers");
    }
}
