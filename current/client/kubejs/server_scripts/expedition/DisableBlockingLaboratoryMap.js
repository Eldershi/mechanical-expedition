// priority: -1200
// Incident 2026-10-21 01:45: Quark reads wandering-trader offers automatically;
// Mutant More synchronously locates its laboratory map target on the tick thread.
// Disable only this map's target tag. Laboratory worldgen and other trades remain.
const ExpeditionLaboratoryStructures = Java.loadClass('com.alexander.mutantmore.init.TagInit$Structures')
const ExpeditionLaboratoryRegistries = Java.loadClass('net.minecraft.core.registries.Registries')
const ExpeditionLaboratoryLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
const ExpeditionLaboratoryClock = Java.loadClass('java.lang.System')
let expeditionLaboratoryMapAuditPending = true

ServerEvents.tags('worldgen/structure', event => {
  event.get('mutantmore:on_suspicious_entrance_maps').removeAll()
})

// The first tick after /reload sees the final bound registry tags.
ServerEvents.tick(event => {
  if (!expeditionLaboratoryMapAuditPending) return
  expeditionLaboratoryMapAuditPending = false
  const server = event.server
  const registry = server.registryAccess().registryOrThrow(ExpeditionLaboratoryRegistries.STRUCTURE)
  const targets = registry.getTag(ExpeditionLaboratoryStructures.ON_SUSPICIOUS_ENTRANCE_MAPS)
  const count = targets.isPresent() ? targets.get().size() : 0
  const laboratoryPresent = registry.containsKey(new ExpeditionLaboratoryLocation('mutantmore:derelict_laboratory'))
  const report = { mapTargetCount: count, laboratoryStructureRegistered: laboratoryPresent,
    lookupTested: false, lookupReturnedNull: false, lookupMs: 0, passed: false }
  // Never run a real search if the tag-clear did not take effect.
  if (count === 0) {
    const level = server.overworld()
    const start = ExpeditionLaboratoryClock.nanoTime()
    const found = level.findNearestMapStructure(ExpeditionLaboratoryStructures.ON_SUSPICIOUS_ENTRANCE_MAPS,
      level.getSharedSpawnPos(), 100, true)
    report.lookupMs = (ExpeditionLaboratoryClock.nanoTime() - start) / 1000000
    report.lookupTested = true
    report.lookupReturnedNull = found == null
    report.passed = laboratoryPresent && report.lookupReturnedNull && report.lookupMs < 100
  }
  JsonIO.write('kubejs/exported/laboratory-map-stall-mitigation.json', report)
  if (!report.passed) throw new Error('Laboratory map mitigation failed: ' + JSON.stringify(report))
  console.info('[Expedition] Blocking laboratory map disabled; targets=' + count +
    '; laboratory retained=' + laboratoryPresent + '; native lookup=' + report.lookupMs + 'ms')
})
