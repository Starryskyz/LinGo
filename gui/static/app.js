'use strict';
const $=id=>document.getElementById(id), clone=x=>JSON.parse(JSON.stringify(x)), esc=x=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let state,spec,page='hardware',selected={type:'pe',r:0,c:0},paint=null,sourceOriginal='',loadedProgram='',draftTimer,draftPending=false,editing=false,mapped=null,adg=null,lastGraph='',mapJob='',currentJob='',refreshing=false,wasBusy=false,verificationName='',verificationOriginal='',verificationDirty=false,verificationSaved=false,verificationLoadToken=0;
const pages=['hardware','compile','mapping','verification','physical'];
const labels=['CGRA HW','Compile','Mapping','Verification','Physical Design'];
const titles=['Build your architecture.','Turn code into data flow.','Place. Route. Execute.','Verify your design.','Bring your design to silicon.'];
const descriptions=['Shape the array, configure its resources, then generate hardware.','Compile a C kernel and inspect its data flow graph.','Map a compiled program onto your generated architecture.','Simulation and result checking.','Physical implementation and design reports.'];
async function api(path,data){const response=await fetch('/api/'+path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw Error(result.error||'Request failed');return result;}
function notice(message){$('notice').textContent=message;$('notice').hidden=!message;}
function status(id,message,kind=''){$(id).textContent=message;$(id).className='status '+kind;}
async function action(fn){try{notice('');await fn();}catch(error){notice(error.message);}}
function flow(){const limit=state.dirty||!state.rtl_current?0:state.step;$('flow').innerHTML=pages.map((p,i)=>`<button class="flow-item ${page===p?'active':''} ${i<limit?'done':''}" data-page="${p}" ${(i===3?!state.rtl_current||state.dirty:i>limit||i>3)?'disabled':''}><span class="step-number">${i<limit?'✓':String(i+1).padStart(2,'0')}</span>${labels[i]}</button>`).join('');$('flow').querySelectorAll('button').forEach(b=>b.onclick=()=>showPage(b.dataset.page));}
function showPage(next){page=next;document.querySelector('main').classList.toggle('verification-view',page==='verification');document.querySelector('.log-card').hidden=page==='verification';$('mapping-artifacts').hidden=page!=='mapping';pages.forEach(p=>$(p).hidden=p!==page);const index=pages.indexOf(page);$('step-label').textContent=`STEP ${String(index+1).padStart(2,'0')} / ${labels[index].toUpperCase()}`;$('page-title').textContent=titles[index];$('page-description').textContent=descriptions[index];flow();if(page==='mapping')drawMap();if(page==='verification')action(refreshVerification);updateLog();}
function fillPrograms(id,names){const select=$(id),old=select.value;if(JSON.stringify(Array.from(select.options).map(o=>o.value))===JSON.stringify(names))return;select.innerHTML=names.map(n=>`<option value="${esc(n)}">${esc(n)}</option>`).join('');if(names.includes(old))select.value=old;}
function latestJob(kind,name){return Object.values(state.jobs).filter(j=>j.kind===kind&&(!name||j.name===name)).slice(-1)[0];}
function jobStatus(id,kind,name,result){const job=latestJob(kind,name);if(job&&(!result||job.id!==result.job)){status(id,`${job.status==='running'?'Running':job.status==='succeeded'?'Succeeded':job.status==='cancelled'?'Cancelled':'Failed'} · ${job.elapsed}s`,job.status==='succeeded'?'success':job.status==='running'?'running':'failed');return;}status(id,result?(result.current===false?'Outdated':'Succeeded'):'Not run',result?(result.current===false?'warning':'success'):'');}
async function refresh(first=false){if(refreshing)return;refreshing=true;try{state=await api('state');if(first||!draftPending&&JSON.stringify(spec)!==JSON.stringify(state.draft)){spec=clone(state.draft);arrayFields();drawArchitecture('hw-canvas',spec,false);instancePanel();}if(wasBusy&&!state.active)instancePanel();wasBusy=!!state.active;for(const id of ['rows','cols','bank','coalesce','cg-tracks','fg-tracks'])$(id).disabled=!!state.active;if(state.active)$('instance-settings').querySelectorAll('input,select,button').forEach(el=>el.disabled=true);fillPrograms('compile-program',state.benchmarks);fillPrograms('mapping-program',Object.keys(state.compile).filter(n=>state.benchmarks.includes(n)));if(first){fillPrograms('verification-program',(state.verification||{}).benchmarks||[]);const ui=state.ui||{};for(const [key,id]of [['program','compile-program'],['mapping_program','mapping-program'],['compiler','compiler'],['kernel','kernel'],['backend','backend'],['verification_program','verification-program']])if(ui[key]&&($(id).tagName!=='SELECT'||Array.from($(id).options).some(o=>o.value===ui[key])))$(id).value=ui[key];$('kernel').disabled=$('compiler').value==='mlir';}fillPrograms('spec-template',state.spec_templates||[]);if(first&&state.loaded_template&&Array.from($('spec-template').options).some(o=>o.value===state.loaded_template))$('spec-template').value=state.loaded_template;$('spec-template').disabled=!!state.active;$('load-spec').disabled=!!state.active||!$('spec-template').value;$('save-spec').disabled=!!state.active||state.dirty||draftPending;$('save-spec-name').disabled=!!state.active;flow();status('spec-status',state.dirty?'Draft changes': 'Up to date',state.dirty?'warning':'success');const rtlJob=latestJob('rtl');if(rtlJob&&rtlJob.status==='running')status('rtl-status',`Generating · ${rtlJob.elapsed}s`,'running');else if(rtlJob&&rtlJob.status==='failed')status('rtl-status','Failed','failed');else status('rtl-status',state.rtl_current?'Succeeded':state.rtl?'Outdated':'Not generated',state.rtl_current?'success':'warning');['generate-spec','generate-rtl','compile-button','map-button','save-source','new-program'].forEach(id=>$(id).disabled=!!state.active);$('generate-rtl').disabled=!!state.active||state.dirty;const name=$('compile-program').value,result=state.compile[name];jobStatus('compile-status','compile',name,result);const cj=latestJob('compile',name);const valid=result&&result.current&&(!cj||cj.status==='succeeded'&&cj.id===result.job);$('node-count').textContent=valid?result.nodes:'--';$('edge-count').textContent=valid?result.edges:'--';$('compile-time').textContent=cj?cj.elapsed+' s':'--';if(name!==loadedProgram&&!editing)await loadSource();if(valid&&result.svg!==lastGraph){lastGraph=result.svg;await loadDFG(result.svg);}else if(!valid){lastGraph='';$('dfg-canvas').innerHTML='<div class="empty"><span>◇</span>Compile this program to explore its data flow.</div>';}
const mn=$('mapping-program').value,mr=state.mapping[mn],mj=latestJob('mapping',mn);jobStatus('mapping-status','mapping',mn,mr);const mv=mr&&mr.current&&(!mj||mj.status==='succeeded'&&mj.id===mr.job);$('ii').textContent=mv?mr.ii:'--';$('latency').textContent=mv?mr.latency:'--';$('mapping-time').textContent=mj?mj.elapsed+' s':'--';updateUtilization(mv&&mapJob===mr.job);$('mapping-artifacts').hidden=page!=='mapping'||!mv;$('mapping-artifacts').innerHTML=mv?'<span>Generated outputs</span>'+ (mr.files||[]).map(file=>`<a download href="/api/artifact?job=${mr.job}&file=${encodeURIComponent(file)}">${esc(file)} ↓</a>`).join(''):'';$('map-button').disabled=!!state.active||!(state.compile[mn] && state.compile[mn].current)||!state.rtl_current||state.dirty;$('compile-button').disabled=!!state.active||!state.rtl_current||state.dirty||!name;updateLog();if(page==='mapping'&&mv&&mapJob!==mr.job){mapJob=mr.job;[mapped,adg]=await Promise.all([api('mapping?job='+mr.job),api('adg')]);drawMap();}if(!mv&&page==='mapping'){mapped=null;mapJob='';drawMap();}await refreshVerification();}finally{refreshing=false;}}
function updateLog(){const kind=page==='hardware'?'rtl':page==='compile'?'compile':'mapping',name=page==='compile'?$('compile-program').value:page==='mapping'?$('mapping-program').value:null;const job=state.active?state.jobs[state.active]:latestJob(kind,name);$('cancel').hidden=!state.active;$('log-label').textContent=job?`${job.kind.toUpperCase()} · ${job.status} · ${job.elapsed}s`:'Ready';const el=$('log'),bottom=el.scrollTop+el.clientHeight>=el.scrollHeight-25;el.textContent=job?job.log:'Your workspace is ready. Configure the architecture to begin.';if(bottom)el.scrollTop=el.scrollHeight;updateVerificationLog();}
function arrayFields(){const vals={rows:spec.fgra_num_row,cols:spec.fgra_num_colum,bank:2**spec.spad_bank_lg_size/1024,'cg-tracks':spec.fgra_gib_num_track_cg,'fg-tracks':spec.fgra_gib_num_track_fg};for(const [id,v]of Object.entries(vals))$(id).value=v;coalesceOptions();}
function coalesceOptions(){const col=spec.fgra_num_colum;$('coalesce').innerHTML=Array.from({length:col},(_,i)=>i+1).filter(i=>col%i===0).map(i=>`<option>${i}</option>`).join('');$('coalesce').value=spec.fgra_iob_sram_banks_coalesce;}
function resizeGrid(grid,rows,cols,fallback){return Array.from({length:rows},(_,r)=>Array.from({length:cols},(_,c)=>clone((grid[r]||[])[c]||fallback)));}
function resizeArray(rows,cols){spec.fgra_gpes=resizeGrid(spec.fgra_gpes,rows,cols,state.profiles.basic);spec.fgra_iobs=resizeGrid(spec.fgra_iobs,2,cols,spec.fgra_iobs[0][0]);spec.fgra_cg_gibs=resizeGrid(spec.fgra_cg_gibs,rows+1,cols+1,{diag_iopin_connect:true,fclist:[2,2,2]});spec.fgra_fg_gibs=resizeGrid(spec.fgra_fg_gibs,rows+1,cols+1,{diag_iopin_connect:true,fclist:[2,2,2]});spec.fgra_gpe_fg_rows=Array.from({length:rows},(_,i)=>i);spec.fgra_gpe_fg_columns=Array.from({length:cols},(_,i)=>i);spec.fgra_num_row=rows;spec.fgra_num_colum=cols;spec.spad_num_banks=cols*2;if(cols%spec.fgra_iob_sram_banks_coalesce)spec.fgra_iob_sram_banks_coalesce=cols;selected={type:'pe',r:Math.min(selected.r,rows-1),c:Math.min(selected.c,cols-1)};coalesceOptions();instancePanel();}
async function saveDraft(){await api('draft',{spec});draftPending=false;await refresh();}
function changed(){draftPending=true;state.dirty=true;flow();status('spec-status','Draft changes','warning');$('generate-rtl').disabled=true;$('save-spec').disabled=true;drawArchitecture('hw-canvas',spec,false,true);clearTimeout(draftTimer);draftTimer=setTimeout(()=>action(saveDraft),400);}
for(const id of ['rows','cols','bank','cg-tracks','fg-tracks'])$(id).onchange=()=>{if(state.active){arrayFields();return;}const el=$(id),v=Number(el.value);let valid=Number.isFinite(v)&&v>=0;if(id==='rows'||id==='cols')valid=Number.isInteger(v)&&v>=1&&v<=32;else if(id==='bank')valid=v>=.015625&&v<=16384&&Number.isInteger(Math.log2(v*1024));else valid=Number.isInteger(v)&&v<=32;el.classList.toggle('invalid',!valid);if(!valid){notice('Enter a valid value. Dimensions: 1–32; tracks: 0–32; bank capacity: a power of two.');return;}notice('');if(id==='rows'||id==='cols')resizeArray(id==='rows'?v:spec.fgra_num_row,id==='cols'?v:spec.fgra_num_colum);else if(id==='bank')spec.spad_bank_lg_size=Math.log2(v*1024);else spec[id==='cg-tracks'?'fgra_gib_num_track_cg':'fgra_gib_num_track_fg']=v;changed();};
$('coalesce').onchange=()=>{if(!state.active){spec.fgra_iob_sram_banks_coalesce=Number($('coalesce').value);changed();}};
function peName(pe){return pe.gpe_mode===2?'XCore':pe.gpe_mode===1?(pe.num_input_lut?'PC-F-PE':'PC-PE'):pe.num_input_lut?'F-PE':'C-PE';}
function selectedCell(){return selected.type==='pe'?spec.fgra_gpes[selected.r][selected.c]:selected.type==='iob'?spec.fgra_iobs[selected.r][selected.c]:spec.fgra_cg_gibs[selected.r][selected.c];}
function fgGibCell(r,c){
    const rows=[...spec.fgra_gpe_fg_rows,spec.fgra_num_row];
    const cols=[...spec.fgra_gpe_fg_columns,spec.fgra_num_colum];
    return (spec.fgra_fg_gibs[rows.indexOf(r)]||[])[cols.indexOf(c)];
}
function captureInstance(){
    return {type:selected.type,cell:clone(selectedCell()),
        fg:selected.type==='gib'&&fgGibCell(selected.r,selected.c)?clone(fgGibCell(selected.r,selected.c)):null};
}
function applyInstance(config,all=false){
    if(state.active||config.type!==selected.type)return false;
    const grids={pe:'fgra_gpes',iob:'fgra_iobs',gib:'fgra_cg_gibs'};
    const key=grids[config.type];
    if(all)spec[key]=spec[key].map(row=>row.map(()=>clone(config.cell)));
    else spec[key][selected.r][selected.c]=clone(config.cell);
    if(config.type==='gib'&&config.fg){
        if(all)spec.fgra_fg_gibs=spec.fgra_fg_gibs.map(row=>row.map(()=>clone(config.fg)));
        else {const target=fgGibCell(selected.r,selected.c);if(target)Object.assign(target,clone(config.fg));}
    }
    changed();
    return true;
}
function bindInstanceActions(body){
    const active=paint&&paint.type===selected.type;
    const name={pe:'PEs',iob:'IOBs',gib:'GIBs'}[selected.type];
    body.insertAdjacentHTML('beforeend',`<div class="instance-actions"><button id="paint" class="small ${active?'paint-active':''}">${active?'Brush active · Esc to stop':'◩ Format brush'}</button><button id="homogeneous" class="small">Apply to all ${name}</button></div>`);
    if(selected.type==='gib')body.insertAdjacentHTML('beforeend','<p class="muted">Copies CG settings and, when present, FG settings to existing GIBs.</p>');
    $('paint').onclick=()=>{if(state.active)return;paint=active?null:captureInstance();instancePanel();};
    $('homogeneous').onclick=()=>{if(applyInstance(captureInstance(),true))instancePanel();};
    if(state.active)body.querySelectorAll('input,select,button').forEach(el=>el.disabled=true);
}
function inputField(label,id,value,min=0){return `<label>${label}<input type="number" id="${id}" min="${min}" value="${value}"></label>`;}
function instancePanel(){const {type,r,c}=selected;$('instance-coordinate').textContent=`${type==='iob'?(r?'BOTTOM':'TOP'):r} · ${c}`;$('instance-title').textContent=type==='pe'?'PE configuration':type==='gib'?'GIB configuration':'IOB configuration';const body=$('instance-settings'),cell=selectedCell();if(type==='pe'){const mode=cell.gpe_mode,lut=cell.num_input_lut;const groups={'Integer & compare':[], 'Logic & shifts':[], 'Floating point':[], 'Accumulation & control':[]};for(const op of state.operations){if(op==='XCORE')continue;const group=op.startsWith('F')?'Floating point':/^(A(?!DD|ND|SHR)|C(?!SH)|I(?!N))/.test(op)||['SEL','SEXT','ZEXT','MAC'].includes(op)?'Accumulation & control':/AND|OR|NOT|SH[LR]|LSHR|EQ|NE|PASS/.test(op)?'Logic & shifts':'Integer & compare';groups[group].push(op);}body.innerHTML=`<label>Tile type<select id="pe-type">${['C-PE','F-PE','PC-PE','PC-F-PE','XCore'].map(v=>`<option ${peName(cell)===v?'selected':''}>${v}</option>`).join('')}</select></label><div class="fields">${inputField('LUT inputs','lut-inputs',lut)}${inputField('CG max delay','delay-cg',cell.max_delay_cg)}${inputField('FG max delay','delay-fg',cell.max_delay_fg)}</div><div class="operation-list">${Object.entries(groups).map(([title,ops])=>`<div class="operation-group"><h3>${title}</h3><div class="operation-options">${ops.map(op=>`<label class="op-choice"><input type="checkbox" data-op="${op}" ${cell.operations.includes(op)?'checked':''} ${mode?'disabled':''}>${op}</label>`).join('')}</div></div>`).join('')}</div>${mode?'<p class="muted">Operations are fixed by the selected PE profile.</p>':''}`;$('lut-inputs').disabled=mode===2||peName(cell)==='C-PE'||peName(cell)==='PC-PE';$('pe-type').onchange=()=>{if(state.active)return;const kind=$('pe-type').value,previous=clone(cell);Object.assign(cell,clone(kind==='XCore'?state.profiles.xcore:kind.startsWith('PC')?state.profiles.unified:state.profiles.basic));if(kind==='F-PE'||kind==='PC-F-PE')cell.num_input_lut=previous.num_input_lut||2;changed();instancePanel();};for(const [id,key]of [['lut-inputs','num_input_lut'],['delay-cg','max_delay_cg'],['delay-fg','max_delay_fg']])$(id).onchange=()=>{const v=Number($(id).value),valid=Number.isInteger(v)&&v>=0&&(id!=='lut-inputs'||v<=8);$(id).classList.toggle('invalid',!valid);if(valid&&!state.active){cell[key]=v;changed();}};body.querySelectorAll('[data-op]').forEach(input=>input.onchange=()=>{if(state.active)return;cell.operations=input.checked?[...cell.operations,input.dataset.op]:cell.operations.filter(op=>op!==input.dataset.op);if(!cell.operations.length){input.checked=true;cell.operations=[input.dataset.op];notice('A PE must support at least one operation.');return;}changed();});}
else if(type==='gib'){const fg=fgGibCell(r,c);body.innerHTML=`<p class="muted">Connection flexibility per pin. Track access and local pin connections are configured independently.</p>${[['CG',cell],['FG',fg]].filter(x=>x[1]).map(([grain,gib])=>`<div class="operation-group"><h3>${grain} connections</h3><div class="fields">${gib.fclist.map((v,i)=>inputField(['Tracks → input','Output → tracks','Output → input'][i],grain+'-fc-'+i,v)).join('')}</div><label><input type="checkbox" id="${grain}-diag" ${gib.diag_iopin_connect?'checked':''}> Diagonal pin connections</label></div>`).join('')}`;for(const [grain,gib]of [['CG',cell],['FG',fg]])if(gib){gib.fclist.forEach((v,i)=>$(grain+'-fc-'+i).onchange=()=>{const input=$(grain+'-fc-'+i),n=Number(input.value),valid=Number.isInteger(n)&&n>=0;input.classList.toggle('invalid',!valid);if(valid&&!state.active){gib.fclist[i]=n;changed();}});$(grain+'-diag').onchange=()=>{if(!state.active){gib.diag_iopin_connect=$(grain+'-diag').checked;changed();}};}}
else{body.innerHTML=`<label>IOB mode<select id="iob-mode"><option value="1">FIFO</option><option value="2">SRAM</option><option value="3">Task condition exit</option></select></label><div class="fields">${inputField('CG max delay','iob-cg',cell.max_delay_cg)}${inputField('FG max delay','iob-fg',cell.max_delay_fg)}</div><label><input id="iob-fg-enable" type="checkbox" ${cell.has_io_fg?'checked':''}> Fine-grained IO</label>`;$('iob-mode').value=cell.iob_mode;$('iob-mode').onchange=()=>{if(!state.active){cell.iob_mode=Number($('iob-mode').value);changed();}};$('iob-fg-enable').onchange=()=>{if(!state.active){cell.has_io_fg=$('iob-fg-enable').checked;changed();}};for(const [id,key]of [['iob-cg','max_delay_cg'],['iob-fg','max_delay_fg']])$(id).onchange=()=>{const n=Number($(id).value),valid=Number.isInteger(n)&&n>=0;$(id).classList.toggle('invalid',!valid);if(valid&&!state.active){cell[key]=n;changed();}};}bindInstanceActions(body);}
const views={};
function viewport(container,svg,preserve=false){const box=svg.getAttribute('viewBox').split(/\s+/).map(Number),id=container.id;let view=preserve&&views[id]?views[id]:box.slice();const apply=()=>{svg.setAttribute('viewBox',view.join(' '));views[id]=view;};apply();container.onwheel=e=>{e.preventDefault();const rect=container.getBoundingClientRect(),scale=e.deltaY>0?1.12:.89,u=(e.clientX-rect.left)/rect.width,v=(e.clientY-rect.top)/rect.height;view=[view[0]+view[2]*u*(1-scale),view[1]+view[3]*v*(1-scale),view[2]*scale,view[3]*scale];apply();};let down=null;container._moved=false;container.onpointerdown=e=>{if(e.button!==0)return;down={x:e.clientX,y:e.clientY,view:view.slice()};container._moved=false;};container.onpointermove=e=>{if(!down)return;const dx=e.clientX-down.x,dy=e.clientY-down.y;if(Math.abs(dx)+Math.abs(dy)>4)container._moved=true;if(container._moved){const rect=container.getBoundingClientRect();view=[down.view[0]-dx/rect.width*down.view[2],down.view[1]-dy/rect.height*down.view[3],view[2],view[3]];apply();}};container.onpointerup=()=>{down=null;};container.onpointerleave=()=>{down=null;};if(!container._capture){container.addEventListener('click',e=>{if(container._moved){e.stopPropagation();container._moved=false;}},{capture:true});container._capture=true;}return()=>{view=box.slice();apply();};}
function architecturePosition(type,r,c){const gap=106,x=65+c*gap,y=135+r*gap;return type==='pe'?[x+gap/2,y+gap/2]:type==='iob'?[x+gap/2,r===0?85:135+spec.fgra_num_row*gap+50]:[x,y];}
function drawArchitecture(id,s,mapping,preserve=false){const el=$(id),rows=s.fgra_num_row,cols=s.fgra_num_colum,w=130+cols*106,h=270+rows*106;const cg=$(mapping?'map-cg':'show-cg').checked,fg=$(mapping?'map-fg':'show-fg').checked;let out=`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" role="img" aria-label="CGRA architecture"><defs><marker id="arrow-${id}" markerUnits="userSpaceOnUse" markerWidth="5" markerHeight="5" viewBox="0 0 5 5" refX="4.5" refY="2.5" orient="auto"><path d="M0 0 L5 2.5 L0 5" fill="context-stroke"/></marker></defs><rect x="40" y="15" width="${w-80}" height="34" rx="7" fill="#edf1f7"/><text x="${w/2}" y="37" text-anchor="middle" fill="#8190a5" font-size="11">MULTIBANK SCRATCHPAD MEMORY</text><rect x="40" y="${h-49}" width="${w-80}" height="34" rx="7" fill="#edf1f7"/><text x="${w/2}" y="${h-27}" text-anchor="middle" fill="#8190a5" font-size="11">MULTIBANK SCRATCHPAD MEMORY</text>`;
const position=(type,r,c)=>{const x=65+c*106,y=135+r*106;return type==='pe'?[x+53,y+53]:type==='iob'?[x+53,r===0?85:135+rows*106+50]:[x,y];};
function line(a,b,color='#bac6d7',dash=false,tracks=1){if(!tracks)return;const dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy),nx=-dy/len,ny=dx/len;for(let t=0;t<tracks;t++){const offset=(t-(tracks-1)/2)*3+(dash?2:0);out+=`<line x1="${a[0]+nx*offset}" y1="${a[1]+ny*offset}" x2="${b[0]+nx*offset}" y2="${b[1]+ny*offset}" stroke="${color}" stroke-width="${mapping?.8:1.2}" ${dash?'stroke-dasharray="4 4"':''}/>`;}}
if(cg)for(let r=0;r<=rows;r++)for(let c=0;c<=cols;c++){if(c<cols)line(position('gib',r,c),position('gib',r,c+1),'#b1bdcc',false,s.fgra_gib_num_track_cg);if(r<rows)line(position('gib',r,c),position('gib',r+1,c),'#b1bdcc',false,s.fgra_gib_num_track_cg);}
const fgRows=[...s.fgra_gpe_fg_rows,rows],fgCols=[...s.fgra_gpe_fg_columns,cols];if(fg)for(let i=0;i<fgRows.length;i++)for(let j=0;j<fgCols.length;j++){const a=position('gib',fgRows[i],fgCols[j]);if(j+1<fgCols.length)line(a,position('gib',fgRows[i],fgCols[j+1]),'#b6a8cf',true,s.fgra_gib_num_track_fg);if(i+1<fgRows.length)line(a,position('gib',fgRows[i+1],fgCols[j]),'#b6a8cf',true,s.fgra_gib_num_track_fg);}
for(let r=0;r<rows;r++)for(let c=0;c<cols;c++){const pe=s.fgra_gpes[r][c],a=position('pe',r,c);for(const [dr,dc]of [[0,0],[0,1],[1,0],[1,1]]){if(cg)line(a,position('gib',r+dr,c+dc));if(fg&&pe.gpe_mode!==2&&s.fgra_gpe_fg_rows.includes(r)&&s.fgra_gpe_fg_columns.includes(c)&&(pe.num_input_lut||pe.operations.some(op=>/SEL|ACC|EQ|LT|LE|ADD/.test(op))))line(a,position('gib',r+dr,c+dc),'#b6a8cf',true);}}
for(let side=0;side<2;side++)for(let c=0;c<cols;c++){const a=position('iob',side,c),r=side?rows:0;if(cg){line(a,position('gib',r,c));line(a,position('gib',r,c+1));}if(fg&&s.fgra_iobs[side][c].has_io_fg){line(a,position('gib',r,c),'#b6a8cf',true);line(a,position('gib',r,c+1),'#b6a8cf',true);}line(a,[a[0],side?h-49:49],'#c3ccd8');}
let mappedLabels={},mappedPaths=[];if(mapping&&mapped&&adg){const ids=Object.fromEntries(adg.instances.filter(n=>n.type!=='This').map(n=>[n.id,n]));const coords={};const axes={};for(const type of ['GPE','CGGIB','FGGIB']){const entries=adg.instances.filter(n=>n.type===type);axes[type]={x:[...new Set(entries.map(n=>n.x))].sort((a,b)=>a-b),y:[...new Set(entries.map(n=>n.y))].sort((a,b)=>a-b)};}for(const n of mapped.objects||[]){const match=n.name && n.name.match(/(\d+)$/),inst=match?ids[Number(match[1])]:null;if(!inst)continue;let type,r,c;if(inst.type==='GPE'){type='pe';r=axes.GPE.x.indexOf(inst.x);c=axes.GPE.y.indexOf(inst.y);}else if(inst.type==='IOB'){type='iob';r=inst.iob_index>=cols?1:0;c=inst.iob_index%cols;}else{type='gib';if(inst.type==='FGGIB'){r=fgRows[axes.FGGIB.x.indexOf(inst.x)];c=fgCols[axes.FGGIB.y.indexOf(inst.y)];}else{r=axes.CGGIB.x.indexOf(inst.x);c=axes.CGGIB.y.indexOf(inst.y);}}if(!Number.isFinite(r)||!Number.isFinite(c))continue;coords[n._gvid]={pos:position(type,r,c),type,r,c,grain:inst.type==='FGGIB'?'fg':'cg'};if(n.label && n.label.includes('DFG:'))mappedLabels[`${type}:${r}:${c}`]=n.label.split(/\\n|\n/).filter(x=>x.includes('DFG:')).map(x=>x.replace('DFG:','')).join(' → ');}for(const e of mapped.edges||[]){if(!e.color||e.color==='gray80')continue;const a=coords[e.tail],b=coords[e.head];if(!a||!b)continue;const fine=a.grain==='fg'||b.grain==='fg';if(fine&&!fg||!fine&&!cg)continue;mappedPaths.push({a,b,e,fine});}const colors=['#4779d3','#e69e49','#a179be','#42a389','#da718e','#6f8aab'];mappedPaths.forEach(({a,b,e,fine},i)=>{const dx=b.pos[0]-a.pos[0],dy=b.pos[1]-a.pos[1],len=Math.hypot(dx,dy)||1,ra=a.type==='gib'?18:a.type==='iob'?23:29,rb=b.type==='gib'?19:b.type==='iob'?24:30;out+=`<line x1="${a.pos[0]+dx/len*ra}" y1="${a.pos[1]+dy/len*ra}" x2="${b.pos[0]-dx/len*rb}" y2="${b.pos[1]-dy/len*rb}" stroke="${colors[(Number(e.color)||i)%colors.length]}" stroke-width="1.2" stroke-linecap="round" ${fine?'stroke-dasharray="5 4"':''} marker-end="url(#arrow-${id})"/>`;});}
function tile(type,r,c,name,color,radius){const [x,y]=position(type,r,c),key=`${type}:${r}:${c}`,label=mappedLabels[key],isSelected=!mapping&&selected.type===type&&selected.r===r&&selected.c===c;out+=`<g class="tile ${isSelected?'selected':''}" data-type="${type}" data-r="${r}" data-c="${c}" data-label="${esc(label||'Unmapped resource')}"><title>${esc(name)} (${r}, ${c})${label?': '+esc(label):''}</title><circle cx="${x}" cy="${y}" r="${radius}" fill="${mapping&&!label?'#f3f5f8':color}" stroke="${label?'#4779d3':'#d7dfe9'}" stroke-width="${label?2:1.2}"/><text x="${x}" y="${y+3}" text-anchor="middle" font-size="${type==='gib'?7:9}" fill="#53647e" font-weight="600">${esc(name)}</text>${type==='pe'?`<text x="${x}" y="${y+radius+13}" text-anchor="middle" font-size="8" fill="#96a2b1">${label?esc(label.length>23?label.slice(0,21)+'…':label):r+', '+c}</text>`:''}</g>`;}
for(let r=0;r<=rows;r++)for(let c=0;c<=cols;c++)tile('gib',r,c,fgRows.includes(r)&&fgCols.includes(c)?'F/C-GIB':'C-GIB','#f0f2f7',17);
for(let r=0;r<rows;r++)for(let c=0;c<cols;c++){const pe=s.fgra_gpes[r][c];tile('pe',r,c,peName(pe),pe.gpe_mode===2?'#f8efdb':pe.gpe_mode===1?'#e8e5f5':pe.num_input_lut?'#f4e6f1':'#e7eef9',28);}
for(let side=0;side<2;side++)for(let c=0;c<cols;c++)tile('iob',side,c,'IOB','#e4f2ef',22);out+='</svg>';el.innerHTML=out;const fit=viewport(el,el.querySelector('svg'),preserve);$(mapping?'map-fit':'hw-fit').onclick=fit;el.querySelectorAll('.tile').forEach(tile=>tile.onclick=()=>{if(mapping){el.querySelectorAll('.selected').forEach(t=>t.classList.remove('selected'));tile.classList.add('selected');$('mapping-selection').textContent=`${tile.dataset.type.toUpperCase()} (${tile.dataset.r}, ${tile.dataset.c}) · ${tile.dataset.label}`;return;}selected={type:tile.dataset.type,r:Number(tile.dataset.r),c:Number(tile.dataset.c)};if(paint&&paint.type===selected.type&&!state.active){applyInstance(paint);}else drawArchitecture(id,s,false,true);instancePanel();});if(!mapping)$('array-summary').textContent=`${rows} × ${cols} array · ${rows*cols} processing elements · ${cols*2} IOBs`;}
function mappingUtilization(graph,architecture){
    const instances=architecture.instances.filter(n=>n.type!=='This'),ids=new Map(instances.map(n=>[n.id,n]));
    const used=new Set();
    for(const object of graph.objects||[]){
        if(!object.label||!object.label.includes('DFG:'))continue;
        const match=(object.name||'').match(/(\d+)$/);
        if(match&&ids.has(Number(match[1])))used.add(Number(match[1]));
    }
    const count=type=>({used:instances.filter(n=>n.type===type&&used.has(n.id)).length,total:instances.filter(n=>n.type===type).length});
    return {pe:count('GPE'),io:count('IOB')};
}
function updateUtilization(valid){
    const usage=valid&&mapped&&adg?mappingUtilization(mapped,adg):null;
    for(const type of ['pe','io']){
        const count=usage&&usage[type];
        $(type+'-usage').textContent=count&&count.total?(100*count.used/count.total).toFixed(1)+'%':'--';
        $(type+'-count').textContent=count?count.used+' / '+count.total+' used':'';
    }
}
function drawMap(){const result=state.mapping[$('mapping-program').value];updateUtilization(result&&result.current&&mapJob===result.job);drawArchitecture('map-canvas',state.spec,true,true);}
for(const id of ['show-cg','show-fg'])$(id).onchange=()=>drawArchitecture('hw-canvas',spec,false,true);for(const id of ['map-cg','map-fg'])$(id).onchange=drawMap;
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&paint){paint=null;instancePanel();}if((e.ctrlKey||e.metaKey)&&e.key==='s'&&(page==='compile'||page==='verification')){e.preventDefault();$(page==='compile'?'save-source':'save-verification-source').click();}});
$('load-spec').onclick=()=>action(async()=>{
    clearTimeout(draftTimer);
    // Flush a pending local edit first so a delayed draft save cannot overwrite the loaded spec.
    if(draftPending)await saveDraft();
    await api('load-spec',{name:$('spec-template').value});
    paint=null;selected={type:'pe',r:0,c:0};draftPending=false;
    $('hardware').querySelectorAll('.invalid').forEach(el=>el.classList.remove('invalid'));
    await refresh();
    spec=clone(state.draft);arrayFields();drawArchitecture('hw-canvas',spec,false);instancePanel();
    notice(`Loaded ${state.loaded_template}. Generate RTL if the architecture has changed.`);
});
$('generate-spec').onclick=()=>action(async()=>{if(document.querySelector('.invalid'))throw Error('Correct the highlighted configuration fields first.');clearTimeout(draftTimer);await api('spec',{spec});draftPending=false;await refresh();spec=clone(state.draft);notice('Architecture spec generated. Optionally save it as a template, or generate RTL to apply the design.');});
$('save-spec').onclick=()=>action(async()=>{
    if(document.querySelector('#hardware .invalid'))throw Error('Correct the highlighted configuration fields first.');
    if(state.dirty||draftPending)throw Error('Generate spec before saving changes.');
    const savedSpec=clone(state.spec),name=$('save-spec-name').value.trim();
    let result=await api('save-spec',{name,spec:savedSpec});
    if(result.exists){
        if(!window.confirm(`Spec "${result.name}" already exists. Overwrite it?`))return;
        result=await api('save-spec',{name:result.name,spec:savedSpec,overwrite:true});
    }
    await refresh();$('spec-template').value=result.name;$('save-spec-name').value=result.name;
    notice(`Saved hardware/spectemplate/${result.name}.`);
});
function highlightVerification(){
    const source=$('verification-source'),text=source.value;
    const regex=/("""[\s\S]*?"""|'''[\s\S]*?'''|#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:async|await|def|class|import|from|as|return|for|while|if|elif|else|in|not|and|or|is|None|True|False|assert|with|try|except|raise|pass|break|continue)\b|\b\d+(?:\.\d+)?\b)/g;
    let output='',last=0;
    for(const match of text.matchAll(regex)){
        const token=match[0],kind=token.startsWith('#')?'comment':/^['"]/.test(token)?'string':/^\d/.test(token)?'number':'keyword';
        output+=esc(text.slice(last,match.index))+`<span class="token-${kind}">${esc(token)}</span>`;last=match.index+token.length;
    }
    const pre=$('verification-highlight');pre.innerHTML=output+esc(text.slice(last))+'\n';
    pre.scrollTop=source.scrollTop;pre.scrollLeft=source.scrollLeft;
}
async function loadVerificationSource(){
    const name=$('verification-program').value;if(!name)return;
    const token=++verificationLoadToken,response=await api('verification-source?name='+encodeURIComponent(name));
    // A selection may have changed while the response was in flight.
    if(name!==$('verification-program').value||token!==verificationLoadToken||verificationDirty)return;
    verificationName=name;verificationOriginal=response.source;verificationDirty=false;verificationSaved=response.saved;
    $('verification-source').value=response.source;$('verification-title').textContent=name+' / test_cgra.py';
    $('verification-source-status').textContent=response.saved?'Saved':'Template · save before running';
    highlightVerification();
}
function updateVerificationControls(){
    const verification=state.verification||{},busy=!!state.active;
    $('build-verilator').disabled=busy||!state.rtl_current||state.dirty;
    $('verification-program').disabled=busy||!verification.built;
    $('verification-source').readOnly=busy||!verificationName;
    $('save-verification-source').disabled=busy||!verificationName;
    $('verification-run').disabled=busy||!verification.built||!verificationSaved||verificationDirty||!verificationName||verificationName!==$('verification-program').value||!(verification.benchmarks||[]).includes(verificationName);
    $('verification-stop').hidden=!(busy&&['verilator','verification'].includes(state.jobs[state.active].kind));
}
async function refreshVerification(){
    const verification=state.verification||{benchmarks:[]};
    if(!verificationDirty)fillPrograms('verification-program',verification.benchmarks||[]);
    const model=verification.build,job=latestJob('verilator');
    if(job&&job.status==='running')status('verilator-status','Building · '+job.elapsed+' s','running');
    else if(verification.built)status('verilator-status','Built','success');
    else if(job&&job.status==='failed')status('verilator-status','Build failed','failed');
    else status('verilator-status',model?'Model outdated · rebuild required':'Not built',model?'warning':'');
    if(page==='verification'&&verification.built&&$('verification-program').value!==verificationName&&!verificationDirty)await loadVerificationSource();
    if(!verificationName&&verification.built&&!(verification.benchmarks||[]).length)$('verification-source-status').textContent='Map a benchmark with Cocotb or All backends first.';
    updateVerificationControls();updateVerificationLog();
}
function updateVerificationLog(){
    if(!state)return;
    const active=state.active&&state.jobs[state.active],run=latestJob('verification',$('verification-program').value),build=latestJob('verilator');
    const job=active&&['verification','verilator'].includes(active.kind)?active:run&&(!build||run.created>=build.created)?run:build;
    const log=$('verification-log'),bottom=log.scrollTop+log.clientHeight>=log.scrollHeight-25;
    log.textContent=job?job.log:'Build the Verilator model, select a mapped benchmark and save the test script.';
    $('verification-log-label').textContent=job?`${job.kind==='verilator'?'BUILD':'RUN'} · ${job.status} · ${job.elapsed} s`:'Ready';
    if(bottom)log.scrollTop=log.scrollHeight;
}
$('verification-program').onchange=()=>action(async()=>{
    if(verificationDirty){$('verification-program').value=verificationName;throw Error('Save test changes before switching benchmarks.');}
    await loadVerificationSource();await saveUi();updateVerificationControls();updateVerificationLog();
});
$('verification-source').oninput=()=>{
    verificationDirty=$('verification-source').value!==verificationOriginal;
    $('verification-source-status').textContent=verificationDirty?'Unsaved changes':verificationSaved?'Saved':'Template · save before running';
    highlightVerification();updateVerificationControls();
};
$('verification-source').onscroll=highlightVerification;
$('verification-source').onkeydown=e=>{if(e.key==='Tab'){e.preventDefault();const el=$('verification-source');el.setRangeText('    ',el.selectionStart,el.selectionEnd,'end');el.dispatchEvent(new Event('input'));}};
$('save-verification-source').onclick=()=>action(async()=>{
    const source=$('verification-source').value;
    await api('verification-source',{name:verificationName,source});
    verificationOriginal=source;verificationDirty=$('verification-source').value!==source;verificationSaved=true;
    $('verification-source-status').textContent=verificationDirty?'Unsaved changes':'Saved';await refresh();
});
$('build-verilator').onclick=()=>action(()=>runTask('verilator'));
$('verification-run').onclick=()=>action(()=>runTask('verification'));
$('verification-stop').onclick=()=>action(()=>api('cancel',{}));
async function runTask(kind){if(kind==='compile'&&$('source').value!==sourceOriginal)throw Error('Save your source changes before compiling.');if(kind==='verification'&&(verificationDirty||!verificationSaved))throw Error('Save the test script before running.');const result=await api('run',{kind,test_source:kind==='verification'?$('verification-source').value:undefined,name:kind==='compile'?$('compile-program').value:kind==='verification'?$('verification-program').value:$('mapping-program').value,compiler:$('compiler').value,kernel:$('kernel').value,backend:$('backend').value});currentJob=result.id;await refresh();if(result.cached)notice(result.message);}
$('generate-rtl').onclick=()=>action(()=>runTask('rtl'));$('compile-button').onclick=()=>action(()=>runTask('compile'));$('map-button').onclick=()=>action(()=>runTask('mapping'));$('cancel').onclick=()=>action(()=>api('cancel',{}));
function highlight(){const text=$('source').value;const regex=/(\/\*[\s\S]*?\*\/|\/\/[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:int|float|double|void|char|short|long|unsigned|signed|const|static|volatile|restrict|return|for|while|if|else|break|continue|struct|typedef|sizeof|include|define|bool)\b|\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?[fFuUlL]*\b)/g;let output='',last=0;for(const m of text.matchAll(regex)){output+=esc(text.slice(last,m.index));const token=m[0],cls=token.startsWith('//')||token.startsWith('/*')?'comment':/^['"]/.test(token)?'string':/^\d/.test(token)?'number':'keyword';output+=`<span class="token-${cls}">${esc(token)}</span>`;last=m.index+token.length;}$('code-highlight').innerHTML=output+esc(text.slice(last))+'\n';$('code-highlight').scrollTop=$('source').scrollTop;$('code-highlight').scrollLeft=$('source').scrollLeft;}
async function saveUi(){await api('ui',{program:$('compile-program').value,mapping_program:$('mapping-program').value,compiler:$('compiler').value,kernel:$('kernel').value,backend:$('backend').value,verification_program:$('verification-program').value});}
async function loadSource(){const name=$('compile-program').value;if(!name)return;const response=await api('source?name='+encodeURIComponent(name));loadedProgram=name;sourceOriginal=response.source;$('source').value=response.source;$('source-title').textContent=name+'.c';$('source-status').textContent='Saved';editing=false;highlight();}
$('source').oninput=()=>{editing=$('source').value!==sourceOriginal;$('source-status').textContent=editing?'Unsaved changes':'Saved';highlight();};$('source').onscroll=highlight;$('source').onkeydown=e=>{if(e.key==='Tab'){e.preventDefault();const el=$('source'),a=el.selectionStart,b=el.selectionEnd;el.setRangeText('    ',a,b,'end');el.dispatchEvent(new Event('input'));}};
$('save-source').onclick=()=>action(async()=>{await api('source',{name:loadedProgram,source:$('source').value});sourceOriginal=$('source').value;editing=false;$('source-status').textContent='Saved';await refresh();});
$('compile-program').onchange=()=>action(async()=>{if(editing){$('compile-program').value=loadedProgram;throw Error('Save source changes before switching programs.');}await loadSource();await saveUi();await refresh();});$('mapping-program').onchange=()=>{mapJob='';mapped=null;action(async()=>{await saveUi();await refresh();});};$('compiler').onchange=()=>{$('kernel').disabled=$('compiler').value==='mlir';action(saveUi);};$('kernel').onchange=()=>action(saveUi);$('backend').onchange=()=>action(saveUi);
$('new-program').onclick=()=>{if(editing){notice('Save source changes before creating a new program.');return;}$('new-name').value='';$('new-dialog').showModal();};$('close-dialog').onclick=()=>$('new-dialog').close();$('new-form').onsubmit=e=>{e.preventDefault();action(async()=>{const name=$('new-name').value;await api('new',{name});$('new-dialog').close();await refresh();$('compile-program').value=name;await loadSource();});};
async function loadDFG(url){const response=await fetch(url);if(!response.ok)throw Error('Unable to load the DFG visualization');const xml=new DOMParser().parseFromString(await response.text(),'image/svg+xml'),svg=xml.documentElement;svg.querySelectorAll('script,foreignObject').forEach(n=>n.remove());svg.querySelectorAll('*').forEach(n=>{for(const attr of [...n.attributes])if(attr.name.startsWith('on')||attr.name.includes('href'))n.removeAttribute(attr.name);});const container=$('dfg-canvas');container.replaceChildren(document.importNode(svg,true));const rendered=container.querySelector('svg');$('dfg-fit').onclick=viewport(container,rendered);rendered.querySelectorAll('.node').forEach(node=>node.onclick=()=>{const name=(node.querySelector('title')||{}).textContent;rendered.querySelectorAll('.highlight').forEach(n=>n.classList.remove('highlight'));node.classList.add('highlight');rendered.querySelectorAll('.edge').forEach(edge=>{const title=(edge.querySelector('title')||{}).textContent||'';if(title.split('->').some(n=>n.split(':')[0]===name))edge.classList.add('highlight');});});}
$('toggle-log').onclick=()=>{const expand=$('log').hidden;$('log').hidden=!expand;document.querySelector('main').classList.toggle('log-collapsed',!expand);$('toggle-log').textContent=expand?'Collapse':'Expand';$('toggle-log').setAttribute('aria-expanded',String(expand));if(expand)$('log').scrollTop=$('log').scrollHeight;};
action(async()=>{await refresh(true);setInterval(()=>refresh().catch(error=>notice(error.message)),1500);});
