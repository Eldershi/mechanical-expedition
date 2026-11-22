// Models are in controller-local coordinates, matching the north-facing assembly fixtures.
const $WorksMinecraft = Java.loadClass('net.minecraft.client.Minecraft')
const $WorksAxis = Java.loadClass('com.mojang.math.Axis')
const $WorksDirection = Java.loadClass('net.minecraft.core.Direction')
const $WorksRenderType = Java.loadClass('net.minecraft.client.renderer.RenderType')
const $WorksModelKey = Java.loadClass('net.minecraft.client.resources.model.ModelResourceLocation')
const $WorksResource = Java.loadClass('net.minecraft.resources.ResourceLocation')
const $WorksRegisterModels = Java.loadClass('net.neoforged.neoforge.client.event.ModelEvent$RegisterAdditional')
const $WorksParticles = Java.loadClass('net.minecraft.core.particles.ParticleTypes')

const $WorksAtlas = Java.loadClass('net.minecraft.client.renderer.texture.TextureAtlas')

const worksNamespace = 'expedition_industry:'
const worksOrientations = {
  north: {degrees: 0, rightX: 1, rightZ: 0, backX: 0, backZ: 1},
  east: {degrees: -90, rightX: 0, rightZ: 1, backX: -1, backZ: 0},
  south: {degrees: 180, rightX: -1, rightZ: 0, backX: 0, backZ: -1},
  west: {degrees: 90, rightX: 0, rightZ: -1, backX: 1, backZ: 0},
}
const alloyParts = ['body', 'lamp', 'idle_blaze_head', 'idle_blaze_visor',
  'fueled_blaze_head', 'fueled_blaze_visor', 'fueled_blaze_rods_large', 'fueled_blaze_rods_small',
  'work_blaze_head', 'work_blaze_visor', 'work_blaze_flame', 'work_blaze_rods_large', 'work_blaze_rods_small']
const worksParts = {}
const worksites = {
  shaft_furnace: [8, 14, 9],
  electrolytic_cell: [8, 8, 8],
  trading_station: [9, 9, 7],
}
for (const name of Object.keys(worksites)) {
  worksParts[name + '_body'] = worksNamespace + 'block/' + name + '_assembly/body'
}

alloyParts.forEach(name => {
  worksParts['alloy_' + name] = worksNamespace + 'block/alloy_assembly/' + name
})

const pressParts = ['body', 'ram', 'workpiece', 'plate', 'cast', 'ingot']
pressParts.forEach(name => {
  worksParts['press_' + name] = worksNamespace + 'block/hydropress_assembly/' + name
})

function pressEase(value) {
  const t = Math.max(0, Math.min(1, value))
  return t * t * (3 - 2 * t)
}

function worksModelKey(name) {
  return $WorksModelKey.standalone($WorksResource.parse(worksParts[name]))
}

NativeEvents.onEvent($WorksRegisterModels, event => {
  Object.keys(worksParts).forEach(name => event.register(worksModelKey(name)))
})

function worksOrientation(machine) {
  const facing = String(machine.getFrontFacing().orElse($WorksDirection.NORTH))
  return worksOrientations[facing] ?? worksOrientations.north
}

function drawWorksPart(context, name, x, y, z, sx, sy, sz) {
  const client = $WorksMinecraft.getInstance()
  const models = client.getModelManager()
  const model = models.getModel(worksModelKey(name))
  if (model === models.getMissingModel()) return
  const stack = context.poseStack
  stack.pushPose()
  try {
    stack.translate(x, y, z)
    stack.scale(sx, sy, sz)
    const layer = name.startsWith('alloy_') || name.startsWith('press_') || name.endsWith('_body')
      ? $WorksRenderType.entityCutoutNoCull($WorksAtlas.LOCATION_BLOCKS) : $WorksRenderType.cutout()
    const sink = context.bufferSource.getBuffer(layer)
    client.getBlockRenderer().getModelRenderer().renderModel(
      stack.last(), sink, null, model, 1, 1, 1, context.packedLight, context.packedOverlay)
  } finally {
    stack.popPose()
  }
}

function worksMachinePose(context, render) {
  const {degrees} = worksOrientation(context.getMachine())
  const stack = context.poseStack
  stack.pushPose()
  try {
    stack.translate(0.5, 0, 0.5)
    stack.mulPose($WorksAxis.YP.rotationDegrees(degrees))
    stack.translate(-0.5, 0, -0.5)
    render()
  } finally {
    stack.popPose()
  }
}

