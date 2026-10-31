package net.minecraft.server;
import net.minecraft.server.level.ServerLevel;
public class MinecraftServer {
    public int scheduled;
    private final ServerLevel level;
    public MinecraftServer(long time) {level=new ServerLevel(time);}
    public ServerLevel m_129783_() {return level;}
    public void execute(Runnable action) {scheduled++;action.run();}
}
