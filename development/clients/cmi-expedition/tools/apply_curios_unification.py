"""Apply the Expedition equipment layout to the client, server and reusable overlay."""
from datetime import datetime
from pathlib import Path
import hashlib
import json
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
EVIDENCE = ROOT / 'evidence/curios-unification-20261017'
TARGETS = [ROOT / 'instance', ROOT / 'overlay', PROJECT / 'servers/cmi-expedition/instance']
SLOTS = {
    'back': 1, 'backpack': 1, 'belt': 2, 'body': 1, 'bracelet': 2,
    'charm': 5, 'curio': 5, 'hands': 2, 'head': 1, 'necklace': 3,
    'ring': 10, 'mechanisms': 1,
    'hostility_curse': 1, 'an_focus': 1, 'bundle': 1, 'feet': 1,
    'spellbook': 1, 'adv_pattern_encoder': 1, 'brooch': 1,
    'deep_learner': 1, 'pouch': 1, 'tiab': 1,
    'rings': 0, 'waist': 0, 'aether_accessory': 0, 'aether_cape': 0,
    'aether_gloves': 0, 'aether_pendant': 0, 'aether_ring': 0, 'aether_shield': 0,
    # Preserve the original progression/equipment unlocks for these four types.
    'talisman': 0, 'rune': 0, 'scroll': 0, 'spellstone': 0,
}
BACKPACKS = ['sophisticatedbackpacks:' + name for name in (
    'backpack', 'copper_backpack', 'iron_backpack', 'gold_backpack',
    'diamond_backpack', 'netherite_backpack')]

STARTUP = '''// Full client/server restart required: native listeners and item registration.
// Keep the dedicated backpack position strict, including Curios' generic-curio fallback.
const ExpeditionEquipmentApi = Java.loadClass('top.theillusivec4.curios.api.CuriosApi')
const ExpeditionEquipmentLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
const ExpeditionEquipmentResult = Java.loadClass('net.minecraftforge.eventbus.api.Event$Result')
const ExpeditionCatItems = Java.loadClass('com.github.L_Ender.cataclysm.init.ModItems')
const ExpeditionCatAttributes = Java.loadClass('com.github.L_Ender.cataclysm.init.ModAttribute')
const ExpeditionCatAttributeContainer = Java.loadClass('com.github.L_Ender.cataclysm.items.CuriosItem.AttributeContainer')
const ExpeditionEquipmentOperation = Java.loadClass('net.minecraft.world.entity.ai.attributes.AttributeModifier$Operation')
const ExpeditionEquipmentSlotAttribute = Java.loadClass('top.theillusivec4.curios.api.SlotAttribute')
const expeditionBackpackTag = 'expedition:backpacks'
const expeditionAetherShieldTag = 'aether:accessories_shields'
const expeditionAetherMiscTag = 'aether:accessories_miscellaneous'
const expeditionGenericCurioTag = 'curios:curio'
const expeditionTypedEquipmentTags = {}
;['back', 'backpack', 'belt', 'body', 'bracelet', 'charm', 'hands', 'head', 'necklace',
  'ring', 'mechanisms', 'hostility_curse', 'an_focus', 'bundle', 'feet', 'spellbook',
  'adv_pattern_encoder', 'brooch', 'deep_learner', 'pouch', 'tiab',
  'talisman', 'rune', 'scroll', 'spellstone'].forEach(slot => {
  expeditionTypedEquipmentTags[slot] = 'curios:' + slot
})
function expeditionEquipmentHasTag(stack, tag) {
  // Avoid ItemStack.is(TagKey)/is(Item), which share an SRG name in KubeJS 2001.
  return Ingredient.of('#' + tag).test(stack)
}

StartupEvents.init(() => {
  ExpeditionEquipmentApi.registerCurioPredicate(new ExpeditionEquipmentLocation('expedition:backpack'), result => {
    return expeditionEquipmentHasTag(result.stack(), expeditionBackpackTag)
  })
})

StartupEvents.postInit(() => {
  // Cataclysm checks the identifier before supplying this ring's native attribute.
  ExpeditionCatItems.RING_OF_GRUDGED.get().withAttributes('ring',
    new ExpeditionCatAttributeContainer(ExpeditionCatAttributes.ADDITIONAL_CRITICAL_DAMAGE.get(),
      10, ExpeditionEquipmentOperation.ADDITION))
})

global.expeditionEquipmentAllowed = (slot, stack) => {
  let backpack = expeditionEquipmentHasTag(stack, expeditionBackpackTag)
  // Curios normally accepts any tagged equipment in curio, and curio-tagged items
  // in every other type. Enforce the pack's explicit, separate equipment budgets.
  let validType = slot === 'curio'
    ? expeditionEquipmentHasTag(stack, expeditionGenericCurioTag) && !Object.keys(expeditionTypedEquipmentTags)
      .some(type => expeditionEquipmentHasTag(stack, expeditionTypedEquipmentTags[type]))
    : expeditionTypedEquipmentTags[slot] && expeditionEquipmentHasTag(stack, expeditionTypedEquipmentTags[slot])
  if ((slot === 'backpack' && !backpack) || (backpack && slot !== 'backpack') ||
      expeditionEquipmentHasTag(stack, expeditionAetherShieldTag) ||
      (expeditionEquipmentHasTag(stack, expeditionAetherMiscTag) && slot !== 'curio') || !validType) {
    return false
  }
  return true
}

ForgeEvents.onEvent('top.theillusivec4.curios.api.event.CurioEquipEvent', event => {
  if (!global.expeditionEquipmentAllowed(String(event.getSlotContext().identifier()), event.getStack()))
    event.setResult(ExpeditionEquipmentResult.DENY)
})

ForgeEvents.onEvent('top.theillusivec4.curios.api.event.CurioAttributeModifierEvent', event => {
  // Fix the requested capacities while preserving the four original unlock systems.
  let remove = []
  event.getModifiers().keySet().forEach(attribute => {
    if (attribute instanceof ExpeditionEquipmentSlotAttribute &&
        ['talisman', 'rune', 'scroll', 'spellstone'].indexOf(String(attribute.getIdentifier())) < 0)
      remove.push(attribute)
  })
  remove.forEach(attribute => event.removeAttribute(attribute))
})
'''

