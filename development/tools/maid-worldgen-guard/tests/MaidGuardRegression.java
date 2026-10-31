import java.lang.reflect.*;
import net.minecraft.server.MinecraftServer;
import net.minecraftforge.event.server.ServerStartedEvent;
import expedition.maidguard.WorldAgeGuard;

/** Execute the actual transformed callback/guard against a scheduling fixture. */
public final class MaidGuardRegression {
    public static void main(String[] args)throws Exception {
        Class<?> target=Class.forName("com.github.yimeng261.maidspell.worldgen.StellarEndshoreFixedSpawn");
        Method callback=target.getMethod("onServerStarted",ServerStartedEvent.class);
        Field placements=target.getField("testPlacements");
        int checked=0;
        for(long time:new long[]{1,20,24000,Long.MAX_VALUE}) {
            placements.setInt(null,0);
            MinecraftServer server=new MinecraftServer(time);
            callback.invoke(null,new ServerStartedEvent(server));
            if(server.scheduled!=0 || placements.getInt(null)!=0 || !WorldAgeGuard.existingWorld(time))
                throw new AssertionError("Existing world scheduled placement: "+time);
            checked++;
        }
        for(long time:new long[]{0,-1}) {
            placements.setInt(null,0);
            MinecraftServer server=new MinecraftServer(time);
            callback.invoke(null,new ServerStartedEvent(server));
            if(server.scheduled!=1 || placements.getInt(null)!=1 || WorldAgeGuard.existingWorld(time))
                throw new AssertionError("Nonpositive game time lost original callback: "+time);
            checked++;
        }
        System.out.println("TRANSFORMED_STARTUP_CALLBACK_REGRESSION_OK: "+checked+" game-time cases; existing worlds schedule nothing; time0 retains original scheduling path");
    }
}
