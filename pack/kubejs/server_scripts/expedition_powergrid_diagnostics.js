// Read-only Power Grid measurements around the command execution position.
ServerEvents.customCommand('expedition_powergrid_probe', function (event) {
  if (!Platform.isLoaded('powergrid')) return;
  var electricType = Java.loadClass('org.patryk3211.powergrid.electricity.base.ElectricBehaviour').TYPE;
  var origin = event.block;
  var level = event.level;
  var rows = [];
  var windingCount = 0;
  var windingFieldMin = null;
  var windingFieldMax = null;
  function number(value) {
    var n = Number(value);
    return isFinite(n) ? Math.round(n * 1000000) / 1000000 : null;
  }
  function nodes(entity) {
    var behavior = entity.getBehaviour(electricType);
    var list = behavior.getExternalNodes();
    var voltages = [];
    var converged = [];
    for (var i = 0; i < list.size(); i++) {
      var node = list.get(i);
      voltages.push(number(node.getVoltage()));
      var network = node.getNetwork();
      converged.push(network == null ? null : Boolean(network.isConverged()));
    }
    return { volts: voltages, converged: converged };
  }
  for (var x = origin.x - 6; x <= origin.x + 6; x++) {
    for (var y = origin.y - 6; y <= origin.y + 6; y++) {
      for (var z = origin.z - 6; z <= origin.z + 6; z++) {
        var block = level.getBlock(x, y, z);
        var id = String(block.id);
        if (id.indexOf('powergrid:') !== 0) continue;
        var entity = block.entity;
        if (entity == null) continue;
        try {
          var tag = block.entityData;
          if (id === 'powergrid:winding') {
            windingCount++;
            var field = entity.fieldStrengthCalc();
            if (field != null) {
              var b = number(field.get());
              windingFieldMin = windingFieldMin == null ? b : Math.min(windingFieldMin, b);
              windingFieldMax = windingFieldMax == null ? b : Math.max(windingFieldMax, b);
            }
            if (!tag.contains('I')) continue;
            rows.push({ id: id, pos: [x, y, z], amps: number(tag.getFloat('I')), nodes: nodes(entity) });
          } else if (id === 'powergrid:generator_commutator') {
            rows.push({ id: id, pos: [x, y, z], amps: number(entity.getCurrent()), watts: number(entity.getPower()), rpm: number(tag.getFloat('AngularVelocity')), nodes: nodes(entity) });
          } else if (id === 'powergrid:transformer_medium') {
            var primary = entity.getPrimary();
            if (primary == null || primary.getTurns() <= 0) continue;
            rows.push({ id: id, pos: [x, y, z], nodes: nodes(entity) });
          } else if (id === 'powergrid:current_gauge' || id === 'powergrid:power_gauge') {
            rows.push({ id: id, pos: [x, y, z], reading: number(entity.getValue()), nodes: nodes(entity) });
          } else if (id === 'powergrid:device_connector' || id === 'powergrid:hv_breaker') {
            rows.push({ id: id, pos: [x, y, z], nodes: nodes(entity) });
          }
        } catch (error) {
          rows.push({ id: id, pos: [x, y, z], error: String(error) });
        }
      }
    }
  }
  console.info('[PG-PROBE] ' + JSON.stringify({ origin: [origin.x, origin.y, origin.z], windingCount: windingCount, windingFieldMin: windingFieldMin, windingFieldMax: windingFieldMax, components: rows }));
});
