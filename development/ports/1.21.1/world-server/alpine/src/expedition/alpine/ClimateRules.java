package expedition.alpine;

import com.google.gson.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;
import net.minecraft.core.*;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.*;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.KeyDispatchDataCodec;
import net.minecraft.world.level.*;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.block.*;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.levelgen.*;

/** Local alpine bands: no biome replacement and no density-function modification. */
public final class ClimateRules {
    private static final JsonObject POLICY=loadPolicy();
    private static final Set<String> IDS=Set.copyOf(POLICY.getAsJsonObject("biomes").keySet());
    private static volatile Map<Biome,Profile> PROFILES=Map.of();
    private static volatile List<Group> GROUPS=List.of();
    private static volatile SurfaceSystem OVERWORLD_SURFACE;
    private static final AtomicLong TEMPERATURE_CALLS=new AtomicLong(),SURFACE_CALLS=new AtomicLong(),TREE_REJECTED=new AtomicLong();
    private record Group(float baseTemperature,ResourceKey<Biome>[] keys){}
    public record Profile(String id,float baseTemperature){}
    private ClimateRules(){}

    private static JsonObject loadPolicy(){
        Path file=Path.of("config/expedition-alpine-climate.json");
        if(Files.isRegularFile(file)){
            try(Reader reader=Files.newBufferedReader(file)){return JsonParser.parseReader(reader).getAsJsonObject();}
            catch(IOException e){throw new ExceptionInInitializerError(e);}
        }
        try(InputStream stream=ClimateRules.class.getResourceAsStream("/alpine-biome-policy.json")){
            if(stream==null)throw new IllegalStateException("Missing alpine policy");
            JsonObject root=JsonParser.parseReader(new InputStreamReader(stream,StandardCharsets.UTF_8)).getAsJsonObject();
            return root;
        }catch(IOException e){throw new ExceptionInInitializerError(e);}
    }
    public static double setting(String key,double fallback){return POLICY.has(key)?POLICY.get(key).getAsDouble():fallback;}
    public static String policy(){return POLICY.toString();}

    public static void loaded(LevelAccessor accessor){
        if(!(accessor instanceof Level level)||!level.dimension().equals(Level.OVERWORLD))return;
        register(level.registryAccess().registryOrThrow(Registries.BIOME));
        if(level instanceof ServerLevel server)OVERWORLD_SURFACE=server.getChunkSource().randomState().surfaceSystem();
    }

    @SuppressWarnings("unchecked")
    private static synchronized void register(Registry<Biome> registry){
        IdentityHashMap<Biome,Profile> profiles=new IdentityHashMap<>(PROFILES);
        Map<Float,List<ResourceKey<Biome>>> grouped=new TreeMap<>();
        for(Biome biome:registry){
            ResourceLocation id=registry.getKey(biome);
            if(id==null||!IDS.contains(id.toString()))continue;
            Profile p=new Profile(id.toString(),biome.getBaseTemperature());profiles.put(biome,p);
            grouped.computeIfAbsent(p.baseTemperature(),ignored->new ArrayList<>()).add(ResourceKey.create(Registries.BIOME,id));
        }
        PROFILES=Collections.unmodifiableMap(profiles);
        List<Group> groups=new ArrayList<>();
        grouped.forEach((temperature,keys)->groups.add(new Group(temperature,keys.toArray(ResourceKey[]::new))));
        GROUPS=List.copyOf(groups);
    }

