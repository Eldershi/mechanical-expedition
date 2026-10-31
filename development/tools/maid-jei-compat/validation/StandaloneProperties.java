import java.util.*;
import org.spongepowered.asm.service.*;

/** Process-local globals; no launcher, game instance, or persisted state. */
public final class StandaloneProperties implements IGlobalPropertyService {
    private record Key(String name) implements IPropertyKey {}
    private final Map<IPropertyKey,Object> data = new HashMap<>();
    public IPropertyKey resolveKey(String name) { return new Key(name); }
    @SuppressWarnings("unchecked") public <T> T getProperty(IPropertyKey key) { return (T)data.get(key); }
    public void setProperty(IPropertyKey key,Object value) { data.put(key,value); }
    @SuppressWarnings("unchecked") public <T> T getProperty(IPropertyKey key,T fallback) { return (T)data.getOrDefault(key,fallback); }
    public String getPropertyString(IPropertyKey key,String fallback) { return Objects.toString(data.get(key),fallback); }
}
