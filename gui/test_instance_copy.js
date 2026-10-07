// Exercise copy behavior on mixed and sparse resource grids without browser dependencies.
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
function evaluate(script) { return vm.runInContext(script, context); }
function value(script) { return JSON.parse(JSON.stringify(evaluate(script))); }
evaluate(`
    state={active:null}; changed=()=>{};
    spec={fgra_num_row:4,fgra_num_colum:4,fgra_gpe_fg_rows:[0,2],fgra_gpe_fg_columns:[1,3],
        fgra_gpes:Array.from({length:4},()=>Array.from({length:4},()=>({operations:['ADD']}))),
        fgra_iobs:Array.from({length:2},()=>Array.from({length:4},()=>({iob_mode:2,max_delay_cg:2,has_io_fg:true}))),
        fgra_cg_gibs:Array.from({length:5},()=>Array.from({length:5},()=>({fclist:[2,2,2],diag_iopin_connect:true}))),
        fgra_fg_gibs:Array.from({length:3},()=>Array.from({length:3},()=>({fclist:[2,2,2],diag_iopin_connect:true})))};
    selected={type:'iob',r:0,c:0};
    spec.fgra_iobs[0][0].max_delay_cg=9;
    paint=captureInstance(); selected={type:'iob',r:1,c:3}; applyInstance(paint);
`);
assert.strictEqual(value('spec.fgra_iobs[1][3].max_delay_cg'), 9);
evaluate('spec.fgra_iobs[1][3].max_delay_cg=7;');
assert.strictEqual(value('spec.fgra_iobs[0][0].max_delay_cg'), 9, 'Painted cells must be independent copies');
evaluate("selected={type:'pe',r:0,c:0};");
assert.strictEqual(evaluate('applyInstance(paint)'), false, 'Cross-type copying must be rejected');
assert.deepStrictEqual(value('spec.fgra_gpes[0][0].operations'), ['ADD']);
evaluate("selected={type:'iob',r:0,c:0};applyInstance(captureInstance(),true);");
assert(value('spec.fgra_iobs.every(row=>row.every(x=>x.max_delay_cg===9))'), 'All IOBs on both sides must be updated');
evaluate(`
    selected={type:'gib',r:0,c:1};
    selectedCell().fclist=[4,4,2]; fgGibCell(0,1).fclist=[6,8,2];
    paint=captureInstance();selected={type:'gib',r:2,c:3};applyInstance(paint);
`);
assert.deepStrictEqual(value('spec.fgra_cg_gibs[2][3].fclist'), [4,4,2]);
assert.deepStrictEqual(value('spec.fgra_fg_gibs[1][1].fclist'), [6,8,2], 'FG indexing must follow the sparse grid');
evaluate("selected={type:'gib',r:1,c:0};applyInstance(paint);");
assert.strictEqual(evaluate('fgGibCell(1,0)'), undefined, 'Painting must not create new FG resources');
evaluate('applyInstance(captureInstance(),true);');
assert.deepStrictEqual(value('spec.fgra_fg_gibs[0][0].fclist'), [6,8,2], 'CG-only sources must preserve FG settings');
evaluate("selected={type:'gib',r:2,c:3};applyInstance(captureInstance(),true);");
assert(value('spec.fgra_cg_gibs.every(row=>row.every(x=>x.fclist[0]===4))'));
assert(value('spec.fgra_fg_gibs.every(row=>row.every(x=>x.fclist[0]===6))'));
evaluate("selected={type:'gib',r:4,c:4};fgGibCell(4,4).fclist=[10,10,2];");
assert.deepStrictEqual(value('spec.fgra_fg_gibs[2][2].fclist'), [10,10,2], 'Terminal GIB row and column must be indexed correctly');
evaluate('state.active="running";');
assert.strictEqual(evaluate('applyInstance(captureInstance(),true)'), false, 'Running tasks must lock configuration edits');
console.log('Instance copy checks passed (IOB, CG/FG GIB, sparse grid, type isolation, edit locking).');
