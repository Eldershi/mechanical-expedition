ServerEvents.tags('item', event => {
  const rules = JsonIO.read('kubejs/data/expedition/item_compatibility.json')
  if (!rules) return

  const alias = (kind, id) => 'expedition:recipe_aliases/' + kind + '/' + id.replace(':', '/')
  const matches = {}
  rules.groups.forEach(group => {
    group.forEach(item => {
      if (!matches[item]) matches[item] = new Set()
      group.forEach(alternative => matches[item].add(alternative))
    })
  })
  Object.keys(matches).forEach(item => {
    event.add(alias('item', item), Array.from(matches[item]))
  })
  Object.keys(rules.augmentedTags).forEach(tag => {
    event.add(alias('tag', tag), ['#' + tag].concat(rules.augmentedTags[tag]))
  })
})
