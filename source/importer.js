const importButton=document.createElement('button');importButton.id='importPob';importButton.className='iconlabel';importButton.innerHTML=uiIcon('builds')+'<span>Manage builds</span>';document.querySelector('.topactions').append(importButton);
let importPreview=null;
async function importRequest(path,body){const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await response.json();if(!response.ok){const error=Error(data.error||'Import failed.');error.details=data;throw error;}return data;}
function importMessage(message,error=false){const status=$('importStatus');if(status){status.textContent=message;status.classList.toggle('importerror',error);}}
async function openImporter(){
 record('Build library & PoB importer',`<div class="importstart"><div><p class="eyebrow">Create a local guide</p><h3>Paste a PoB code or pobb.in link</h3><p>Your build is parsed locally. A link downloads its public export; raw codes need no upload or account login. PoE 1 only.</p><label class="sr-only" for="pobInput">PoB export code, XML or pobb.in link</label><textarea id="pobInput" placeholder="https://pobb.in/… or paste the full export code" spellcheck="false" maxlength="12000000"></textarea><button id="previewPob">Read build & review milestones →</button><p id="importStatus" role="status"></p></div><aside><h3>Saved guides</h3><a href="/?library=1">All saved builds ↗</a><div id="libraryStatus" role="status"></div><div id="savedBuilds">Loading local library…</div><details id="removedBuilds"><summary>Recently removed</summary><div id="removedBuildList"></div></details><p class="muted">Gems you own stay saved per character when you switch guides.</p></aside></div>`);
 if(location.protocol==='file:'){importMessage('Start the local companion to use the importer.',true);$('previewPob').disabled=true;return;}
 await renderBuildLibrary();
 try{const response=await fetch('/api/gem-coverage');const data=await response.json();if($('pobInput')){const coverage=document.createElement('p');coverage.className='gemcoverage';coverage.textContent=`${data.classes.length} PoE 1 classes · ${data.gems} gem variants · class-specific vendors, free rewards and special acquisition`;coverage.title=data.classes.join(', ');$('pobInput').before(coverage);}}catch{}
}
function importReview(preview){
 importPreview=preview;
 const options=(list,value,empty)=>`<option value="">${empty}</option>`+list.map(x=>`<option value="${esc(x.id)}" ${x.id===value?'selected':''}>${esc(x.title)}</option>`).join('')+(empty.startsWith('Choose tree')?'<option value="none">No passive tree</option>':'');
 record('Review your imported guide',`<div class="importreview"><p class="eyebrow">${esc(preview.className)} · ${esc(preview.ascendancy)} · ${preview.skills.length} skill sets</p><p>Confirm the starting level and the skills, tree and gear for each step. Uncheck budget variants you do not want. Levels from build labels are preserved. Unlabelled steps use a tree-based estimate, assuming typical quest rewards. Adjust these to your plan; each included step needs a higher starting level than the previous one.</p>${preview.warnings.length?`<div class="importwarnings">${preview.warnings.map(w=>`<p>• ${esc(w)}</p>`).join('')}</div>`:''}<label class="importname">Guide name<input id="guideName" maxlength="120" value="${esc((preview.ascendancy||preview.className)+' leveling guide')}"></label><div class="importrows"><div class="importrow importrowhead"><span>Use</span><span>Milestone label</span><span>From level</span><span>Skills</span><span>Passive tree</span><span>Equipment</span></div>${preview.milestones.map((m,i)=>`<div class="importrow" data-import-row="${i}"><input type="checkbox" data-include ${m.included?'checked':''} aria-label="Include ${esc(m.label)}"><input data-label value="${esc(m.label)}" maxlength="160" aria-label="Milestone label"><div class="levelcell"><input data-level type="number" min="1" max="100" value="${m.startLevel||''}" aria-label="Starting level for ${esc(m.label)}"><small data-level-hint title="${esc(m.levelExplanation||'')}">${esc(m.levelSource||'Enter a level')}</small></div><select data-skills aria-label="Skill set">${options(preview.skills,m.skillSetId,'Choose skills')}</select><select data-tree aria-label="Passive tree set">${options(preview.trees,m.treeId,preview.trees.length?'Choose tree / none':'No tree supplied')}</select><select data-items aria-label="Equipment set">${options(preview.items,m.itemSetId,'No item targets')}</select></div>`).join('')}</div><p class="muted">Tree rendering uses the matching installed PoB tree version. Cluster expansions and Timeless transformations are flagged rather than guessed. Vendor routes without verified class data are marked for review.</p><div class="importactions"><button id="generatePob">Generate & open guide →</button><button id="importBack">Paste another build</button><span id="importStatus" role="status"></span></div></div>`);
}
importButton.addEventListener('click',openImporter);
document.addEventListener('click',async e=>{
 const gemButton=e.target.closest('[data-record-gem]');
 if(gemButton){
  const n=gemButton.dataset.recordGem,body=$('recordBody');
  if(body&&$('recordDialog').open){
   const extra=document.createElement('section');extra.className='acquisition-alternatives';
   const note=D.acquisitionNotes?.[n];
   const mule=n==='Momentum'&&earlyMomentum()?'<section class="mulingdetails"><h3>Optional: mule a Ranger</h3><p>Create a Ranger in the same league and mode, take Momentum from the Twilight Strand starting chest, defeat Hillock, then put the gem in the shared stash in Lioneye’s Watch. Collect it on your main character. This is a free alternative to buying it later; it requires shared stash access.</p></section>':'';
   extra.innerHTML=note?`<p class="importwarnings">${esc(note)}</p>`:'';
   extra.innerHTML+=mule;body.append(extra);
  }
 }
 if(D.imported&&e.target.closest('[data-record="sources"]'))record('Imported guide · Sources & limits',`<p>${esc(D.name)} · ${esc(D.build.className)} / ${esc(D.build.ascendClassName||'No ascendancy')} · Bandit: ${esc(D.build.bandit||'Not specified')}</p><p>Skills, enabled flags, gear variants and allocations come from your imported PoB. Gem use requirements and base-tree geometry are read from the installed Path of Building data. Verified acquisition entries are class-specific; other routes say they need review.</p><p>The tree uses native PoE node assets and compares saved allocations between steps. It does not simulate damage. Cluster expansions and Timeless transformations are not reconstructed. Open Imported Notes for the original author notes and any warnings.</p><p><a href="https://github.com/PathOfBuildingCommunity/PathOfBuilding" target="_blank" rel="noopener">Path of Building Community source</a></p>`);
 if(e.target.closest('#importBack'))openImporter();
 if(e.target.closest('#previewPob')){const button=$('previewPob');button.disabled=true;importMessage('Reading build…');try{const result=await importRequest('/api/import/preview',{input:$('pobInput').value});importReview(result);}catch(error){importMessage(error.message,true);button.disabled=false;}}
 if(e.target.closest('#generatePob')){
  const button=$('generatePob');button.disabled=true;
  const rows=Array.from(document.querySelectorAll('[data-import-row]')).filter(row=>row.querySelector('[data-include]').checked);
  document.querySelectorAll('[aria-invalid=true]').forEach(el=>el.removeAttribute('aria-invalid'));
  try{
   if(!rows.length)throw Error('Select at least one milestone to include in your guide.');
   const milestones=rows.map(row=>({label:row.querySelector('[data-label]').value,startLevel:Number(row.querySelector('[data-level]').value),skillSetId:row.querySelector('[data-skills]').value,treeId:row.querySelector('[data-tree]').value,itemSetId:row.querySelector('[data-items]').value}));
   milestones.forEach((m,i)=>{
    let message='',field='level';
    if(!Number.isInteger(m.startLevel)||m.startLevel<1||m.startLevel>100)message=`Enter a starting level for “${m.label}” between 1 and 100. Use the tree estimate as a guide.`;
    else if(i&&m.startLevel<=milestones[i-1].startLevel)message=`“${m.label}” starts at level ${m.startLevel}, but the previous step “${milestones[i-1].label}” starts at ${milestones[i-1].startLevel}. Raise this level or untick an alternative setup.`;
    else if(importPreview.trees.length&&!m.treeId){message=`Choose a passive tree for “${m.label}”, or select “No passive tree”.`;field='tree';}
    if(message){const error=Error(message);error.details={row:i,field};throw error;}
   });
   importMessage('Generating skills, item targets and passive trees…');
   const result=await importRequest('/api/import/generate',{draftId:importPreview.draftId,name:$('guideName').value,milestones});location.href='/guide?build='+encodeURIComponent(result.id);
  }catch(error){importMessage(error.message,true);const input=rows[error.details?.row]?.querySelector(`[data-${error.details?.field||'level'}]`);if(input){input.setAttribute('aria-invalid','true');input.focus();input.scrollIntoView({block:'center'});}button.disabled=false;}
 }
});
if(D.imported){
 document.body.classList.add('importedguide');
 const brand=document.querySelector('.brand strong');brand.textContent='LEAGUE START COMPANION';
 const notice=document.createElement('button');notice.id='importedNotes';notice.innerHTML=uiIcon('text')+'<span>Imported Notes</span>'+(D.warnings.length?' <span class=notecount>'+D.warnings.length+'</span>':'');notice.className='iconlabel';const placeNotes=()=>document.querySelector('.concepthero,.dashhero,.stagehero')?.append(notice);const beforeNotes=render;render=function(...args){beforeNotes(...args);placeNotes();};placeNotes();
 notice.addEventListener('click',()=>record(D.name+' · Imported Notes',`<p>${esc(D.name)} · ${esc(D.build.className)} / ${esc(D.build.ascendClassName||'No ascendancy')}</p>${D.warnings.map(w=>`<p class="importwarnings">${esc(w)}</p>`).join('')}<p>Blue = new nodes, gold = already allocated, red = removed. Native assets come from the matching installed PoB tree; ascendancy is shown separately. This view does not calculate damage or reconstruct cluster-jewel expansions or Timeless transformations.</p><h3>Original build notes</h3><pre class="importnotes">${esc(D.notes||'No notes supplied.')}</pre>`));
}

