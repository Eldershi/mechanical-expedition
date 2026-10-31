package expedition.worldgen;

import com.google.gson.*;
import java.nio.file.*;
import java.util.*;

/** Sparse Twilight boss landmarks retain native eligibility, biome and locate rules. */
public final class BossDensityPolicy {
    private static volatile Map<String,Double> frequencies=Map.of();
    private static volatile boolean initialized=false;
    private BossDensityPolicy() {}
    public static synchronized void reload() {
        Map<String,Double> next=new HashMap<>();
        Path file=Path.of("config/expedition-boss-density.json");
        if(Files.isRegularFile(file)) {
            try {
                JsonObject root=JsonParser.parseString(Files.readString(file)).getAsJsonObject();
                for(var e:root.getAsJsonObject("twilightLandmarkFrequencies").entrySet()) {
                    double value=e.getValue().getAsDouble();
                    if(!e.getKey().startsWith("twilightforest:")||!Double.isFinite(value)||value<=0||value>1)
                        throw new IllegalArgumentException("Invalid Twilight boss frequency: "+e.getKey());
                    next.put(e.getKey(),value);
                }
            } catch(Exception error) {
                System.err.println("[Expedition boss density] Invalid configuration; native generation retained: "+error);
                next.clear();
            }
        }
        frequencies=Map.copyOf(next);initialized=true;
    }
    public static double score(String identifier,long seed,int chunkX,int chunkZ) {
        long value=seed ^ ((long)identifier.hashCode()*0x9e3779b97f4a7c15L)
            ^ ((long)chunkX*0x632be59bd9b4e019L) ^ ((long)chunkZ*0x85157af5L);
        value=(value^(value>>>30))*0xbf58476d1ce4e5b9L;
        value=(value^(value>>>27))*0x94d049bb133111ebL;
        value^=value>>>31;
        return (value>>>11)*0x1.0p-53;
    }
    public static boolean allowsId(String id,long seed,int chunkX,int chunkZ) {
        if(!initialized)reload();
        if(id==null)return true;
        Double frequency=frequencies.get(id);
        return frequency==null || score(id,seed,chunkX,chunkZ)<frequency;
    }
    public static boolean allows(Object placement,long seed,int chunkX,int chunkZ) {
        if(!initialized)reload();
        if(frequencies.isEmpty())return true;
        try {
            String id=(String)placement.getClass().getMethod("structurify$getStructureSetId").invoke(placement);
            if(id==null)return true; // Codec-only diagnostic trials have no registered set identity.
            return allowsId(id,seed,chunkX,chunkZ);
        } catch(ReflectiveOperationException error) {
            throw new IllegalStateException("Structurify placement identity unavailable",error);
        }
    }
}
