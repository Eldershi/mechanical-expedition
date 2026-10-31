// priority: -99
// 仅合并教程书；保留模组原有的页面解锁条件。
const ExpeditionTome = Java.loadClass('website.eccentric.tome.Tome')
const ExpeditionBookRegistry = Java.loadClass('vazkii.patchouli.common.book.BookRegistry')
const ExpeditionResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
const ExpeditionGuideItemStack = Java.loadClass('net.minecraft.world.item.ItemStack')
const ExpeditionStartingCursedRing = Java.loadClass('com.aizistral.enigmaticlegacy.items.CursedRing')
// Apply native options on script reload as well, so an active server need not restart.
ExpeditionStartingCursedRing.autoEquip.setValue(true)
ExpeditionStartingCursedRing.ultraHardcore.setValue(true)
const expeditionGuideCatalog = [{"id": "ftbquests:book"}, {"id": "ae2:guide"}, {"id": "immersiveengineering:manual"}, {"id": "tconstruct:materials_and_you"}, {"id": "tconstruct:puny_smelting"}, {"id": "tconstruct:mighty_smelting"}, {"id": "tconstruct:tinkers_gadgetry"}, {"id": "tconstruct:fantastic_foundry"}, {"id": "tconstruct:encyclopedia"}, {"id": "alexscaves:cave_book"}, {"id": "edenring:guide_book"}, {"id": "aether:book_of_lore"}, {"id": "botania:lexicon"}, {"id": "ars_nouveau:worn_notebook"}, {"id": "eidolon:codex"}, {"id": "enigmaticlegacy:the_acknowledgment"}, {"id": "malum:encyclopedia_arcana"}, {"id": "legendary_monsters:guide_book"}, {"id": "eternal_starlight:book"}, {"id": "solcarrot:food_book"}, {"id": "patchouli:guide_book", "nbt": {"patchouli:book": "apotheosis:apoth_chronicle"}}, {"id": "patchouli:guide_book", "nbt": {"patchouli:book": "enderio:guide"}}, {"id": "patchouli:guide_book", "nbt": {"patchouli:book": "ad_astra:astrodux"}}, {"id": "patchouli:guide_book", "nbt": {"patchouli:book": "allthemodium:allthemodium_book"}}, {"id": "patchouli:guide_book", "nbt": {"patchouli:book": "irons_spellbooks:iss_guide_book"}}, {"id": "patchouli:guide_book", "nbt": {"patchouli:book": "l2hostility:hostility_guide"}}, {"id": "patchouli:guide_book", "nbt": {"patchouli:book": "terramity:terramity_guidebook"}}, {"id": "patchouli:guide_book", "nbt": {"patchouli:book": "touhou_little_maid:memorizable_gensokyo"}}, {"id": "patchouli:guide_book", "nbt": {"patchouli:book": "thermal:guidebook"}}]
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