document.addEventListener('input',e=>{if(e.target.matches('[data-level]')){e.target.dataset.dirty='true';e.target.removeAttribute('aria-invalid');e.target.closest('.levelcell').querySelector('[data-level-hint]').textContent='Your level';}});
document.addEventListener('change',e=>{
 if(!e.target.matches('[data-tree]')||!importPreview)return;
 const row=e.target.closest('[data-import-row]'),input=row.querySelector('[data-level]'),milestone=importPreview.milestones[Number(row.dataset.importRow)];
 if(input.dataset.dirty||['Label','PoB character level'].includes(milestone.levelSource))return;
 const tree=importPreview.trees.find(t=>t.id===e.target.value),level=tree?.labelLevel||tree?.estimate?.level;
 input.value=level||'';const hint=row.querySelector('[data-level-hint]');hint.textContent=tree?.labelLevel?'Tree label':level?'Estimated from tree':'Enter a level';hint.title=tree?.estimate?.explanation||'';input.removeAttribute('aria-invalid');
});

async function renderBuildLibrary(){
 try{
  const response=await fetch('/api/builds',{cache:'no-store'});if(!response.ok)throw Error('Local library unavailable.');const data=await response.json();
  if(!$('savedBuilds'))return;
  const active=new URLSearchParams(location.search).get('build');
  $('savedBuilds').innerHTML=data.builds.length?data.builds.map(b=>`<article class="libraryrow" data-library-row="${b.id}"><a href="/guide?build=${b.id}">${esc(b.name)} ↗${active===b.id?'<small>Currently open</small>':''}</a><div class="libraryactions"><button data-build-rename="${b.id}" aria-label="Rename ${esc(b.name)}">Rename</button><button data-build-remove="${b.id}" aria-label="Remove ${esc(b.name)}">Remove</button></div><div class="libraryeditor" hidden><label>Build name<input data-build-name maxlength="120" value="${esc(b.name)}"></label><button data-build-save="${b.id}">Save name</button><button data-build-cancel>Cancel</button></div></article>`).join(''):'<p>No imported guides yet.</p>';
  const removed=data.removed||[];$('removedBuilds').hidden=!removed.length;
  $('removedBuildList').innerHTML=removed.map(b=>`<article class="libraryrow"><span>${esc(b.name)}</span><button data-build-restore="${b.id}">Restore</button></article>`).join('');
 }catch(error){if($('libraryStatus'))$('libraryStatus').textContent=error.message;}
}
document.addEventListener('click',async e=>{
 const rename=e.target.closest('[data-build-rename]');if(rename){const row=rename.closest('.libraryrow');row.querySelector('.libraryeditor').hidden=false;row.querySelector('[data-build-name]').focus();return;}
 const cancel=e.target.closest('[data-build-cancel]');if(cancel){cancel.closest('.libraryeditor').hidden=true;return;}
 const button=e.target.closest('[data-build-save],[data-build-remove],[data-build-restore]');if(!button)return;
 button.disabled=true;
 const action=button.hasAttribute('data-build-save')?'rename':button.hasAttribute('data-build-remove')?'remove':'restore';
 const id=button.dataset.buildSave||button.dataset.buildRemove||button.dataset.buildRestore;
 try{
  const name=action==='rename'?button.closest('.libraryrow').querySelector('[data-build-name]').value:undefined;
  const result=await importRequest('/api/builds/'+action,{id,name});
  if(action==='rename'&&D.id===id){D.name=result.name;designNames.board=result.name;render(current);}
  if(action==='remove'&&D.id===id){location.href='/?library=1&removedBuild='+encodeURIComponent(id);return;}
  await renderBuildLibrary();if(!D.sets.length)refreshLibraryHome();$('libraryStatus').textContent=action==='remove'?'Build removed. Restore it below in Recently removed.':action==='rename'?'Build renamed.':'Build restored.';
  if(action==='remove')$('removedBuilds').open=true;
 }catch(error){if($('libraryStatus'))$('libraryStatus').textContent=error.message;button.disabled=false;}
});
if(new URLSearchParams(location.search).has('removedBuild'))openImporter().then(()=>{if($('libraryStatus')){$('libraryStatus').textContent='Build removed. Your gem progress is saved. You can restore the build below.';$('removedBuilds').open=true;}history.replaceState(null,'',location.pathname+location.hash);});

function formatGemCost(cost){return cost?.amount?`${cost.amount} × ${cost.currency}`:'Cost not verified';}
function earlyMomentum(){const first=D.sets[0];return D.build.className!=='Ranger'&&first?.startLevel===1&&first.groups.some(g=>g.enabled!=='false'&&g.gems.some(gem=>gem.nameSpec==='Momentum'&&gem.enabled!=='false'));}
function acquisitionExtras(name,route){
 const siosa=route.vendor==='Siosa'?(D.acquisitionOptions?.[name]||[]).find(r=>r.vendor==='Siosa'):null;
 return (route.vendor==='Siosa'?`<small class="gemcost">Cost: ${esc(formatGemCost(siosa?.cost))}</small>`:'')+(name==='Momentum'&&earlyMomentum()?'<small class="mulinghint">Optional: mule a Ranger · free starting chest</small>':'');
}
