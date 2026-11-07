package net.minecraft.client.multiplayer;
import com.mojang.authlib.GameProfile;
public class ClientPacketListener {
    private final GameProfile accepted;
    public ClientPacketListener(GameProfile accepted) { this.accepted = accepted; }
    public GameProfile m_105144_() { return accepted; }
}
