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
const $AlloyFurnaceRender = Platform.isLoaded('expedition_alloy_furnace_render')
  ? Java.loadClass('expedition.alloyrender.AlloyFurnaceRender') : null

const worksNamespace = 'expedition_industry:'
const worksOrientations = {
  north: {degrees: 0, rightX: 1, rightZ: 0, backX: 0, backZ: 1},
  east: {degrees: -90, rightX: 0, rightZ: 1, backX: -1, backZ: 0},
  south: {degrees: 180, rightX: -1, rightZ: 0, backX: 0, backZ: -1},
  west: {degrees: 90, rightX: 0, rightZ: -1, backX: 1, backZ: 0},
}
const worksParts = {
  alloy_furnace_shell: worksNamespace + 'block/works/alloy_furnace_shell',
  press_head: 'create:block/mechanical_press/head',
  press_yoke: worksNamespace + 'block/works/press_yoke',
  trade_counter: worksNamespace + 'block/works/trade_counter',
  parcel: worksNamespace + 'block/works/parcel',
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
    const layer = name === 'alloy_furnace_shell'
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
  event.register(worksNamespace + 'alloy_furnace_motion')
    .viewDistance(96).renderOffScreen(true).boundingBoxInflate(3, 9, 3)
    .onRender(context => {
      if (!$AlloyFurnaceRender || !$AlloyFurnaceRender.isVisible(context.getMachine())) return
      worksMachinePose(context, () => drawWorksPart(context, 'alloy_furnace_shell', 0, 0, 0, 1, 1, 1))
    })

  event.register(worksNamespace + 'hydropress_motion')
    .viewDistance(64).renderOffScreen(true).boundingBoxInflate(2, 6, 2)
    .onRender(context => worksMachinePose(context, () => {
      const machine = context.getMachine()
      const time = context.getGameTime() + context.partialTick
      const stroke = machine.getMachineStateName() === 'working'
        ? 0.34 * Math.pow(Math.max(0, Math.sin(Math.PI * (time % 28) / 28)), 2) : 0
      // The carrier at (2,6,4) supports the yoke extending into the free bay at (2,6,3).
      drawWorksPart(context, 'press_yoke', 0, 4, 2, 1, 1, 1)
      drawWorksPart(context, 'press_head', 0.20, 4.27 - stroke, 2.12, 0.60, 0.60, 0.60)
    }))

  event.register(worksNamespace + 'trading_station_motion')
    .viewDistance(48).renderOffScreen(true).boundingBoxInflate(2, 2, 2)
    .onRender(context => worksMachinePose(context, () => {
      drawWorksPart(context, 'trade_counter', 0, 0, -2, 1, 1, 1)
      if (context.getMachine().getMachineStateName() !== 'working') return
      const time = (context.getGameTime() + context.partialTick) % 32
      if (time < 24) {
        drawWorksPart(context, 'parcel', 0, 0.0625, -2 + 0.40 * time / 24, 1, 1, 1)
      }
    }))
})

function worksVent(name, dx, dy, dz, interval, particle, speed) {
  MBDMachineEvents.onClientTick(worksNamespace + name, jsEvent => {
    const machine = jsEvent.event.machine
    if (machine.getMachineStateName() !== 'working') return
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
worksVent('alloy_furnace', 0, 3.05, 0, 7, $WorksParticles.SMOKE, 0.045)
worksVent('shaft_furnace', 0, 3.10, 0, 5, $WorksParticles.LARGE_SMOKE, 0.055)
worksVent('electrolytic_cell', -1, 0.70, 0, 6, $WorksParticles.ELECTRIC_SPARK, 0.025)
worksVent('electrolytic_cell', 1, 0.70, 0, 6, $WorksParticles.ELECTRIC_SPARK, 0.025)
