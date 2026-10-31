"""Build a conservative catalogue of guidebooks from installed mod resources."""
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INSTANCE = ROOT / 'instance'
# Deliberately retired content must not return if historical JARs are staged here.
REMOVED_CONTENT_MODS = {'goety', 'goety_revelation', 'iceandfire', 'livingthings', 'mowziesmobs'}
direct = [
    'ftbquests:book', 'ae2:guide', 'immersiveengineering:manual',
    'tconstruct:materials_and_you', 'tconstruct:puny_smelting',
    'tconstruct:mighty_smelting', 'tconstruct:tinkers_gadgetry',
    'tconstruct:fantastic_foundry', 'tconstruct:encyclopedia',
    'alexscaves:cave_book', 'edenring:guide_book', 'aether:book_of_lore',
    'botania:lexicon', 'ars_nouveau:worn_notebook', 'eidolon:codex',
    'enigmaticlegacy:the_acknowledgment', 'malum:encyclopedia_arcana',
    'legendary_monsters:guide_book',
    'eternal_starlight:book', 'solcarrot:food_book',
]
books = [{'id': item} for item in direct]
for jar in sorted((INSTANCE / 'mods').glob('*.jar')):
    with zipfile.ZipFile(jar) as z:
        for name in z.namelist():
            parts = name.split('/')
            if len(parts) != 5 or parts[0] != 'data' or parts[2] != 'patchouli_books' or parts[4] != 'book.json':
                continue
            if parts[1] in REMOVED_CONTENT_MODS:
                continue
            data = json.loads(z.read(name))
            if data.get('dont_generate_book') or data.get('extend'):
                continue
            books.append({'id': 'patchouli:guide_book', 'nbt': {'patchouli:book': parts[1] + ':' + parts[3]}})
