// priority: -99
// 收录已确认的教程书；保留各模组原有的页面解锁条件。
let ExpeditionTome = Java.loadClass('website.eccentric.tome.Tome')
let ExpeditionBookRegistry = Java.loadClass('vazkii.patchouli.common.book.BookRegistry')
let ExpeditionResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
let ExpeditionGuideItemStack = Java.loadClass('net.minecraft.world.item.ItemStack')
let ExpeditionGuideCompoundTag = Java.loadClass('net.minecraft.nbt.CompoundTag')
let ExpeditionGuideNbtOps = Java.loadClass('net.minecraft.nbt.NbtOps')
let ExpeditionGuideJsonOps = Java.loadClass('com.mojang.serialization.JsonOps')
let ExpeditionGuideRegistries = Java.loadClass('net.minecraftforge.registries.ForgeRegistries')
let ExpeditionStartingCursedRing = Java.loadClass('com.aizistral.enigmaticlegacy.items.CursedRing')
ExpeditionStartingCursedRing.autoEquip.setValue(true)
ExpeditionStartingCursedRing.ultraHardcore.setValue(true)
let expeditionGuideCatalog = JSON.parse(String(JsonIO.readJson('kubejs/guide-tome-catalog.json')))

function expeditionGuideStacks() {
  let books = []
  expeditionGuideCatalog.forEach(row => {
    if (!Item.exists(row.id)) throw new Error('Guide item missing: ' + row.id)
    let generated = null
    let guideId = null
    if (row.factory === 'scguns:mob_guide') {
      let helper = Java.loadClass('top.ribs.scguns.common.MobGuideHelper')
      let entity = ExpeditionGuideRegistries.ENTITY_TYPES.getValue(new ExpeditionResourceLocation(row.entity))
      if (entity == null) throw new Error('Guide entity missing: ' + row.entity)
      generated = helper.createGuideBook(entity)
      let definition = row.definition
      if (generated == null || generated.isEmpty()) {
        if (!definition || definition.id !== row.entity) throw new Error('Guide definition missing: ' + row.entity)
        generated = Item.of('minecraft:written_book', {
          title: String(Component.translatable(definition.title).getString()),
          author: String(Component.translatable(definition.title.replace('.title', '.author')).getString()),
          generation: 0,
          pages: definition.pages.map(page => JSON.stringify({ translate: page.text })),
          resolved: false
        })
      }
      if (definition) {
        generated.nbt.display = { Name: JSON.stringify({ translate: definition.title }) }
      }
      guideId = row.factory + '/' + row.entity
    } else if (row.factory === 'twilightforest:structure_hint') {
      let helper = Java.loadClass('twilightforest.world.components.structures.util.StructureHints$HintConfig')
      generated = helper.book(row.hint, row.pages)
      guideId = row.factory + '/' + row.hint
    } else if (row.factory === 'aquamirae:logbook') {
      let helper = Java.loadClass('com.obscuria.aquamirae.common.items.Logbook')
      generated = helper.valueOf(row.variant).get()
      guideId = row.factory + '/' + row.variant
    } else if (row.factory) {
      throw new Error('Unknown guide factory: ' + row.factory)
    }
    if (row.factory) {
      if (generated == null || generated.isEmpty()) throw new Error('Native guide missing: ' + guideId)
      generated.nbt['expedition:guide_id'] = guideId
      books.push(generated)
      return
    }
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

// A renamed or annotated copy still opens the same guide. Required variant NBT
// must match, while extra player data remains untouched.
function expeditionMatchesGuide(stack, guide) {
  if (String(stack.id) !== String(guide.id)) return false
  let required = expeditionGuideNbtData(guide)
  let actual = expeditionGuideNbtData(stack)
  if (String(guide.id) === 'minecraft:written_book') {
    if (actual['expedition:guide_id'] && required['expedition:guide_id']) {
      return actual['expedition:guide_id'] === required['expedition:guide_id']
    }
    // Vanilla resolves pages when a written book is opened. Stable native
    // identifiers distinguish the volumes even after page resolution.
    if (required['aquamirae:author'] && actual['aquamirae:author'] !== required['aquamirae:author']) return false
    return actual.title === required.title && actual.author === required.author
  }
  let keys = Object.keys(required)
  for (let index = 0; index < keys.length; index++) {
    let key = keys[index]
    if (expeditionGuideCanonicalJson(actual[key]) !== expeditionGuideCanonicalJson(required[key])) return false
  }
  return true
}

function expeditionSelectedGuide(tome) {
  if (String(tome.id) === 'eccentrictome:tome') return null
  let selected = tome.copy()
  // Native revert clears only this copy's Tome metadata and restores its name.
  // The actual selected item and every player-owned field stay in place.
  ExpeditionTome.revert(selected)
  return selected
}

function expeditionContainsGuide(tome, guide, selected) {
  if (selected != null && expeditionMatchesGuide(selected, guide)) return true
  let items = ExpeditionTome.getItems(tome)
  for (let index = 0; index < items.size(); index++) {
    if (expeditionMatchesGuide(items.get(index), guide)) return true
  }
  return false
}

function expeditionRefreshGuideTome(tome, guides) {
  if (!ExpeditionTome.isTome(tome)) return 0
  let selected = expeditionSelectedGuide(tome)
  let added = 0
  guides.forEach(guide => {
    if (!expeditionContainsGuide(tome, guide, selected)) {
      ExpeditionTome.attach(tome, guide)
      added++
    }
  })
  return added
}

function expeditionHasCompleteGuideTome(tome, guides) {
  if (!ExpeditionTome.isTome(tome)) return false
  let selected = expeditionSelectedGuide(tome)
  return guides.every(guide => expeditionContainsGuide(tome, guide, selected))
}

function expeditionRefreshPlayerGuideTomes(player, notify) {
  let guides = expeditionGuideStacks()
  let inventory = player.getInventory()
  let added = 0
  for (let slot = 0; slot < inventory.getContainerSize(); slot++) {
    added += expeditionRefreshGuideTome(inventory.getItem(slot), guides)
  }
  if (added > 0) {
    inventory.setChanged()
    if (notify) player.tell('怪奇宝典已补齐当前整合包的教程书，原有内容和当前选书均已保留。')
  }
  return added
}

function expeditionConsolidateStarterGuides(player) {
  let inventory = player.getInventory()
  let guides = expeditionGuideStacks()
  let hasFullTome = false
  for (let slot = 0; slot < inventory.getContainerSize(); slot++) {
    if (expeditionHasCompleteGuideTome(inventory.getItem(slot), guides)) hasFullTome = true
  }
  if (!hasFullTome) return { safe: false, removed: 0 }
  let removed = 0
  for (let slot = 0; slot < inventory.getContainerSize(); slot++) {
    let stack = inventory.getItem(slot)
    // Only the original one-time starter cleanup removes exact unmodified copies.
    if (!stack.isEmpty() && guides.some(book => ExpeditionGuideItemStack.isSameItemSameTags(stack, book))) {
      removed += stack.getCount()
      stack.setCount(0)
    }
  }
  inventory.setChanged()
  return { safe: true, removed: removed }
}

ServerEvents.recipes(event => {
  event.remove({ id: 'eccentrictome:tome' })
  event.shapeless(expeditionFullGuideTome(), ['minecraft:book', '#forge:bookshelves']).id('eccentrictome:tome')
})

function expeditionQueueStarterGuideCleanup(player, server) {
  if (player.persistentData.expeditionStarterGuidesConsolidatedV1) return
  let removed = 0
  ;[20, 100, 200].forEach(delay => server.scheduleInTicks(delay, () => {
    if (!player.isAlive() || player.isRemoved()) return
    expeditionRefreshPlayerGuideTomes(player, false)
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
  expeditionRefreshPlayerGuideTomes(player, true)
  expeditionQueueStarterGuideCleanup(player, event.server)
})

let expeditionGuideOnlineMigrationDone = false
let expeditionGuideRefreshTicks = 0
let expeditionGuideAuditDone = false
ServerEvents.tick(event => {
  if (!expeditionGuideOnlineMigrationDone) {
    expeditionGuideOnlineMigrationDone = true
    expeditionAuditGuideTome(event)
    event.server.getPlayerList().getPlayers().forEach(player => {
      expeditionRefreshPlayerGuideTomes(player, true)
      expeditionQueueStarterGuideCleanup(player, event.server)
    })
  }
  if (++expeditionGuideRefreshTicks < 200) return
  expeditionGuideRefreshTicks = 0
  event.server.getPlayerList().getPlayers().forEach(player => expeditionRefreshPlayerGuideTomes(player, false))
})

function expeditionGuideCanonicalJson(value) {
  if (value == null || typeof value !== 'object') return JSON.stringify(value)
  if (Array.isArray(value)) return '[' + value.map(expeditionGuideCanonicalJson).join(',') + ']'
  return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + expeditionGuideCanonicalJson(value[key])).join(',') + '}'
}

function expeditionGuideNbtData(stack) {
  if (stack.nbt == null) return {}
  return JSON.parse(String(ExpeditionGuideNbtOps.INSTANCE.convertTo(ExpeditionGuideJsonOps.INSTANCE, stack.nbt)))
}

function expeditionGuideSerializedData(stack) {
  return JSON.parse(String(ExpeditionGuideNbtOps.INSTANCE.convertTo(ExpeditionGuideJsonOps.INSTANCE,
    stack.save(new ExpeditionGuideCompoundTag()))))
}

function expeditionGuideStackState(stack) {
  return expeditionGuideCanonicalJson(expeditionGuideSerializedData(stack))
}

function expeditionGuideOuterState(stack) {
  let state = expeditionGuideSerializedData(stack)
  if (state.tag) delete state.tag['eccentrictome:items']
  return expeditionGuideCanonicalJson(state)
}

function expeditionAuditGuideTome(event) {
  if (expeditionGuideAuditDone) return
  expeditionGuideAuditDone = true
  let expected = expeditionGuideStacks()
  let tome = expeditionFullGuideTome()
  let failures = []
  let check = (condition, label) => { if (!condition) failures.push(label) }
  expected.forEach((book, index) => {
    let converted = ExpeditionTome.convert(tome.copy(), index)
    check(expeditionMatchesGuide(converted, book), 'convert:' + index)
    let restored = ExpeditionTome.revert(converted)
    ExpeditionTome.attach(restored, converted)
    check(ExpeditionTome.getItemCount(restored) === expected.length, 'revert-count:' + index)
    check(expeditionHasCompleteGuideTome(restored, expected), 'revert-content:' + index)
    if (String(book.id) === 'minecraft:written_book') {
      let nativeCopy = book.copy()
      delete nativeCopy.nbt['expedition:guide_id']
      nativeCopy.nbt.resolved = true
      check(expeditionMatchesGuide(nativeCopy, book), 'written-native-resolved-match:' + index)
      let matchingVolumes = 0
      expected.forEach(candidate => { if (expeditionMatchesGuide(nativeCopy, candidate)) matchingVolumes++ })
      check(matchingVolumes === 1, 'written-native-distinct-volume:' + index)
    }
  })

  let legacy = []
  expeditionGuideCatalog.forEach((entry, index) => {
    if (!entry.factory && (!entry.nbt || entry.nbt['patchouli:book'] !== 'eclipticseasons:seasons_chronicle')) legacy.push(expected[index])
  })
  check(legacy.length === 28, 'legacy-real-guide-count')
  let blank = Item.of('legendary_monsters:guide_book')
  let blankState = expeditionGuideStackState(blank)
  let oldCount = legacy.length + 1
  check(oldCount === 29, 'legacy-book-count')
  let old = Item.of('eccentrictome:tome', { expeditionGuideAuditMarker: 'outer-preserved' })
  legacy.forEach(book => ExpeditionTome.attach(old, book))
  ExpeditionTome.attach(old, blank)
  let custom = Item.of('minecraft:book', {
    display: { Name: '{"text":"自定义教程笔记"}', Lore: ['{"text":"保留玩家内容"}'] },
    expeditionGuideAuditMarker: 'custom-preserved'
  })
  ExpeditionTome.attach(old, custom)
  let customState = expeditionGuideStackState(custom)
  let beforeOuter = expeditionGuideOuterState(old)
  let added = expeditionRefreshGuideTome(old, expected)
  check(added === 14, 'refresh-old-added')
  check(expeditionGuideOuterState(old) === beforeOuter, 'refresh-old-outer-preserved')
  check(expeditionHasCompleteGuideTome(old, expected), 'refresh-old-complete')
  let containsState = (stack, state) => {
    let entries = ExpeditionTome.getItems(stack)
    for (let index = 0; index < entries.size(); index++) {
      if (expeditionGuideStackState(entries.get(index)) === state) return true
    }
    return false
  }
  check(containsState(old, blankState), 'refresh-old-blank-preserved')
  check(containsState(old, customState), 'refresh-old-custom-preserved')
  check(ExpeditionTome.getItemCount(old) === expected.length + 2, 'refresh-old-count')
  let once = expeditionGuideStackState(old)
  check(expeditionRefreshGuideTome(old, expected) === 0, 'refresh-old-idempotent-count')
  check(expeditionGuideStackState(old) === once, 'refresh-old-idempotent-nbt')

  if (legacy.length > 0) {
    let partial = Item.of('eccentrictome:tome')
    legacy.forEach(book => ExpeditionTome.attach(partial, book))
    ExpeditionTome.attach(partial, blank)
    ExpeditionTome.attach(partial, custom)
    let selected = ExpeditionTome.convert(partial, 0)
    selected.nbt.expeditionGuideAuditMarker = 'selected-preserved'
    let selectedOuter = expeditionGuideOuterState(selected)
    let selectedAdded = expeditionRefreshGuideTome(selected, expected)
    check(selectedAdded === 14, 'refresh-selected-added')
    check(expeditionGuideOuterState(selected) === selectedOuter, 'refresh-selected-outer-preserved')
    check(expeditionHasCompleteGuideTome(selected, expected), 'refresh-selected-complete')
    check(containsState(selected, blankState), 'refresh-selected-blank-preserved')
    check(containsState(selected, customState), 'refresh-selected-custom-preserved')
    check(ExpeditionTome.getItemCount(selected) === expected.length + 1, 'refresh-selected-no-active-duplicate')
    let selectedOnce = expeditionGuideStackState(selected)
    check(expeditionRefreshGuideTome(selected, expected) === 0, 'refresh-selected-idempotent-count')
    check(expeditionGuideStackState(selected) === selectedOnce, 'refresh-selected-idempotent-nbt')
    let restored = ExpeditionTome.revert(selected)
    ExpeditionTome.attach(restored, selected)
    check(expeditionHasCompleteGuideTome(restored, expected), 'refresh-selected-revert-complete')
    check(containsState(restored, blankState), 'refresh-selected-revert-blank-preserved')
    check(containsState(restored, customState), 'refresh-selected-revert-custom-preserved')
    check(ExpeditionTome.getItemCount(restored) === expected.length + 2, 'refresh-selected-revert-count')
  }

  let ordinary = custom.copy()
  let ordinaryBefore = expeditionGuideStackState(ordinary)
  check(expeditionRefreshGuideTome(ordinary, expected) === 0, 'ordinary-guide-not-upgraded')
  check(expeditionGuideStackState(ordinary) === ordinaryBefore, 'ordinary-guide-unchanged')
  let recipe = event.server.getRecipeManager().byKey(new ExpeditionResourceLocation('eccentrictome:tome'))
  check(recipe.isPresent(), 'crafting-recipe-missing')
  if (recipe.isPresent()) {
    let result = recipe.get().getResultItem(event.server.registryAccess())
    check(ExpeditionTome.getItemCount(result) === expected.length, 'crafting-recipe-count')
    check(expeditionHasCompleteGuideTome(result, expected), 'crafting-recipe-content')
  }
  let ExportDirectory = Java.loadClass('java.io.File')
  new ExportDirectory('kubejs/exported').mkdirs()
  JsonIO.write('kubejs/exported/guide-tome-audit.json', {
    bookCount: ExpeditionTome.getItemCount(tome), books: expeditionGuideCatalog,
    roundTripFailures: failures, passed: failures.length === 0,
    refresh: {
      oldBookCount: oldCount, missingBooksAdded: added,
      customDataPreserved: !failures.some(label => label.indexOf('preserved') >= 0),
      idempotencyPassed: !failures.some(label => label.indexOf('idempotent') >= 0)
    },
    scope: 'Registered guide variants, native conversion/reversion, crafting output, and non-destructive upgrades of ordinary and selected Tomes; page unlock conditions remain native.'
  })
  console.info('[Guide Tome] books=' + expected.length + ', failures=' + failures.length)
}
ServerEvents.loaded(expeditionAuditGuideTome)
