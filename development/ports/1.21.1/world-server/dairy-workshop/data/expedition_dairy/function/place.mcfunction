# Foundation and the cattle enclosure.
fill ~ ~ ~ ~12 ~ ~8 create:polished_cut_andesite
fill ~1 ~1 ~2 ~5 ~1 ~6 minecraft:spruce_planks
fill ~2 ~1 ~3 ~4 ~1 ~5 createrancher:livestock_drain
fill ~1 ~2 ~2 ~5 ~2 ~2 minecraft:spruce_fence[east=true,west=true]
fill ~1 ~2 ~6 ~5 ~2 ~6 minecraft:spruce_fence[east=true,west=true]
fill ~1 ~2 ~3 ~1 ~2 ~5 minecraft:spruce_fence[north=true,south=true]
fill ~5 ~2 ~3 ~5 ~2 ~5 minecraft:spruce_fence[north=true,south=true]
setblock ~1 ~2 ~2 minecraft:spruce_fence[east=true,south=true]
setblock ~5 ~2 ~2 minecraft:spruce_fence[west=true,south=true]
setblock ~1 ~2 ~6 minecraft:spruce_fence[east=true,north=true]
setblock ~5 ~2 ~6 minecraft:spruce_fence[west=true,north=true]
setblock ~1 ~2 ~4 minecraft:spruce_fence_gate[facing=west]
fill ~0 ~1 ~1 ~0 ~4 ~1 minecraft:stripped_spruce_log[axis=y]
fill ~0 ~1 ~7 ~0 ~4 ~7 minecraft:stripped_spruce_log[axis=y]
fill ~5 ~1 ~1 ~5 ~4 ~1 minecraft:stripped_spruce_log[axis=y]
fill ~5 ~1 ~7 ~5 ~4 ~7 minecraft:stripped_spruce_log[axis=y]
fill ~0 ~5 ~1 ~5 ~5 ~7 minecraft:spruce_slab[type=bottom]

# Collection, 8-bucket buffer, and milk supply to the spout.
setblock ~5 ~1 ~4 create:fluid_pipe[west=true,east=true]
setblock ~6 ~1 ~4 create:mechanical_pump[facing=east]
setblock ~7 ~1 ~4 create:fluid_tank[shape=window]
fill ~8 ~1 ~4 ~9 ~1 ~4 create:fluid_pipe[west=true,east=true]
setblock ~10 ~1 ~4 create:mechanical_pump[facing=east]
setblock ~11 ~1 ~4 create:fluid_pipe[west=true,up=true]
fill ~11 ~2 ~4 ~11 ~3 ~4 create:fluid_pipe[up=true,down=true]
setblock ~11 ~4 ~4 create:fluid_pipe[down=true,north=true]
setblock ~11 ~4 ~3 create:spout

# A contained water column drives the two pumps through the shared shaft.
setblock ~6 ~2 ~4 create:cogwheel[axis=x]
fill ~7 ~2 ~4 ~8 ~2 ~4 create:shaft[axis=x]
setblock ~9 ~2 ~4 create:water_wheel[facing=east]
setblock ~10 ~2 ~4 create:cogwheel[axis=x]
fill ~8 ~1 ~5 ~8 ~3 ~5 minecraft:glass
fill ~10 ~1 ~5 ~10 ~3 ~5 minecraft:glass
fill ~9 ~1 ~6 ~9 ~3 ~6 minecraft:glass
setblock ~9 ~3 ~4 minecraft:glass
setblock ~9 ~3 ~5 minecraft:water

# Bottles enter via the top barrel. The filtered chute collects only filled bottles.
setblock ~11 ~ ~3 minecraft:barrel[facing=east]
setblock ~11 ~1 ~3 create:smart_chute{Filter:{id:"farmersdelight:milk_bottle",count:1}}
setblock ~11 ~2 ~3 create:depot
setblock ~11 ~2 ~2 minecraft:hopper[facing=south]
setblock ~11 ~3 ~2 minecraft:barrel[facing=east]
setblock ~12 ~3 ~2 minecraft:spruce_wall_sign[facing=east]{front_text:{messages:['{"text":"乳品车间"}','{"text":"上桶放玻璃瓶"}','{"text":"下桶取奶瓶"}','{"text":""}']}}

summon minecraft:cow ~2.5 ~2 ~3.5 {PersistenceRequired:1b,Tags:["expedition_dairy_cow"]}
summon minecraft:cow ~4.5 ~2 ~5.5 {PersistenceRequired:1b,Tags:["expedition_dairy_cow"]}
