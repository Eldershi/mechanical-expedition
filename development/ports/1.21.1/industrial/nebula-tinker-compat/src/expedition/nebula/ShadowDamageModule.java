package expedition.nebula;

import java.util.List;
import modernmods.hilt.data.loadable.record.RecordLoadable;
import modernmods.hilt.data.loadable.record.SingletonLoader;
import modernmods.modernfoundry.library.modifiers.ModifierEntry;
import modernmods.modernfoundry.library.modifiers.ModifierHooks;
import modernmods.modernfoundry.library.modifiers.hook.combat.MeleeHitModifierHook;
import modernmods.modernfoundry.library.modifiers.hook.ranged.ProjectileHitModifierHook;
import modernmods.modernfoundry.library.modifiers.modules.ModifierModule;
import modernmods.modernfoundry.library.module.ModuleHook;
import modernmods.modernfoundry.library.tools.context.ToolAttackContext;
import modernmods.modernfoundry.library.tools.nbt.IToolStackView;
import modernmods.modernfoundry.library.tools.nbt.ModDataNBT;
import modernmods.modernfoundry.library.tools.nbt.ModifierNBT;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraft.world.phys.EntityHitResult;

record ShadowDamageModule(RecordLoadable<ShadowDamageModule> getLoader)
        implements ModifierModule, MeleeHitModifierHook, ProjectileHitModifierHook {
    private static final ShadowDamageModule INSTANCE = SingletonLoader.singleton(ShadowDamageModule::new);
    static final RecordLoadable<ShadowDamageModule> LOADER = INSTANCE.getLoader();
    private static final List<ModuleHook<?>> HOOKS = List.of(ModifierHooks.MELEE_HIT, ModifierHooks.PROJECTILE_HIT);

    @Override
    public List<ModuleHook<?>> getDefaultHooks() {
        return HOOKS;
    }

    @Override
    public void afterMeleeHit(IToolStackView tool, ModifierEntry modifier, ToolAttackContext context,
                              float dealtDamage) {
        if (dealtDamage > 0) {
            hurt(context.getLivingTarget(), modifier.getLevel());
        }
    }

    @Override
    public boolean onProjectileHitEntity(ModifierNBT modifiers, ModDataNBT data, ModifierEntry modifier,
                                        Projectile projectile, EntityHitResult hit, LivingEntity attacker,
                                        LivingEntity target, boolean primaryTarget) {
        hurt(target, modifier.getLevel());
        return false;
    }

    private static void hurt(LivingEntity target, int level) {
        if (target != null && !target.level().isClientSide() && target.isAlive()) {
            int invulnerability = target.invulnerableTime;
            target.invulnerableTime = 0;
            target.hurt(target.damageSources().fellOutOfWorld(), 1F + level);
            target.invulnerableTime = invulnerability;
        }
    }
}
