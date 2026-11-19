package expedition.space;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.saveddata.SavedData;

final class FreightData extends SavedData {
    static final int BATCH = 8;
    static final int OUTPUT = 9;
    static final int CARRIER = 18;
    static final int FUEL = 19;
    static final int DUNGEON = 1;
    static final int VISITED_OTHER = 2;
    static final int VISITED_MOON = 4;
    static final int VISITED_EARTH_ORBIT = 8;
    static final int VISITED_MOON_ORBIT = 16;

    enum Role {
        SATELLITE("satellite_relay"), LAUNCH("freight_launchpad"), LIFT("space_elevator"),
        DROP("orbital_drop_cannon"), GATE("other_gate"), BEACON("surface_beacon");

        final String path;

        Role(String path) { this.path = path; }

        static Role of(ResourceLocation id) {
            if (!id.getNamespace().equals("expedition_space")) return null;
            for (Role role : values()) if (role.path.equals(id.getPath())) return role;
            return null;
        }
    }

    record Key(UUID team, ResourceKey<Level> dimension, Role role) {
        CompoundTag save() {
            var tag = new CompoundTag();
            tag.putUUID("team", team);
            tag.putString("dimension", dimension.location().toString());
            tag.putString("role", role.name());
            return tag;
        }

        static Key load(CompoundTag tag) {
            return new Key(tag.getUUID("team"), ResourceKey.create(Registries.DIMENSION,
                ResourceLocation.parse(tag.getString("dimension"))), Role.valueOf(tag.getString("role")));
        }
    }

    final class Station extends SimpleContainer {
        final Key key;
        BlockPos pos;
        boolean registered;
        boolean automatic;
        long nextLaunch;

        Station(Key key, BlockPos pos) {
            super(27);
            this.key = key;
            this.pos = pos.immutable();
            addListener(container -> setDirty());
        }

        @Override
        public boolean stillValid(net.minecraft.world.entity.player.Player player) {
            return player instanceof net.minecraft.server.level.ServerPlayer serverPlayer
                && SpaceLogistics.team(serverPlayer).equals(key.team())
                && player.level().dimension().equals(key.dimension())
                && player.distanceToSqr(pos.getCenter()) <= 64
                && SpaceLogistics.operational(serverPlayer.server, this);
        }

        List<ItemStack> input() {
            List<ItemStack> cargo = new ArrayList<>();
            for (int slot = 0; slot < BATCH; slot++) {
                ItemStack stack = getItem(slot);
                if (!stack.isEmpty()) cargo.add(stack.copy());
            }
            return cargo;
        }

        boolean receive(List<ItemStack> cargo) {
            List<Integer> free = new ArrayList<>();
            for (int slot = OUTPUT; slot < OUTPUT + BATCH; slot++) {
                if (getItem(slot).isEmpty()) free.add(slot);
            }
            if (free.size() < cargo.size()) return false;
            for (int index = 0; index < cargo.size(); index++) setItem(free.get(index), cargo.get(index));
            return true;
        }
    }

    record Shipment(UUID id, Key source, Key target, long due, List<ItemStack> cargo) {}

    final Map<Key, Station> stations = new LinkedHashMap<>();
    final Map<UUID, Shipment> shipments = new LinkedHashMap<>();
    final Map<UUID, int[]> deliveries = new LinkedHashMap<>();
    final Map<UUID, Integer> milestones = new LinkedHashMap<>();
    final Map<UUID, BlockPos> dungeons = new LinkedHashMap<>();
    final Map<UUID, BlockPos> returnGates = new LinkedHashMap<>();

    static FreightData get(MinecraftServer server) {
        return server.overworld().getDataStorage().computeIfAbsent(
            new Factory<>(FreightData::new, FreightData::load, null), "expedition_space_freight");
    }

    boolean flag(UUID player, int bit) {
        return (milestones.getOrDefault(player, 0) & bit) != 0;
    }

    void mark(UUID player, int bit) {
        int previous = milestones.getOrDefault(player, 0);
        if ((previous & bit) == 0) {
            milestones.put(player, previous | bit);
            setDirty();
        }
    }

    void delivered(UUID team, boolean headingToMoon) {
        int[] count = deliveries.computeIfAbsent(team, ignored -> new int[2]);
        int direction = headingToMoon ? 0 : 1;
        if (count[direction] < Integer.MAX_VALUE) count[direction]++;
        setDirty();
    }

