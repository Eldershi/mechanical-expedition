package expedition.industry;

import java.util.Map;

import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.event.lifecycle.FMLCommonSetupEvent;

@Mod("expedition_upstream_compat")
public final class SteamMachineMigration {
    private static final String SPOUT = "advanced_spout";
    private static final String HAMMER = "steam_hammer";
    private static final String FLUID_BACKUP = "expedition:legacy_fluid_tanks";
    private static final Map<String, String> MACHINE_IDS = Map.of(
        "cmi:" + SPOUT, "steam_letters:" + SPOUT,
        "cmi:" + HAMMER, "steam_letters:" + HAMMER,
        "cmi:bronze_solar_boiler", "steam_letters:bronze_solar_boiler",
        "cmi:bronze_fluid_burner", "steam_letters:bronze_fluid_burner"
    );
    private static final Map<String, String> BLOCK_ENTITY_IDS = Map.of(
        "cmi:" + SPOUT, "steam_letters:" + SPOUT,
        "cmi:" + HAMMER, "steam_letters:" + HAMMER,
        "cmi:bronze_solar_boiler", "steam_letters:solar_boiler",
        "cmi:bronze_fluid_burner", "steam_letters:fluid_burner"
    );
    private static final Map<String, String> STEAM_FLUIDS = Map.of(
        "create_steam_ages:steam", "steam_letters:steam",
        "create_steam_ages:flowing_steam", "steam_letters:flowing_steam",
        "create_steam_ages:high_temperature_steam", "steam_letters:superheated_steam",
        "create_steam_ages:flowing_high_temperature_steam", "steam_letters:flowing_superheated_steam"
    );
    private static final Map<String, String> STEAM_BUCKETS = Map.of(
        "create_steam_ages:steam_bucket", "steam_letters:steam_bucket",
        "create_steam_ages:high_temperature_steam_bucket", "steam_letters:superheated_steam_bucket"
    );

    public SteamMachineMigration(IEventBus modBus) {
        modBus.addListener(this::addMachineAliases);
    }

    private void addMachineAliases(FMLCommonSetupEvent event) {
        event.enqueueWork(() -> {
            addAliases(BuiltInRegistries.BLOCK, MACHINE_IDS);
            addAliases(BuiltInRegistries.ITEM, MACHINE_IDS);
            addAliases(BuiltInRegistries.BLOCK_ENTITY_TYPE, BLOCK_ENTITY_IDS);
            addAliases(BuiltInRegistries.FLUID, STEAM_FLUIDS);
            addAliases(BuiltInRegistries.ITEM, STEAM_BUCKETS);
        });
    }

    private static void addAliases(Registry<?> registry, Map<String, String> aliases) {
        aliases.forEach((legacy, current) -> {
            ResourceLocation source = ResourceLocation.parse(legacy);
            ResourceLocation target = ResourceLocation.parse(current);
            if (!registry.containsKey(source) && registry.containsKey(target)) {
                registry.addAlias(source, target);
            }
        });
    }

