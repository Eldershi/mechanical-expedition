const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(path.join(__dirname, '../../pack/kubejs/server_scripts/expedition_powergrid_diagnostics.js'), 'utf8');
let handler;
const messages = [];
const external = [{getVoltage: () => 120, getNetwork: () => ({isConverged: () => true})}, {getVoltage: () => 0, getNetwork: () => ({isConverged: () => true})}];
const electric = {getExternalNodes: () => ({size: () => external.length, get: i => external[i]})};
const blocks = new Map([
  ['0,0,0', {id: 'powergrid:generator_commutator', entity: {getCurrent: () => 2, getPower: () => 240, getBehaviour: () => electric}, entityData: {getFloat: () => 256}}],
  ['1,0,0', {id: 'powergrid:winding', entity: {fieldStrengthCalc: () => ({get: () => 3}), getBehaviour: () => electric}, entityData: {contains: key => key === 'I', getFloat: () => 2}}],
  ['2,0,0', {id: 'powergrid:winding', entity: {fieldStrengthCalc: () => ({get: () => 3})}, entityData: {contains: () => false}}],
  ['3,0,0', {id: 'powergrid:transformer_medium', entity: {getPrimary: () => null}, entityData: {}}],
  ['4,0,0', {id: 'minecraft:chest', entity: {getBehaviour: () => {throw new Error('Unrelated inventory must not be inspected');}}}],
]);
let reads = 0;
vm.runInNewContext(source, {
  Java: {loadClass: name => {assert.equal(name, 'org.patryk3211.powergrid.electricity.base.ElectricBehaviour'); return {TYPE: {}};}},
  Platform: {isLoaded: id => id === 'powergrid'},
  ServerEvents: {customCommand: (id, callback) => {assert.equal(id, 'expedition_powergrid_probe'); handler = callback;}},
  console: {info: message => messages.push(message)},
});
handler({block: {x: 0, y: 0, z: 0}, level: {getBlock: (x,y,z) => {reads++; assert.ok(Math.abs(x) <= 6 && Math.abs(y) <= 6 && Math.abs(z) <= 6); return blocks.get([x,y,z].join(',')) || {id:'minecraft:air'};}}});
assert.equal(reads, 13 ** 3);
assert.equal(messages.length, 1);
const report = JSON.parse(messages[0].slice('[PG-PROBE] '.length));
assert.equal(report.windingCount, 2);
assert.equal(report.windingFieldMin, 3);
assert.equal(report.components.length, 2);
assert.equal(report.components.find(row => row.id === 'powergrid:generator_commutator').watts, 240);
assert.equal(report.components.find(row => row.id === 'powergrid:winding').amps, 2);
assert.deepEqual(report.components[0].nodes.volts, [120, 0]);
console.log('Read-only scan, solver measurements, owner filtering and bounds passed.');
