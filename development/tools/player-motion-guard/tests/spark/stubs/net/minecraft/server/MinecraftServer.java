package net.minecraft.server;

/** Test-only command sink. No Minecraft runtime, socket, or profiler is started. */
public final class MinecraftServer {
    public int commandCount;
    public String lastCommand = "";
    private final Commands commands = new Commands();
    public Commands m_129892_() { return commands; }
    public Object m_129893_() { return this; }
    public final class Commands {
        public int m_230957_(Object source, String command) {
            commandCount++; lastCommand = command; return 1;
        }
    }
}
