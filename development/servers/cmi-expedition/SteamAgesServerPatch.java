import org.objectweb.asm.*;
import org.objectweb.asm.tree.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

/** Remove only client render suppliers from the server's fluid registration chain. */
public final class SteamAgesServerPatch {
    public static void main(String[] args) throws Exception {
        Path source=Path.of(args[0]),target=Path.of(args[1]);
        String name="dev/celestiacraft/create_steam_ages/commom/register/CSAFluids.class";
        int removed=0;Set<String> lambdas=new HashSet<>();
        try(var input=new ZipFile(source.toFile());var output=new ZipOutputStream(Files.newOutputStream(target))) {
            for(var it=input.entries();it.hasMoreElements();) {
                var entry=it.nextElement();byte[] blob=input.getInputStream(entry).readAllBytes();
                if(entry.getName().equals(name)) {
                    var node=new ClassNode();new ClassReader(blob).accept(node,0);
                    for(var method:node.methods)if(method.name.equals("<clinit>")) {
                        for(var instruction=method.instructions.getFirst();instruction!=null;) {
                            var next=instruction.getNext();
                            if(instruction instanceof MethodInsnNode call && call.owner.equals("com/tterrag/registrate/builders/FluidBuilder") && call.name.equals("renderType")) {
                                var previous=instruction.getPrevious();
                                while(previous!=null && previous.getOpcode()<0)previous=previous.getPrevious();
                                if(!(previous instanceof InvokeDynamicInsnNode supplier))throw new IllegalStateException("Unexpected fluid render supplier shape");
                                for(Object arg:supplier.bsmArgs)if(arg instanceof Handle handle)lambdas.add(handle.getName());
                                method.instructions.remove(supplier);method.instructions.remove(instruction);removed++;
                            }
                            instruction=next;
                        }
                    }
                    node.methods.removeIf(method->lambdas.contains(method.name) && method.desc.equals("()Lnet/minecraft/client/renderer/RenderType;"));
                    if(removed!=2 || lambdas.size()!=2)throw new IllegalStateException("Expected exactly two steam render suppliers: "+removed+" / "+lambdas);
                    var writer=new ClassWriter(0);node.accept(writer);blob=writer.toByteArray();
                }
                var out=new ZipEntry(entry.getName());out.setTime(entry.getTime());output.putNextEntry(out);output.write(blob);output.closeEntry();
            }
        }
        if(removed!=2)throw new IllegalStateException("Steam fluid class not patched");
        System.out.println("Removed two client render suppliers; preserved all fluid, bucket and tag registrations.");
    }
}
