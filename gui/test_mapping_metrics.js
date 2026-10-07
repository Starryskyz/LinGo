// Count physical resource occupancy, including packed operators and repeated labels.
'use strict';
const assert = require('assert');
const fs = require('fs');
const vm = require('vm');
const elements = {};
const context = vm.createContext({
    document: {
        getElementById(id) { return elements[id] || (elements[id] = {}); },
        addEventListener() {}
    },
    fetch() { return new Promise(() => {}); },
    setTimeout, clearTimeout, setInterval, console
});
vm.runInContext(fs.readFileSync(__dirname + '/static/app.js', 'utf8'), context);
const usage = vm.runInContext(`mappingUtilization({objects:[
    {name:'GPE1',label:'GPE1\\nDFG:ADD1\\nDFG:MUL2'},
    {name:'GPE1',label:'DFG:ADD1'},
    {name:'GPE2',label:'GPE2'},
    {name:'IOB3',label:'DFG:Input4'},
    {name:'CGGIB4',label:'DFG:route'},
    {name:'GPE999',label:'DFG:unknown'}
]},{instances:[
    {id:1,type:'GPE'},{id:2,type:'GPE'},
    {id:3,type:'IOB'},{id:4,type:'CGGIB'},{id:0,type:'This'}
]})`, context);
assert.deepStrictEqual(JSON.parse(JSON.stringify(usage)), {pe:{used:1,total:2},io:{used:1,total:1}});
vm.runInContext('mapped=null;adg=null;updateUtilization(false);', context);
assert.strictEqual(elements['pe-usage'].textContent, '--');
assert.strictEqual(elements['io-count'].textContent, '');
console.log('Mapping utilization checks passed (packing, duplicates, unused resources, invalid IDs and stale results).');