# Thermal registers this book in code instead of shipping a book.json.
books.append({'id': 'patchouli:guide_book', 'nbt': {'patchouli:book': 'thermal:guidebook'}})
data_path = INSTANCE / 'kubejs/guide-tome-catalog.json'
data_path.write_text(json.dumps(books, ensure_ascii=False, indent=2) + '\n')
script = '''// priority: -99
// 仅合并教程书；保留模组原有的页面解锁条件。
const ExpeditionTome = Java.loadClass('website.eccentric.tome.Tome')
const ExpeditionBookRegistry = Java.loadClass('vazkii.patchouli.common.book.BookRegistry')
const ExpeditionResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
const ExpeditionGuideItemStack = Java.loadClass('net.minecraft.world.item.ItemStack')
const ExpeditionStartingCursedRing = Java.loadClass('com.aizistral.enigmaticlegacy.items.CursedRing')
// Apply native options on script reload as well, so an active server need not restart.
ExpeditionStartingCursedRing.autoEquip.setValue(true)
ExpeditionStartingCursedRing.ultraHardcore.setValue(true)
const expeditionGuideCatalog = __GUIDE_CATALOG__
function expeditionGuideStacks() {
  let books = []
  expeditionGuideCatalog.forEach(row => {
    if (!Item.exists(row.id)) throw new Error('Guide item missing: ' + row.id)
    if (row.nbt && row.nbt['patchouli:book']) {
      let bookId = new ExpeditionResourceLocation(row.nbt['patchouli:book'])
      if (!ExpeditionBookRegistry.INSTANCE.books.containsKey(bookId)) throw new Error('Patchouli guide missing: ' + bookId)
    }
    books.push(row.nbt ? Item.of(row.id, row.nbt) : Item.of(row.id))
  })
  return books
}
function expeditionFullGuideTome() {
  let tome = Item.of('eccentrictome:tome')
  expeditionGuideStacks().forEach(book => ExpeditionTome.attach(tome, book))
  return tome
}
function expeditionConsolidateStarterGuides(player) {
  let inventory = player.getInventory()
  let hasFullTome = false
  for (let slot = 0; slot < inventory.getContainerSize(); slot++) {
    let stack = inventory.getItem(slot)
    if (String(stack.id) === 'eccentrictome:tome' && ExpeditionTome.getItemCount(stack) >= expeditionGuideCatalog.length) hasFullTome = true
  }
  if (!hasFullTome) return { safe: false, removed: 0 }
  let guides = expeditionGuideStacks()
  let removed = 0
  for (let slot = 0; slot < inventory.getContainerSize(); slot++) {
    let stack = inventory.getItem(slot)
    // Exact item + NBT matching preserves renamed, annotated and other custom books.
    if (!stack.isEmpty() && guides.some(book => ExpeditionGuideItemStack.isSameItemSameTags(stack, book))) {
      removed += stack.getCount()
      stack.setCount(0)
    }
  }
  inventory.setChanged()
  return { safe: true, removed: removed }
}
ServerEvents.recipes(event => {
  // Keep the mod's attachment recipe; replace only its empty-tome recipe.
  event.remove({id: 'eccentrictome:tome'})
  event.shapeless(expeditionFullGuideTome(), ['minecraft:book', '#forge:bookshelves']).id('eccentrictome:tome')
})
function expeditionQueueStarterGuideCleanup(player, server) {
  if (player.persistentData.expeditionStarterGuidesConsolidatedV1) return
  let removed = 0
  // Other mods grant their books at different login phases; consolidate once per player.
  ;[20, 100, 200].forEach(delay => server.scheduleInTicks(delay, () => {
    if (!player.isAlive() || player.isRemoved()) return
    let result = expeditionConsolidateStarterGuides(player)
    removed += result.removed
    if (delay === 200 && result.safe) {
      player.persistentData.expeditionStarterGuidesConsolidatedV1 = true
      player.persistentData.expeditionStarterGuidesRemoved = removed
      if (removed > 0) player.tell('已收起重复的开局教程书，内容均可从怪奇宝典打开。')
    }
  }))
}
PlayerEvents.loggedIn(event => {
  let player = event.player
  if (!player.persistentData.expeditionGuideTomeGiven) {
    player.give(expeditionFullGuideTome())
    player.persistentData.expeditionGuideTomeGiven = true
    player.tell('教程已收进怪奇宝典：右键选书，左键点空气返回；书＋书架可补领。')
  }
  expeditionQueueStarterGuideCleanup(player, event.server)
})
let expeditionGuideOnlineMigrationDone = false
ServerEvents.tick(event => {
  if (expeditionGuideOnlineMigrationDone) return
  expeditionGuideOnlineMigrationDone = true
  event.server.getPlayerList().getPlayers().forEach(player => expeditionQueueStarterGuideCleanup(player, event.server))
})
ServerEvents.loaded(event => {
  let tome = expeditionFullGuideTome()
  let expected = expeditionGuideStacks()
  let failures = []
  expected.forEach((book, i) => {
    let converted = ExpeditionTome.convert(tome.copy(), i)
    if (String(converted.id) !== String(book.id)) failures.push('convert:' + i)
    if (book.nbt && book.nbt['patchouli:book'] && String(converted.nbt['patchouli:book']) !== String(book.nbt['patchouli:book'])) failures.push('book-nbt:' + i)
    let restored = ExpeditionTome.revert(converted)
    // Match the mod's RevertMessage handler: put the active book back after reverting.
    ExpeditionTome.attach(restored, converted)
    if (ExpeditionTome.getItemCount(restored) !== expected.length) failures.push('revert:' + i)
  })
  let recipe = event.server.getRecipeManager().byKey(new ExpeditionResourceLocation('eccentrictome:tome'))
  if (!recipe.isPresent()) failures.push('crafting recipe missing')
  else if (ExpeditionTome.getItemCount(recipe.get().getResultItem(event.server.registryAccess())) !== expected.length) failures.push('crafting recipe book count')
  let ExpeditionTomeExportDirectory = Java.loadClass('java.io.File')
  new ExpeditionTomeExportDirectory('kubejs/exported').mkdirs()
  JsonIO.write('kubejs/exported/guide-tome-audit.json', {
    bookCount: ExpeditionTome.getItemCount(tome), books: expeditionGuideCatalog,
    roundTripFailures: failures, passed: failures.length === 0,
    scope: 'Registered guidebooks, native Tome conversion/reversion, and crafting recipe; page text and every GUI not exhaustively checked.'
  })
  console.info('[Guide Tome] books=' + expected.length + ', failures=' + failures.length)
})
'''.replace('__GUIDE_CATALOG__', json.dumps(books, ensure_ascii=False))
(INSTANCE / 'kubejs/server_scripts/expedition/GuideTome.js').write_text(script)
print(json.dumps({'catalog':str(data_path), 'books':len(books)}, ensure_ascii=False))
