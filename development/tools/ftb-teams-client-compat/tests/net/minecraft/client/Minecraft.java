package net.minecraft.client;
import net.minecraft.client.multiplayer.ClientPacketListener;
public class Minecraft {
    public static final Minecraft INSTANCE = new Minecraft();
    public ClientPacketListener connection;
    public static Minecraft m_91087_() { return INSTANCE; }
    public ClientPacketListener m_91403_() { return connection; }
}
