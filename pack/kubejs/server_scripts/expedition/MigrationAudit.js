// priority: -100
// 核验迁移里程碑是否有真实注册物品和可加载配方，不改写上游配方。
ServerEvents.loaded((event) => {
	let { server } = event
	let milestones = [
    "cmi:advanced_mekanism_mechanism",
    "cmi:aeronautic_mechanism",
    "cmi:andesite_mechanism",
    "cmi:antimatter_mechanism",
    "cmi:astronautic_mechanism",
    "cmi:basic_mekanism_mechanism",
    "cmi:bronze_mechanism",
    "cmi:coil_mechanism",
    "cmi:computing_mechanism",
    "cmi:copper_mechanism",
    "cmi:elite_mekanism_mechanism",
    "cmi:nuclear_mechanism",
    "cmi:pig_iron_mechanism",
    "cmi:railway_mechanism",
    "cmi:smart_mechanism",
    "cmi:stone_mechanism",
    "cmi:ultimate_mekanism_mechanism",
    "cmi:wooden_mechanism",
    "create:precision_mechanism"
]
	let recipeCounts = {}
	milestones.forEach((id) => {
		recipeCounts[id] = 0
	})
	let auditedRecipes = 0
	// 1.20.1的getRecipes()暴露按RecipeType分组的Map，先展开两层值。
	server.getRecipeManager().getRecipes().values().forEach((recipes) => {
		recipes.values().forEach((recipe) => {
			let output = recipe.getResultItem(server.registryAccess())
			if (!output.isEmpty()) {
				let id = output.id
				if (Object.prototype.hasOwnProperty.call(recipeCounts, id)) {
					recipeCounts[id] += 1
				}
			}
			auditedRecipes += 1
		})
	})
	let missingItems = []
	let missingRecipes = []
	milestones.forEach((id) => {
		if (Item.of(id).isEmpty()) {
			missingItems.push(id)
		}
		if (recipeCounts[id] === 0) {
			missingRecipes.push(id)
		}
	})
	let report = {
		build: "CMI-Expedition-Migration-01",
		milestones: milestones,
		recipeCounts: recipeCounts,
		missingItems: missingItems,
		missingRecipes: missingRecipes,
		auditedRecipes: auditedRecipes,
		passed: missingItems.length === 0 && missingRecipes.length === 0,
		note: "验证物品注册和配方加载；不代表生产链可达性、平衡或全程通关已经验证。"
	}
	JsonIO.write("kubejs/exported/expedition-cmi-smoke.json", report)
	console.info(`[Expedition Migration] milestones=${milestones.length}, missingItems=${missingItems.length}, missingRecipes=${missingRecipes.length}, recipes=${auditedRecipes}`)
})