    public static CompoundTag migrate(CompoundTag data) {
        String oldId = data.getString("id");
        String currentId = BLOCK_ENTITY_IDS.getOrDefault(oldId, oldId);
        boolean isSpout = currentId.equals("steam_letters:" + SPOUT);
        boolean isHammer = currentId.equals("steam_letters:" + HAMMER);
        boolean steamLetters = currentId.startsWith("steam_letters:") || currentId.startsWith("cmi:");
        boolean isSolar = steamLetters && (currentId.endsWith("_solar_boiler")
                || currentId.equals("steam_letters:solar_boiler"));
        boolean isBurner = steamLetters && (currentId.endsWith("_fluid_burner")
                || currentId.equals("steam_letters:fluid_burner"));
        boolean isBoiler = steamLetters && currentId.endsWith("_boiler") && !isSolar;
        boolean isEngine = steamLetters && (currentId.endsWith("_steam_engine")
                || currentId.equals("steam_letters:steam_engine"));
        boolean isCreateTank = currentId.equals("create:fluid_tank");
        if (!isSpout && !isHammer && !isSolar && !isBurner && !isBoiler && !isEngine && !isCreateTank) {
            return data;
        }

        CompoundTag result = data.copy();
        result.putString("id", currentId);
        if (!result.contains("NeoForgeData", Tag.TAG_COMPOUND)
                && result.contains("ForgeData", Tag.TAG_COMPOUND)) {
            result.put("NeoForgeData", result.getCompound("ForgeData"));
        }
        CompoundTag backup = new CompoundTag();
        if (isSpout) {
            ListTag tanks = result.getList("Tanks", Tag.TAG_COMPOUND);
            for (int index = 0; index < tanks.size(); index++) {
                CompoundTag tank = tanks.getCompound(index);
                CompoundTag content = tank.getCompound("TankContent");
                if (!content.contains("Fluid", Tag.TAG_COMPOUND)) {
                    CompoundTag fluid = migrateFluid(content, false, backup, "Tanks." + index);
                    if (fluid != null) {
                        CompoundTag savedTank = new CompoundTag();
                        savedTank.put("Fluid", fluid);
                        tank.put("TankContent", savedTank);
                    }
                }
            }
        } else if (isHammer) {
            CompoundTag fluid = migrateFluid(result.getCompound("Steam"), true, backup, "Steam");
            if (fluid != null) {
                result.put("Steam", fluid);
            }
        } else if (isSolar) {
            convertTank(result, "InputTank", "WaterTank", false, backup);
            convertTank(result, "OutputTank", "SteamTank", true, backup);
        } else if (isBurner) {
            convertTank(result, "FuelTank", "tank", false, backup);
        } else if (isEngine) {
            convertTank(result, "Tank", "Tank", true, backup);
        } else {
            convertTank(result, "TankContent", "TankContent", false, backup);
            if (isBoiler) {
                convertTank(result, "SteamTank", "SteamTank", true, backup);
            }
        }
        if (!backup.isEmpty()) {
            CompoundTag persistentData = result.getCompound("NeoForgeData");
            CompoundTag saved = persistentData.getCompound(FLUID_BACKUP);
            saved.merge(backup);
            persistentData.put(FLUID_BACKUP, saved);
            result.put("NeoForgeData", persistentData);
        }
        return result;
    }

    private static void convertTank(CompoundTag data, String currentKey, String legacyKey,
            boolean steam, CompoundTag backup) {
        boolean hasCurrent = data.contains(currentKey, Tag.TAG_COMPOUND);
        CompoundTag original = data.getCompound(hasCurrent ? currentKey : legacyKey);
        CompoundTag fluid = migrateFluid(original, steam, backup, currentKey);
        if (fluid != null) {
            CompoundTag tank = new CompoundTag();
            if (!fluid.isEmpty()) {
                tank.put("Fluid", fluid);
            }
            data.put(currentKey, tank);
        } else if (!hasCurrent && original.contains("Fluid", Tag.TAG_COMPOUND)) {
            data.put(currentKey, original);
        }
    }

    private static CompoundTag migrateFluid(CompoundTag old, boolean isSteam,
            CompoundTag backup, String path) {
        if (old.contains("id", Tag.TAG_STRING) || !old.contains("FluidName", Tag.TAG_STRING)) {
            return null;
        }
        String originalFluid = old.getString("FluidName");
        String fluidName = STEAM_FLUIDS.getOrDefault(originalFluid, originalFluid);
        int amount = old.getInt("Amount");
        ResourceLocation id = ResourceLocation.tryParse(fluidName);
        if (isSteam && fluidName.equals("mekanism:steam")) {
            id = ResourceLocation.parse("steam_letters:steam");
        }
        if (amount <= 0) {
            return new CompoundTag();
        }
        if (id == null || !BuiltInRegistries.FLUID.containsKey(id)) {
            backup.put(path, old.copy());
            return new CompoundTag();
        }
        if (old.contains("Tag", Tag.TAG_COMPOUND) && !old.getCompound("Tag").isEmpty()) {
            backup.put(path, old.copy());
        }
        CompoundTag fluid = new CompoundTag();
        fluid.putString("id", id.toString());
        fluid.putInt("amount", amount);
        return fluid;
    }
}
