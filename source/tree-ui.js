function nativeGraphic(uri,label,extra=''){
 if(!uri)return `<div class="nativeempty">${esc(label)}</div>`;
 if(!uri.startsWith('data:image/svg+xml;base64,'))return `<img id="treeThumb" class="treeimage" src="${uri}" alt="${esc(label)}">`;
 const bytes=Uint8Array.from(atob(uri.split(',')[1]),c=>c.charCodeAt(0));
 return new TextDecoder().decode(bytes).replace('<svg ',`<svg class="nativegraphic ${extra}" aria-label="${esc(label)}" `);
}
function zoomTreeBox(box,origin,anchor,delta){
 const level=Math.max(1,Math.min(8,origin.width/box.width*Math.exp(-Math.max(-600,Math.min(600,delta))*.0015)));
 const width=origin.width/level,height=origin.height/level,ratio=width/box.width;
 const ax=Math.max(box.x,Math.min(box.x+box.width,anchor.x)),ay=Math.max(box.y,Math.min(box.y+box.height,anchor.y));
 return {x:Math.max(origin.x,Math.min(origin.x+origin.width-width,ax-(ax-box.x)*ratio)),y:Math.max(origin.y,Math.min(origin.y+origin.height-height,ay-(ay-box.y)*ratio)),width,height};
}
const treeViewports=new WeakMap();
let treeDrag=null,treeDragUntil=0;
function treeBox(svg){const b=svg.viewBox.baseVal;return {x:b.x,y:b.y,width:b.width,height:b.height};}
function treeOrigin(svg){if(!treeViewports.has(svg))treeViewports.set(svg,treeBox(svg));return treeViewports.get(svg);}
function setTreeBox(svg,box){svg.setAttribute('viewBox',`${box.x} ${box.y} ${box.width} ${box.height}`);const reset=svg.closest('.nativepanel').querySelector('[data-tree-reset]');if(reset)reset.hidden=box.width>=treeOrigin(svg).width-.01;}
document.addEventListener('wheel',e=>{
 const canvas=e.target.closest('.nativecanvas'),svg=canvas?.querySelector('svg');
 if(svg){e.preventDefault();const matrix=svg.getScreenCTM();if(!matrix)return;const anchor=new DOMPoint(e.clientX,e.clientY).matrixTransform(matrix.inverse());setTreeBox(svg,zoomTreeBox(treeBox(svg),treeOrigin(svg),anchor,e.deltaY*(e.deltaMode===1?16:e.deltaMode===2?canvas.clientHeight:1)));return;}
 const stage=e.target.closest('#zoomStage');if(!stage)return;
 e.preventDefault();const image=$('zoomImage'),rect=image.getBoundingClientRect(),x=(e.clientX-rect.left)/zoom,y=(e.clientY-rect.top)/zoom;
 zoom=Math.max(.2,Math.min(6,zoom*Math.exp(-e.deltaY*.0015)));applyZoom();const next=image.getBoundingClientRect();stage.scrollLeft+=next.left+x*zoom-e.clientX;stage.scrollTop+=next.top+y*zoom-e.clientY;
},{passive:false});
document.addEventListener('pointerdown',e=>{const canvas=e.target.closest('.nativecanvas'),svg=canvas?.querySelector('svg');if(e.button!==0||!svg)return;treeDrag={canvas,svg,id:e.pointerId,x:e.clientX,y:e.clientY,box:treeBox(svg),moved:false};treeOrigin(svg);});
document.addEventListener('pointermove',e=>{
 const drag=treeDrag;if(!drag||drag.id!==e.pointerId)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;
 if(!drag.moved&&Math.hypot(dx,dy)<4)return;
 if(!drag.moved){drag.moved=true;drag.canvas.setPointerCapture(e.pointerId);drag.canvas.classList.add('isdragging');}
 e.preventDefault();const matrix=drag.svg.getScreenCTM(),origin=treeOrigin(drag.svg),box=drag.box;if(!matrix)return;
 setTreeBox(drag.svg,{...box,x:Math.max(origin.x,Math.min(origin.x+origin.width-box.width,box.x-dx/matrix.a)),y:Math.max(origin.y,Math.min(origin.y+origin.height-box.height,box.y-dy/matrix.d))});
});
function finishTreeDrag(e){if(!treeDrag||treeDrag.id!==e.pointerId)return;if(treeDrag.moved)treeDragUntil=performance.now()+300;treeDrag.canvas.classList.remove('isdragging');if(treeDrag.canvas.hasPointerCapture(e.pointerId))treeDrag.canvas.releasePointerCapture(e.pointerId);treeDrag=null;}
document.addEventListener('pointerup',finishTreeDrag);document.addEventListener('pointercancel',finishTreeDrag);
document.addEventListener('click',e=>{if(performance.now()<treeDragUntil&&e.target.closest('.nativecanvas')){e.preventDefault();e.stopImmediatePropagation();}},{capture:true});
document.addEventListener('click',e=>{const reset=e.target.closest('[data-tree-reset]');if(reset){const svg=reset.closest('.nativepanel').querySelector('svg');setTreeBox(svg,treeOrigin(svg));}});
function passiveCheckpointIndex(sets,guideIndex,choice){
 const selected=sets.findIndex(s=>s.key===choice);
 return selected>=0?selected:Math.max(0,Math.min(sets.length-1,guideIndex));
}
function passiveCheckpointSetup(){return D.sets[passiveCheckpointIndex(D.sets,current,treeCheckpointChoice)];}
function treePanel(guide){
 const index=passiveCheckpointIndex(D.sets,current,treeCheckpointChoice),s=D.sets[index],following=!D.sets.some(s=>s.key===treeCheckpointChoice);
 const changes=passiveView==='changes',delta=s.treeDelta||{},image=changes?(s.treeDiffImage||s.treeImage):s.treeImage;
 const summary=delta.added||delta.removed?`+${delta.added||0} new · −${delta.removed||0} removed`:'No passive changes';
 const asc=D.build?.ascendClassName||D.build?.className||'Ascendancy';
 const comparison=changes?(index?'Changes from '+D.sets[index-1].short:'First allocation'):'Full allocation';
 return `<div class="treecolumn"><section class="concepttree nativepanel" aria-label="Passive tree checkpoint"><header class="conceptsectionhead"><div><p class="eyebrow">${esc(comparison)} · ${following?'Following guide':'Tree preview'}</p><h2>Passive tree</h2></div><div class="treetoggles"><button data-tree-mode="changes" aria-pressed="${changes}">Changes</button><button data-tree-mode="full" aria-pressed="${!changes}">Full</button><button data-tree-reset hidden aria-label="Reset passive tree zoom">Reset</button><button id="treeOpen" aria-label="Enlarge passive tree">↗</button></div></header><nav class="treecheckpointnav" aria-label="Passive tree checkpoints"><button data-tree-step="-1" aria-label="Previous passive tree checkpoint" ${index===0?'disabled':''}>←</button><select id="treeCheckpoint" aria-label="Passive tree checkpoint">${D.sets.map((step,i)=>`<option value="${esc(step.key)}" ${i===index?'selected':''}>${esc(step.short+' · '+step.nav)}</option>`).join('')}</select><button data-tree-step="1" aria-label="Next passive tree checkpoint" ${index===D.sets.length-1?'disabled':''}>→</button><button data-tree-follow ${following?'disabled':''} title="Return the passive tree to the selected guide step">${following?'Following guide':'Match guide'}</button></nav><div class="concepttreeimage nativecanvas" title="Mouse wheel to zoom · drag to pan">${nativeGraphic(image,s.title+' · passive tree')}</div><footer class="nativelegend"><span class="newkey">New</span><span class="keptkey">Already allocated</span><span class="removedkey">Removed</span><b>${changes?summary:(s.passivePoints??'')+' passive points'}</b><button data-tree-record="passives">Notables</button><button data-tree-record="masteries">Masteries</button></footer></section><section class="ascendancypanel nativepanel" aria-label="Ascendancy separate from passive tree"><header><div><p class="eyebrow">Ascendancy · guide step ${esc(guide.short)}</p><h3>${esc(asc)}</h3></div><span class="ascpoints">${guide.ascendancyPoints??guide.ascendancy.length*2} / 8 points</span><button data-asc-details>Details ↗</button></header><div class="ascendancycanvas">${nativeGraphic(guide.ascendancyImage,'Ascendancy nodes · '+asc,'ascgraphic')}</div></section></div>`;
}
function refreshPassiveCheckpoint(){
 const column=document.querySelector('#stage .treecolumn');
 if(column?.querySelector('.treecheckpointnav'))column.outerHTML=treePanel(D.sets[current]);
 else{const old=document.querySelector('#stage #treeThumb');if(old)old.closest('section').outerHTML=treePanel(D.sets[current]);}
}
function choosePassiveCheckpoint(choice){
 treeCheckpointChoice=choice;
 try{localStorage.setItem('league-tree-checkpoint:'+(D.id||'library'),choice);}catch{}
 refreshPassiveCheckpoint();
}
document.addEventListener('change',e=>{if(e.target.id==='treeCheckpoint'){choosePassiveCheckpoint(e.target.value);$('treeCheckpoint')?.focus({preventScroll:true});}});
document.addEventListener('click',e=>{
 const step=e.target.closest('[data-tree-step]');if(step){const index=passiveCheckpointIndex(D.sets,current,treeCheckpointChoice),next=index+Number(step.dataset.treeStep);if(next>=0&&next<D.sets.length){choosePassiveCheckpoint(D.sets[next].key);document.querySelector(`[data-tree-step="${step.dataset.treeStep}"]`)?.focus({preventScroll:true});}}
 if(e.target.closest('[data-tree-follow]'))choosePassiveCheckpoint('follow');
 const mode=e.target.closest('[data-tree-mode]');if(mode){passiveView=mode.dataset.treeMode;refreshPassiveCheckpoint();}
 const treeRecord=e.target.closest('[data-tree-record]');if(treeRecord){const s=passiveCheckpointSetup();record(s.short+' · '+s.nav+' · '+(treeRecord.dataset.treeRecord==='passives'?'Notables':'Masteries'),passiveList(treeRecord.dataset.treeRecord==='passives'?s.notables:s.masteryDetails)||'<p>No selected effects in this checkpoint.</p>');}
 const node=e.target.closest('[data-node]');if(node){const setup=node.closest('.ascendancycanvas,.asclarge')?D.sets[current]:passiveCheckpointSetup(),detail=setup.nodeDetails?.[node.dataset.node];if(detail)record(detail.name,`<p class="nodestate">${detail.ascendancy?'Ascendancy · ':''}${{new:'New at this step',removed:'Removed since the previous step',kept:'Already allocated',unallocated:'Not allocated in this setup'}[detail.state]}</p>${detail.stats.map(stat=>`<p class="nodestat">${esc(stat)}</p>`).join('')||'<p>Starting node · no passive point required.</p>'}`);}
 if(e.target.closest('[data-asc-details]')){const s=D.sets[current];record('Ascendancy · '+(D.build?.ascendClassName||D.build?.className),`<div class="asclarge">${nativeGraphic(s.ascendancyImage,'Ascendancy nodes')}</div>${passiveList(s.ascendancy)}`);}
});
// Keep the same tree controls available in the scrolling layout on smaller windows.
const preCheckpointRender=render;
render=function(i,focus=false){preCheckpointRender(i,focus);if(D.sets.length&&!document.querySelector('#stage .treecheckpointnav'))refreshPassiveCheckpoint();};
if(D.sets.length&&!document.querySelector('#stage .treecheckpointnav'))refreshPassiveCheckpoint();

document.addEventListener('keydown',e=>{if(['Enter',' '].includes(e.key)&&e.target.matches('[data-node]')){e.preventDefault();e.target.dispatchEvent(new MouseEvent('click',{bubbles:true}));}});
if(D.uiAssets){
 document.body.classList.add('poetheme');
 if(D.uiAssets.texture)document.documentElement.style.setProperty('--poe-texture',`url("${D.uiAssets.texture}")`);
}