MBDClientEvents.registerCustomRenderers(event => {
  event.register(worksNamespace + 'alloy_furnace_assembly')
    .viewDistance(80).renderOffScreen(true).boundingBoxInflate(4, 11, 4)
    .onRender(context => worksMachinePose(context, () => {
      const machine = context.getMachine()
      const working = String(machine.getMachineStateName()) === 'working'
      const powered = machine.getCustomData().getBoolean('alloyHot')
      const phase = working ? 'work' : powered ? 'fueled' : 'idle'
      const time = context.getGameTime() + context.partialTick
      const bob = Math.sin(time * 0.12)
      drawWorksPart(context, 'alloy_body', 0, 0, 0, 1, 1, 1)
      if (powered || working) drawWorksPart(context, 'alloy_lamp', 0, 0, 0, 1, 1, 1)
      const hover = working ? 0.12 + 0.029 * bob : powered ? 0.018 * bob : 0
      drawWorksPart(context, 'alloy_' + phase + '_blaze_head', 0, hover, 0, 1, 1, 1)
      drawWorksPart(context, 'alloy_' + phase + '_blaze_visor', 0, hover, 0, 1, 1, 1)
      if (!powered && !working) return
      drawWorksPart(context, 'alloy_' + phase + '_blaze_rods_small', 0, 0.028 * bob, 0, 1, 1, 1)
      drawWorksPart(context, 'alloy_' + phase + '_blaze_rods_large', 0, -0.028 * bob, 0, 1, 1, 1)
      if (working) drawWorksPart(context, 'alloy_work_blaze_flame', 0, 0.018 * bob, 0, 1, 1, 1)
    }))

  event.register(worksNamespace + 'hydropress_assembly')
    .viewDistance(72).renderOffScreen(true).boundingBoxInflate(4, 8, 7)
    .onRender(context => worksMachinePose(context, () => {
      const machine = context.getMachine()
      const data = machine.getCustomData()
      const mode = String(machine.getMachineStateName()) === 'working' ? data.getInt('pressMode') : 0
      const t = (context.getGameTime() + context.partialTick - data.getLong('pressStart')) /
        Math.max(1, data.getInt('pressDuration'))
      const travel = mode === 1 ? 29 * (pressEase((t - .24) / .26) - pressEase((t - .58) / .22)) : 0
      drawWorksPart(context, 'press_body', 0, 0, 0, 1, 1, 1)
      drawWorksPart(context, 'press_ram', 0, -travel / 16, 0, 1, 1, 1)
      if (mode === 1) {
        const advance = t < .24 ? -20 * (1 - pressEase(t / .24)) : 27 * pressEase((t - .78) / .22)
        drawWorksPart(context, t < .455 ? 'press_workpiece' : 'press_plate', advance / 16, 0, 0, 1, 1, 1)
      }
      if (mode === 2 && t > .14) {
        const along = 19 * (1 - pressEase((t - .57) / .22))
        const discharge = 26 * pressEase((t - .79) / .21)
        drawWorksPart(context, t < .59 ? 'press_cast' : 'press_ingot', discharge / 16, 0, along / 16, 1, 1, 1)
      }
    }))

  Object.keys(worksites).forEach(name => {
    const bounds = worksites[name]
    event.register(worksNamespace + name + '_assembly')
      .viewDistance(80).renderOffScreen(true).boundingBoxInflate(bounds[0], bounds[1], bounds[2])
      .onRender(context => worksMachinePose(context, () => {
        drawWorksPart(context, name + '_body', 0, 0, 0, 1, 1, 1)
      }))
  })
})

function worksVent(name, dx, dy, dz, interval, particle, speed) {
  MBDMachineEvents.onClientTick(worksNamespace + name, jsEvent => {
    const machine = jsEvent.event.machine
    if (String(machine.getMachineStateName()) !== 'working') return
    const pos = machine.getPos()
    if (machine.getOffsetTimer() % interval !== 0) return
    const {rightX, rightZ, backX, backZ} = worksOrientation(machine)
    const x = pos.getX() + 0.5 + dx * rightX + dz * backX
    const z = pos.getZ() + 0.5 + dx * rightZ + dz * backZ
    $WorksMinecraft.getInstance().particleEngine.createParticle(
      particle, x, pos.getY() + dy, z, 0, speed, 0)
  })
}

// The stack, exhaust crown and exposed electrode gap are in the actual build patterns.
MBDMachineEvents.onClientTick(worksNamespace + 'alloy_furnace', jsEvent => {
  const machine = jsEvent.event.machine
  const state = String(machine.getMachineStateName())
  const engine = $WorksMinecraft.getInstance().particleEngine
  const pos = machine.getPos()
  const orientation = worksOrientation(machine)
  function at(type, right, height, back, speed) {
    return engine.createParticle(type,
      pos.getX() + 0.5 + right * orientation.rightX + back * orientation.backX,
      pos.getY() + height,
      pos.getZ() + 0.5 + right * orientation.rightZ + back * orientation.backZ, 0, speed, 0)
  }
  if (state === 'working' && machine.getOffsetTimer() % 6 === 0) {
    const smoke = at($WorksParticles.CAMPFIRE_SIGNAL_SMOKE, -1.75, 10.02, 1, 0.082)
    if (smoke) smoke.setColor(0.21, 0.20, 0.19)
  }
  if (state !== 'base' && machine.getOffsetTimer() % 12 === 0 &&
      machine.getCustomData().getBoolean('alloyHot')) {
    at($WorksParticles.SMALL_FLAME, 0, -0.58, 0, 0.025)
  }
})
worksVent('shaft_furnace', 0, 10.88, 5, 5, $WorksParticles.CAMPFIRE_SIGNAL_SMOKE, 0.068)
worksVent('electrolytic_cell', -1.125, 4.35, 2.7, 5, $WorksParticles.ELECTRIC_SPARK, 0.047)
worksVent('electrolytic_cell', 1.125, 4.35, 2.7, 7, $WorksParticles.ELECTRIC_SPARK, 0.048)
