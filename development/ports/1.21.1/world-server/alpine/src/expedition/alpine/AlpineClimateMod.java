package expedition.alpine;

import net.minecraft.core.registries.Registries;
import net.minecraft.world.level.levelgen.placement.PlacementModifierType;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.level.LevelEvent;
import net.neoforged.fml.common.Mod;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.neoforged.neoforge.registries.DeferredHolder;

@Mod(AlpineClimateMod.ID)
public final class AlpineClimateMod {
    public static final String ID="expedition_alpine_climate";
    private static final DeferredRegister<PlacementModifierType<?>> PLACEMENTS=DeferredRegister.create(Registries.PLACEMENT_MODIFIER_TYPE,ID);
    public static final DeferredHolder<PlacementModifierType<?>, PlacementModifierType<AlpineTreePlacement>> TREE=PLACEMENTS.register("alpine_treeline",()->()->AlpineTreePlacement.CODEC);
    public AlpineClimateMod(IEventBus modBus){
        PLACEMENTS.register(modBus);
        NeoForge.EVENT_BUS.addListener((LevelEvent.Load event)->ClimateRules.loaded(event.getLevel()));
    }
}
