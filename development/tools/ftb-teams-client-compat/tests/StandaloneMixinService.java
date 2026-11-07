import java.io.*;
import java.net.*;
import java.util.*;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.tree.ClassNode;
import org.spongepowered.asm.launch.platform.container.*;
import org.spongepowered.asm.logging.*;
import org.spongepowered.asm.mixin.MixinEnvironment;
import org.spongepowered.asm.service.*;
import org.spongepowered.asm.util.ReEntranceLock;

/** Read-only classpath adapter for the real Mixin 0.8.5 transformer. */
public final class StandaloneMixinService implements IMixinService, IClassProvider,
        IClassBytecodeProvider, ITransformerProvider, IClassTracker {
    private final ReEntranceLock lock = new ReEntranceLock(1);
    public String getName() { return "ExpeditionOfflineMixinValidation"; }
    public boolean isValid() { return true; }
    public void prepare() {}
    public MixinEnvironment.Phase getInitialPhase() { return MixinEnvironment.Phase.DEFAULT; }
    public void offer(IMixinInternal internal) {}
    public void init() {}
    public void beginPhase() {}
    public void checkEnv(Object ignored) {}
    public ReEntranceLock getReEntranceLock() { return lock; }
    public IClassProvider getClassProvider() { return this; }
    public IClassBytecodeProvider getBytecodeProvider() { return this; }
    public ITransformerProvider getTransformerProvider() { return this; }
    public IClassTracker getClassTracker() { return this; }
    public IMixinAuditTrail getAuditTrail() { return null; }
    public Collection<String> getPlatformAgents() { return List.of(); }
    public IContainerHandle getPrimaryContainer() { return new ContainerHandleVirtual(getName()); }
    public Collection<IContainerHandle> getMixinContainers() { return List.of(); }
    public InputStream getResourceAsStream(String name) { return getClass().getClassLoader().getResourceAsStream(name); }
    public String getSideName() { return "CLIENT"; }
    public MixinEnvironment.CompatibilityLevel getMinCompatibilityLevel() { return MixinEnvironment.CompatibilityLevel.JAVA_17; }
    public MixinEnvironment.CompatibilityLevel getMaxCompatibilityLevel() { return MixinEnvironment.CompatibilityLevel.JAVA_17; }
    public ILogger getLogger(String name) { return new LoggerAdapterDefault(name); }
    public URL[] getClassPath() {
        return Arrays.stream(System.getProperty("java.class.path").split(File.pathSeparator)).map(path -> {
            try { return new File(path).toURI().toURL(); }
            catch (MalformedURLException e) { throw new IllegalStateException(e); }
        }).toArray(URL[]::new);
    }
    public Class<?> findClass(String name) throws ClassNotFoundException { return findClass(name, false); }
    public Class<?> findClass(String name, boolean initialize) throws ClassNotFoundException {
        return Class.forName(name, initialize, getClass().getClassLoader());
    }
    public Class<?> findAgentClass(String name, boolean initialize) throws ClassNotFoundException { return findClass(name, initialize); }
    public ClassNode getClassNode(String name) throws IOException, ClassNotFoundException { return getClassNode(name, false); }
    public ClassNode getClassNode(String name, boolean transformers) throws IOException, ClassNotFoundException {
        try (InputStream in = getResourceAsStream(name.replace('.','/') + ".class")) {
            if (in == null) throw new ClassNotFoundException(name);
            ClassNode result = new ClassNode(); new ClassReader(in).accept(result, 0); return result;
        }
    }
    public Collection<ITransformer> getTransformers() { return List.of(); }
    public Collection<ITransformer> getDelegatedTransformers() { return List.of(); }
    public void addTransformerExclusion(String ignored) {}
    public void registerInvalidClass(String ignored) {}
    public boolean isClassLoaded(String ignored) { return false; }
    public String getClassRestrictions(String ignored) { return ""; }
}
