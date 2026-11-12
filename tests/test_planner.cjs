const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../source/planner.js'), 'utf8');
const planningFunction = source.split('\n').find(line => line.startsWith('function planningLists()'));
const sets = [{gems:['Strike','Leap']},{gems:['Cyclone','Leap']},{gems:['Cyclone','Mark']}];
function plan(index, owned) {
  const context = vm.createContext({D:{sets},planningStage:()=>index,buyNames:s=>s.gems,isGemOwned:n=>owned.includes(n)});
  vm.runInContext(planningFunction, context);
  return JSON.parse(vm.runInContext('JSON.stringify(planningLists())', context));
}
assert.deepEqual(plan(0, ['Strike']), {i:0,needed:['Leap'],next:['Cyclone'],nextIndex:1});
assert.deepEqual(plan(0, ['Strike','Leap','Cyclone']), {i:0,needed:[],next:['Mark'],nextIndex:2});
assert.deepEqual(plan(0, ['Strike','Leap','Cyclone','Mark']), {i:0,needed:[],next:[],nextIndex:null});
assert.deepEqual(plan(2, []), {i:2,needed:['Cyclone','Mark'],next:[],nextIndex:null});
console.log('Shopping planner: 4 cases passed.');