    boolean stable(UUID team) {
        int[] count = deliveries.get(team);
        return count != null && count[0] > 0 && count[1] > 0 && (long) count[0] + count[1] >= 3;
    }

    private static FreightData load(CompoundTag root, HolderLookup.Provider registries) {
        var data = new FreightData();
        for (Tag child : root.getList("stations", Tag.TAG_COMPOUND)) {
            CompoundTag tag = (CompoundTag) child;
            Key key = Key.load(tag);
            var station = data.new Station(key, BlockPos.of(tag.getLong("pos")));
            station.registered = tag.getBoolean("registered");
            station.automatic = tag.getBoolean("automatic");
            station.nextLaunch = tag.getLong("nextLaunch");
            for (Tag saved : tag.getList("items", Tag.TAG_COMPOUND)) {
                CompoundTag item = (CompoundTag) saved;
                int slot = item.getInt("slot");
                if (slot >= 0 && slot < station.getContainerSize()) {
                    station.setItem(slot, ItemStack.parseOptional(registries, item.getCompound("stack")));
                }
            }
            data.stations.put(key, station);
        }
        for (Tag child : root.getList("shipments", Tag.TAG_COMPOUND)) {
            CompoundTag tag = (CompoundTag) child;
            List<ItemStack> items = new ArrayList<>();
            for (Tag item : tag.getList("cargo", Tag.TAG_COMPOUND)) {
                ItemStack.parse(registries, item).ifPresent(items::add);
            }
            UUID id = tag.getUUID("id");
            data.shipments.put(id, new Shipment(id, Key.load(tag.getCompound("source")),
                Key.load(tag.getCompound("target")), tag.getLong("due"), items));
        }
        CompoundTag progress = root.getCompound("progress");
        for (String player : progress.getAllKeys()) data.milestones.put(UUID.fromString(player), progress.getInt(player));
        CompoundTag deliveryTag = root.getCompound("deliveries");
        for (String team : deliveryTag.getAllKeys()) data.deliveries.put(UUID.fromString(team), deliveryTag.getIntArray(team));
        readPositions(root.getCompound("dungeons"), data.dungeons);
        readPositions(root.getCompound("returns"), data.returnGates);
        return data;
    }

    @Override
    public CompoundTag save(CompoundTag root, HolderLookup.Provider registries) {
        var stationTags = new ListTag();
        for (Station station : stations.values()) {
            CompoundTag tag = station.key.save();
            tag.putLong("pos", station.pos.asLong());
            tag.putBoolean("registered", station.registered);
            tag.putBoolean("automatic", station.automatic);
            tag.putLong("nextLaunch", station.nextLaunch);
            var items = new ListTag();
            for (int slot = 0; slot < station.getContainerSize(); slot++) {
                ItemStack stack = station.getItem(slot);
                if (stack.isEmpty()) continue;
                var item = new CompoundTag();
                item.putInt("slot", slot);
                item.put("stack", stack.save(registries));
                items.add(item);
            }
            tag.put("items", items);
            stationTags.add(tag);
        }
        root.put("stations", stationTags);
        var shipmentTags = new ListTag();
        for (Shipment shipment : shipments.values()) {
            var tag = new CompoundTag();
            tag.putUUID("id", shipment.id());
            tag.put("source", shipment.source().save());
            tag.put("target", shipment.target().save());
            tag.putLong("due", shipment.due());
            var items = new ListTag();
            for (ItemStack stack : shipment.cargo()) items.add(stack.save(registries));
            tag.put("cargo", items);
            shipmentTags.add(tag);
        }
        var progress = new CompoundTag();
        milestones.forEach((player, flags) -> progress.putInt(player.toString(), flags));
        var deliveryTag = new CompoundTag();
        deliveries.forEach((team, counts) -> deliveryTag.putIntArray(team.toString(), counts));
        root.put("shipments", shipmentTags);
        root.put("progress", progress);
        root.put("deliveries", deliveryTag);
        root.put("dungeons", writePositions(dungeons));
        root.put("returns", writePositions(returnGates));
        return root;
    }

    private static CompoundTag writePositions(Map<UUID, BlockPos> map) {
        var tag = new CompoundTag();
        map.forEach((id, pos) -> tag.putLong(id.toString(), pos.asLong()));
        return tag;
    }

    private static void readPositions(CompoundTag tag, Map<UUID, BlockPos> map) {
        for (String id : tag.getAllKeys()) map.put(UUID.fromString(id), BlockPos.of(tag.getLong(id)));
    }
}