MIGRATION = '''// Reconcile retained items once; Curios itself returns removed/overflow slots.
const ExpeditionEquipmentMigrationApi = Java.loadClass('top.theillusivec4.curios.api.CuriosApi')
function expeditionReconcileEquipment(player) {
  let optional = ExpeditionEquipmentMigrationApi.getCuriosInventory(player).resolve()
  if (!optional.isPresent()) return {moved: 0, returned: 0}
  let inventory = optional.get()
  inventory.getCurios().forEach((name, handler) => {
    if (['talisman', 'rune', 'scroll', 'spellstone'].indexOf(String(name)) < 0) {
      // Discard saved capacity bonuses from equipment worn before this layout.
      // Curios returns any stacks displaced by the resulting shrink.
      handler.clearModifiers()
      handler.clearCachedModifiers()
      handler.update()
    }
  })
  let pending = []
  inventory.getCurios().forEach((name, handler) => {
    let slot = String(name)
    function collect(stacks, cosmetic) {
      for (let i = 0; i < stacks.getSlots(); i++) {
        let stack = stacks.getStackInSlot(i)
        // Type checks avoid falsely unequipping unique items which are already worn.
        if (!stack.isEmpty() && !global.expeditionEquipmentAllowed(slot, stack)) {
          pending.push({stack: stack.copy(), cosmetic: cosmetic})
          stacks.setStackInSlot(i, Item.of('minecraft:air'))
        }
      }
    }
    collect(handler.getStacks(), false)
    if (handler.hasCosmetic()) collect(handler.getCosmeticStacks(), true)
  })
  let result = {moved: 0, returned: 0}
  pending.forEach(row => {
    let remainder = row.stack
    inventory.getCurios().forEach((name, handler) => {
      if (remainder.isEmpty() || !global.expeditionEquipmentAllowed(String(name), remainder) ||
          (row.cosmetic && !handler.hasCosmetic())) return
      let stacks = row.cosmetic ? handler.getCosmeticStacks() : handler.getStacks()
      for (let i = 0; i < stacks.getSlots() && !remainder.isEmpty(); i++) {
        if (stacks.getStackInSlot(i).isEmpty() && stacks.isItemValid(i, remainder))
          remainder = stacks.insertItem(i, remainder, false)
      }
    })
    if (remainder.isEmpty()) result.moved++
    else {
      inventory.loseInvalidStack(remainder)
      result.returned++
    }
  })
  inventory.handleInvalidStacks()
  return result
}
global.expeditionReconcileEquipment = expeditionReconcileEquipment
PlayerEvents.loggedIn(event => {
  let player = event.player
  if (player.persistentData.expeditionEquipmentLayoutV1) return
  event.server.scheduleInTicks(2, () => {
    if (player.isRemoved()) return
    let result = expeditionReconcileEquipment(player)
    player.persistentData.expeditionEquipmentLayoutV1 = true
    if (result.moved || result.returned)
      player.tell('装备栏已整理：调整 ' + result.moved + ' 件，退回 ' + result.returned + ' 件。')
  })
})
'''

