const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const script = fs.readFileSync(path.join(__dirname, '../examples/clash-verge/opencode-directions.js'), 'utf8');
function run(config, name = 'VPN') {
  const ctx = vm.createContext({config: structuredClone(config), name});
  vm.runInContext(script, ctx);
  return JSON.parse(JSON.stringify(vm.runInContext('selectOpenCodeDirections(config, name)', ctx)));
}
const source = {
  proxies: [{name:'DE-15',type:'vless'}, {name:'Test 🚀',type:'vless'}, {name:'Reject ⭐',type:'reject'}],
  'proxy-groups': [
    {name:'VPN',type:'select',proxies:['DE-15','Country ⭐️','Test 🚀','Country ⭐️','Missing 🚀','Plain country','Reject ⭐']},
    {name:'Country ⭐️',type:'fallback',proxies:['DE-15'],url:'https://example.com'},
    {name:'Plain country',type:'select',proxies:['DE-15']}
  ],
  rules:['PROCESS-NAME,opencode.exe,OpenCode-Location','MATCH,DIRECT'],
  listeners:[{name:'diagnostic',port:7900,proxy:'OpenCode-Location'}],
  tun:{enable:true}, dns:{enable:true}
};
const first = run(source);
const selector = first['proxy-groups'].find(g => g.name === 'OpenCode-Location');
assert.deepEqual(selector.proxies, ['Country ⭐️','Test 🚀']);
assert.deepEqual(first['proxy-groups'].slice(0,3), source['proxy-groups']);
for (const key of ['rules','listeners','tun','dns','proxies']) assert.deepEqual(first[key],source[key]);
assert.deepEqual(run(first),first);
assert.throws(() => run(source,'Missing'),/existing source/);
assert.throws(() => run(first,'OpenCode-Location'),/existing source/);
const empty = structuredClone(source); empty['proxy-groups'][0].proxies=['DE-15'];
assert.throws(() => run(empty),/no starred or rocket/);
console.log('PASS: location directions, nested fallback, exclusions, idempotence and preserved routing');
