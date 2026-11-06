package expedition.terramitycompat.tests;

import com.aizistral.enigmaticlegacy.handlers.SuperpositionHandler;
import com.aizistral.enigmaticlegacy.registries.EnigmaticItems;
import com.mojang.authlib.GameProfile;
import expedition.terramitycompat.TerramityCurseCompat;
import java.lang.reflect.Field;
import java.util.*;
import net.minecraft.core.BlockPos;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.players.PlayerList;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.entity.*;
import net.minecraft.world.entity.monster.Zombie;
import net.minecraft.world.item.ItemStack;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.common.util.FakePlayerFactory;
import net.minecraftforge.event.entity.living.*;
import net.minecraftforge.event.server.ServerStartedEvent;
import net.minecraftforge.eventbus.api.*;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.registries.ForgeRegistries;
import net.mcreator.terramity.init.TerramityModMobEffects;
import net.mcreator.terramity.procedures.NyxiumFireOnEffectActiveTickProcedure;
import top.theillusivec4.curios.api.CuriosApi;

/** Runs only in a disposable full-modpack validation server. */
@Mod("expedition_terramity_runtime_probe")
public final class RuntimeVerification {
    private LivingEntity target;
    private boolean verified;
    private int ticks;
    private float last;
    private net.minecraft.world.damagesource.DamageSource source;
    public RuntimeVerification() {
        MinecraftForge.EVENT_BUS.addListener(this::tick);
        MinecraftForge.EVENT_BUS.addListener(EventPriority.LOWEST,this::hurt);
    }
    private void hurt(LivingHurtEvent event) {if(event.getEntity()==target){last=event.getAmount();source=event.getSource();}}
    private static void check(boolean value,String message) {if(!value)throw new AssertionError(message);}
    private static void near(float got,float expected,String message) {check(Math.abs(got-expected)<0.001F,message+": "+got+" != "+expected);}
    private void tick(net.minecraftforge.event.TickEvent.ServerTickEvent event) {
        if(event.phase==net.minecraftforge.event.TickEvent.Phase.END && !verified && ++ticks>=5) {verified=true;started(event.getServer());}
    }
    private float burn(LivingEntity entity) {
        var pos=entity.m_9236_().m_220360_();entity.m_6034_(pos.m_123341_()+0.5,pos.m_123342_()+2,pos.m_123343_()+0.5);
        target=entity;last=-1;source=null;entity.f_19802_=0;entity.m_21153_(20F);
        NyxiumFireOnEffectActiveTickProcedure.execute(entity.m_9236_(),entity);
        return last;
    }
    @SuppressWarnings("unchecked")
    private void started(net.minecraft.server.MinecraftServer server) {
        var level=server.m_129783_();
        Map<UUID,ServerPlayer> map=null;ServerPlayer player=null;
        try {
            player=FakePlayerFactory.get(level,new GameProfile(UUID.nameUUIDFromBytes("TerramityCurseValidation".getBytes()),"CurseValidation"));
            var spawn=level.m_220360_();player.m_6034_(spawn.m_123341_()+0.5,spawn.m_123342_()+2,spawn.m_123343_()+0.5);
            Field f=PlayerList.class.getDeclaredField("f_11197_");f.setAccessible(true);map=(Map<UUID,ServerPlayer>)f.get(server.m_6846_());map.put(player.m_20148_(),player);
            var curios=CuriosApi.getCuriosInventory(player).resolve().orElseThrow();
            System.out.println("TERRAMITY_TEST_SLOTS "+curios.getCurios().keySet());
            curios.setEquippedCurio("ring",0,new ItemStack(EnigmaticItems.CURSED_RING));
            check(SuperpositionHandler.isTheCursedOne(player),"Cursed ring equipped");
            var effect=TerramityModMobEffects.NYXIUM_FIRE.get();
            for(String sword:List.of("forbidden_oathblade","exalted_oathblade","devils_devastation")) {
                Zombie zombie=new Zombie(level);ItemStack stack=new ItemStack(ForgeRegistries.ITEMS.getValue(new ResourceLocation("lethality",sword)));
                stack.m_41720_().m_7579_(stack,zombie,player);
                check(zombie.m_21023_(effect),sword+" applies shadowflame");
                near(burn(zombie),1.5F,sword+" curse damage");
                check(source.m_7639_()==player && source.m_7640_()==null,"Attributed periodic source");
                System.out.println("TERRAMITY_TEST_SWORD_OK "+sword+" damage="+last);
            }
            Zombie zombie=new Zombie(level);
            var arrow=new net.minecraft.world.entity.projectile.Arrow(level,player);
            zombie.m_147207_(new MobEffectInstance(effect,200,0),arrow);
            near(burn(zombie),1.5F,"Projectile owner");
            player.m_8061_(EquipmentSlot.MAINHAND,new ItemStack(EnigmaticItems.THE_TWIST));
            near(burn(zombie),1.5F,"Switch to exempt melee weapon");
            map.remove(player.m_20148_());near(burn(zombie),1.5F,"Offline applier fallback");map.put(player.m_20148_(),player);
            zombie.m_21195_(effect);check(!((net.minecraftforge.common.extensions.IForgeEntity)zombie).getPersistentData().m_128403_("expedition_shadowflame_owner"),"Cleanup after removal");
            zombie.m_7292_(new MobEffectInstance(effect,200,0));near(burn(zombie),3F,"Anonymous fire clears stale ownership");
            var cow=new net.minecraft.world.entity.animal.Cow(EntityType.f_20557_,level);
            cow.m_147207_(new MobEffectInstance(effect,200,0),player);near(burn(cow),3F,"Passive target retains native ring semantics");
            curios.setEquippedCurio("ring",0,ItemStack.f_41583_);
            zombie.m_147207_(new MobEffectInstance(effect,200,0),player);near(burn(zombie),3F,"Uncursed applier");
            for(String id:List.of("blue_fairy","green_fairy","pink_fairy","cave_gnome","royal_gnome")) {
                var type=ForgeRegistries.ENTITY_TYPES.getValue(new ResourceLocation("terramity",id));
                for(MobSpawnType reason:List.of(MobSpawnType.NATURAL,MobSpawnType.CHUNK_GENERATION,MobSpawnType.SPAWN_EGG,MobSpawnType.COMMAND,MobSpawnType.STRUCTURE)) {
                    var e=new MobSpawnEvent.SpawnPlacementCheck(type,level,reason,BlockPos.f_121853_,level.m_213780_(),true);MinecraftForge.EVENT_BUS.post(e);
                    check((e.getResult()==Event.Result.DENY)==(reason==MobSpawnType.NATURAL||reason==MobSpawnType.CHUNK_GENERATION),id+" spawn "+reason);
                }
            }
            var receiver=FakePlayerFactory.get(level,new GameProfile(UUID.nameUUIDFromBytes("CurseReceiver".getBytes()),"CurseReceiver"));
            CuriosApi.getCuriosInventory(receiver).resolve().orElseThrow().setEquippedCurio("ring",0,new ItemStack(EnigmaticItems.CURSED_RING));
            target=receiver;last=-1;
            var pain=new LivingHurtEvent(receiver,source,3F);
            new com.aizistral.enigmaticlegacy.handlers.EnigmaticEventHandler().onEntityHurt(pain);
            near(pain.getAmount(),6F,"Native cursed victim pain handler");
            Class<?> poolType=Class.forName("com.github.goddamnrepackager.SharedPackagePool");
            Class<?> bigType=Class.forName("com.simibubi.create.content.logistics.BigItemStack");
            Object pool=poolType.getConstructor().newInstance();UUID vault=UUID.randomUUID();
            var payload=new ItemStack(ForgeRegistries.ITEMS.getValue(new ResourceLocation("minecraft","stone")));
            Object batch=bigType.getConstructor(ItemStack.class,int.class).newInstance(payload,3);
            poolType.getMethod("deposit",UUID.class,List.class).invoke(pool,vault,List.of(batch));
            for(int consumer=0;consumer<3;consumer++) {
                Object packet=poolType.getMethod("poll",UUID.class).invoke(pool,vault);
                check(packet!=null && bigType.getField("count").getInt(packet)==1,"Shared pool consumer "+consumer);
            }
            check(poolType.getMethod("poll",UUID.class).invoke(pool,vault)==null,"No duplicate shared package");
            Class.forName("com.simibubi.create.content.logistics.packager.repackager.RepackagerBlockEntity");
            System.out.println("TERRAMITY_RUNTIME_VERIFICATION_OK swords=3 projectile-owner offline-fallback weapon-switch effect-cleanup anonymous-fire passive-target uncursed-owner spawn-rules=25 repackager-mixin-loaded shared-pool-conservation cursed-victim-pain");
        } catch(Throwable failure) {System.out.println("TERRAMITY_RUNTIME_VERIFICATION_FAILED");failure.printStackTrace();}
        finally {if(map!=null&&player!=null)map.remove(player.m_20148_());target=null;}
    }
}