TAGS = '''// priority: -200
// Apply after the upstream tags; retain unrelated accessories from every mod.
ServerEvents.tags('item', event => {
  event.get('curios:belt').add('#curios:waist')
  event.get('curios:ring').add('#curios:rings').add('#aether:accessories_rings')
  event.get('curios:hands').add('#aether:accessories_gloves')
  event.get('curios:necklace').add('#aether:accessories_pendants')
  event.get('curios:back').add('#aether:accessories_capes')
  event.get('curios:curio').add('#aether:accessories_miscellaneous')
  ;BACKPACKS.forEach(id => event.get('curios:back').remove(id))
  // Aether's official Curios pack defaults to charm/body; use the requested mapping.
  event.get('curios:charm').remove('#aether:accessories_miscellaneous')
  ;['aether:golden_feather', 'aether:regeneration_stone', 'aether:iron_bubble']
    .forEach(id => event.get('curios:charm').remove(id))
  event.get('curios:body').remove('#aether:accessories_shields').remove('aether:shield_of_repulsion')
})
'''.replace('BACKPACKS', json.dumps(BACKPACKS))


def as_json(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    files = {}
    files['config/curios-common.toml'] = (
        '# Expedition: exact base capacities; SET also clears legacy ADD contributions.\n'
        '# Conditional rune/scroll/spellstone/talisman unlocks remain native.\nslots = [\n' +
        ',\n'.join('    "id=%s;size=%d;operation=SET"' % row for row in SLOTS.items()) + '\n]\n')
    files['kubejs/startup_scripts/expedition/EquipmentCompatibility.js'] = STARTUP
    files['kubejs/server_scripts/expedition/EquipmentTags.js'] = TAGS
    files['kubejs/server_scripts/expedition/EquipmentMigration.js'] = MIGRATION
    files['kubejs/data/expedition/tags/items/backpacks.json'] = as_json({'replace': True, 'values': BACKPACKS})
    files['kubejs/data/curios/tags/items/backpack.json'] = as_json({'replace': True, 'values': ['#expedition:backpacks']})
    files['kubejs/data/expedition/curios/slots/backpack.json'] = as_json({
        'replace': True, 'size': 1, 'operation': 'SET', 'order': 41,
        'icon': 'curios:slot/empty_back_slot', 'use_native_gui': True,
        'add_cosmetic': False, 'render_toggle': True, 'validators': ['expedition:backpack']})
    files['kubejs/data/expedition/curios/entities/equipment.json'] = as_json({
        'entities': ['minecraft:player'], 'slots': ['backpack']})
    files['kubejs/assets/expedition/lang/zh_cn.json'] = as_json({'curios.identifier.backpack': '背包'})
    files['kubejs/assets/expedition/lang/en_us.json'] = as_json({'curios.identifier.backpack': 'Backpack'})
    # Remain disabled even for existing worlds with a different enabled-pack ordering.
    for slot in [key for key in SLOTS if key.startswith('aether_')]:
        files[f'kubejs/data/curios/tags/items/{slot}.json'] = as_json({'replace': True, 'values': []})
    aether = (ROOT / 'instance/config/aether-common.toml').read_text()
    assert '"Use default Curios\' menu"' in aether
    files['config/aether-common.toml'] = re.sub(
        r'("Use default Curios\' menu"\s*=\s*)(?:true|false)', r'\g<1>true', aether)

    stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    changes = []
    for target in TARGETS:
        for relative, content in files.items():
            path = target / relative
            blob = content.encode('utf-8')
            if path.is_file() and path.read_bytes() == blob:
                continue
            if path.exists():
                backup = EVIDENCE / 'backups' / stamp / target.relative_to(PROJECT) / relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blob)
            changes.append(str(path.relative_to(PROJECT)))
    # package_server.py gives deployment config precedence when it exists.
    for relative in ['config/curios-common.toml', 'config/aether-common.toml']:
        path = PROJECT / 'servers/cmi-expedition/deployment' / relative
        if path.is_file():
            backup = EVIDENCE / 'backups' / stamp / 'deployment' / relative
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, backup)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(files[relative])
    manifest = {'appliedAt': datetime.now().astimezone().isoformat(), 'slots': SLOTS,
                'baseFunctionalSlots': sum(SLOTS.values()), 'enabledTypes': sum(v > 0 for v in SLOTS.values()),
                'files': {name: hashlib.sha256(text.encode()).hexdigest() for name, text in files.items()},
                'changed': changes, 'backpacks': BACKPACKS, 'restartRequired': True}
    (EVIDENCE / 'implementation.json').write_text(as_json(manifest))
    print(as_json({'files': len(files), 'changed': len(changes), 'baseSlots': sum(SLOTS.values()),
                   'enabledTypes': manifest['enabledTypes']}))


if __name__ == '__main__':
    main()
