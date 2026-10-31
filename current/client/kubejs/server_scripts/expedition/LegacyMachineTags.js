// Retained legacy submachines keep their item tags after upstream port migration.
ServerEvents.tags("item", (event) => {
	let machines = [
		"reinforced_coke_oven",
		"improved_rubber_extractor",
		"chemical_reactor",
		"reinforced_chemical_reactor",
		"electrolyzer",
		"electronic_blast_furnace"
	]
	machines.forEach((machine) => {
		event.get("cmi:machine_port")
			.add(`cmi:${machine}_input_bus`)
			.add(`cmi:${machine}_output_bus`)

			.add(`cmi:${machine}_item_input_bus`)
			.add(`cmi:${machine}_item_output_bus`)

			.add(`cmi:${machine}_fluid_input_bus`)
			.add(`cmi:${machine}_fluid_output_bus`)

			.add(`cmi:${machine}_energy_input_bus`)
			.add(`cmi:${machine}_energy_output_bus`)

			.add(`cmi:${machine}_gas_input_bus`)
			.add(`cmi:${machine}_gas_output_bus`)

		event.get("cmi:machine_core")
			.add(`cmi:${machine}`)
	})
})