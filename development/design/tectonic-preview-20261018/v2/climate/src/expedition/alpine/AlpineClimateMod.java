package expedition.alpine;

import net.minecraft.core.registries.Registries;
import net.minecraft.world.level.levelgen.placement.PlacementModifierType;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.fml.javafmlmod.FMLJavaModLoadingContext;
import net.minecraftforge.registries.DeferredRegister;
import net.minecraftforge.registries.RegistryObject;

@Mod(AlpineClimateMod.ID)
public final class AlpineClimateMod {
    public static final String ID="expedition_alpine_climate";
    private static final DeferredRegister<PlacementModifierType<?>> PLACEMENTS=DeferredRegister.create(Registries.f_256843_,ID);
    public static final RegistryObject<PlacementModifierType<AlpineTreePlacement>> TREE=PLACEMENTS.register("alpine_treeline",()->()->AlpineTreePlacement.CODEC);
    public AlpineClimateMod(){
        PLACEMENTS.register(FMLJavaModLoadingContext.get().getModEventBus());
        MinecraftForge.EVENT_BUS.addListener((LevelEvent.Load event)->ClimateRules.loaded(event.getLevel()));
    }
}