    private static double hash(int x,int z){
        long n=x*341873128712L+z*132897987541L+0x6A09E667F3BCC909L;
        n=(n^(n>>>30))*0xBF58476D1CE4E5B9L;n=(n^(n>>>27))*0x94D049BB133111EBL;n^=n>>>31;
        return ((n>>>11)*0x1.0p-53)*2-1;
    }
    private static double smooth(double t){return t*t*(3-2*t);}
    private static double noise(int x,int z,int scale){
        double fx=(double)x/scale,fz=(double)z/scale;int ix=(int)Math.floor(fx),iz=(int)Math.floor(fz);
        double sx=smooth(fx-ix),sz=smooth(fz-iz);
        double a=hash(ix,iz)*(1-sx)+hash(ix+1,iz)*sx,b=hash(ix,iz+1)*(1-sx)+hash(ix+1,iz+1)*sx;
        return a*(1-sz)+b*sz;
    }
    public static double snowline(float baseTemperature,int x,int z){
        return setting("snowline_base_y",220)+Math.max(-.5,Math.min(1.25,baseTemperature))*setting("snowline_temperature_factor",24)
            +noise(x,z,384)*setting("broad_snowline_noise_blocks",4)+noise(x+137,z-91,96)*setting("fine_snowline_noise_blocks",2);
    }
    public static float cap(float original,float baseTemperature,int x,int y,int z){
        // The caller supplies actual Y from getTemperature's original cache key.
        // Tectonic's below(128) happens only inside the earlier original calculation.
        return Math.min(original,(float)(.15+(snowline(baseTemperature,x,z)-y)*setting("cooling_per_block",.0075)));
    }
    public static float temperature(Biome biome,BlockPos pos,float original){
        Profile p=PROFILES.get(biome);if(p==null)return original;
        float result=cap(original,p.baseTemperature(),pos.getX(),pos.getY(),pos.getZ());
        if(result<original)TEMPERATURE_CALLS.incrementAndGet();return result;
    }
    public static boolean allowTree(WorldGenLevel level,BlockPos pos,net.minecraft.util.RandomSource random){
        if(!level.getLevel().dimension().equals(Level.OVERWORLD))return true;
        Profile p=PROFILES.get(level.getBiome(pos).value());if(p==null)return true;
        double fadeStart=setting("tree_fade_start_below_snowline",50),fadeEnd=setting("tree_fade_end_below_snowline",26);
        double fraction=(pos.getY()-(snowline(p.baseTemperature(),pos.getX(),pos.getZ())-fadeStart))/(fadeStart-fadeEnd);
        boolean allow=fraction<=0||(fraction<1&&random.nextFloat()>smooth(fraction));
        if(!allow)TREE_REJECTED.incrementAndGet();return allow;
    }
    public static SurfaceRules.RuleSource wrap(SurfaceSystem owner,SurfaceRules.RuleSource original,Registry<Biome> registry,ChunkAccess chunk){
        if(owner!=OVERWORLD_SURFACE)return original;
        if(GROUPS.isEmpty())register(registry);
        List<SurfaceRules.RuleSource> sources=new ArrayList<>();
        for(Group group:GROUPS){
            SurfaceRules.RuleSource body=SurfaceRules.sequence(
                SurfaceRules.ifTrue(SurfaceRules.steep(),AlpineSurfaceRules.source(group.baseTemperature(),true,chunk)),
                AlpineSurfaceRules.source(group.baseTemperature(),false,chunk));
            body=SurfaceRules.ifTrue(SurfaceRules.abovePreliminarySurface(),SurfaceRules.ifTrue(SurfaceRules.ON_FLOOR,body));
            sources.add(SurfaceRules.ifTrue(SurfaceRules.isBiome(group.keys()),body));
        }
        sources.add(original);SURFACE_CALLS.incrementAndGet();
        return SurfaceRules.sequence(sources.toArray(SurfaceRules.RuleSource[]::new));
    }

    public static Map<String,Object> auditAt(Biome biome,BlockPos pos){
        Profile p=PROFILES.get(biome);Map<String,Object> out=new LinkedHashMap<>();
        out.put("eligible",p!=null);out.put("position",List.of(pos.getX(),pos.getY(),pos.getZ()));
        if(p!=null){out.put("biome",p.id());out.put("baseTemperature",p.baseTemperature());out.put("snowline",snowline(p.baseTemperature(),pos.getX(),pos.getZ()));}
        // Call the true hooked biome temperature, not a stand-alone approximation.
        out.put("coldEnoughToSnow",biome.coldEnoughToSnow(pos));out.put("warmEnoughToRain",biome.warmEnoughToRain(pos));
        out.put("actualHookedTemperature",((expedition.alpine.mixin.BiomeTemperatureAccess)(Object)biome).alpine$readTemperature(pos));
        out.put("temperatureHookApplications",TEMPERATURE_CALLS.get());out.put("surfaceChunkApplications",SURFACE_CALLS.get());out.put("treeCandidatesRejected",TREE_REJECTED.get());
        out.put("registeredBiomeInstances",PROFILES.size());return out;
    }
}
