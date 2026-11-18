ServerEvents.tags('item', event => {
  event.add('c:tools/knife', 'cmi:super_knife')
  event.add('farmersdelight:tools/knives', 'cmi:super_knife')
  event.add('farmersdelight:enchantable/knife', 'cmi:super_knife')
})
ServerEvents.recipes(event => {
  const create = event.recipes.create
  const path = 'expedition:factory/knife/'
  create.mixing(Fluid.of('cmi:ink', 250), [
    Fluid.of('minecraft:water', 250),
    Ingredient.of(['#c:dusts/charcoal', '#c:dusts/coal'])
  ]).id(path + 'ink')
  create.mixing(Fluid.of('cmi:hyper_experience', 10), [
    Ingredient.of('#c:dusts/lapis'), Fluid.of('cmi:ink', 25),
    Fluid.of('create_enchantment_industry:experience', 100)
  ]).superheated().id(path + 'hyper_experience')
  create.filling('cmi:super_knife', [
    'farmersdelight:netherite_knife', Fluid.of('cmi:hyper_experience', 1000)
  ]).id(path + 'super_knife')
})
