// Shopping belongs to the character, independently of the milestone being viewed.
let plannerChoice='auto',plannerSignature='';
try{plannerChoice=localStorage.getItem('slayer-planning-stage')||'auto';}catch{}
const planner=document.createElement('aside');planner.id='buyNextPanel';planner.className='prep';planner.setAttribute('aria-label','Character shopping and next milestone preparation');
document.querySelector('#navigation').after(planner);document.body.classList.add('hasplanner');
function planningStage(){const selected=D.sets.findIndex(s=>s.key===plannerChoice);return selected>=0?selected:(suggestedStage(liveState?.level)??0);}
function planningLists(){const i=planningStage(),needed=buyNames(D.sets[i]).filter(n=>!isGemOwned(n)),currentNames=new Set(buyNames(D.sets[i]));for(let j=i+1;j<D.sets.length;j++){const next=buyNames(D.sets[j]).filter(n=>!currentNames.has(n)&&!isGemOwned(n));if(next.length)return {i,needed,next,nextIndex:j};}return {i,needed,next:[],nextIndex:null};}
function plannerGroup(title,names,index,limit){return `<section class="prepgroup"><header><h3>${esc(title)}</h3><span>${names.length} needed</span></header>${names.length?purchaseTable(D.sets[index],names.slice(0,limit)):'<p class="prepdone">✓ All gems accounted for</p>'}</section>`;}
function renderPlanner(){
 if(!D.sets.length){planner.hidden=true;return;}
 document.querySelector('#stage .newpurchase')?.remove();
 const lists=planningLists(),{i,needed,next,nextIndex}=lists;
 const signature=JSON.stringify([innerHeight<1150,i,needed,next,nextIndex,purchaseCharacter,purchaseReady,purchaseError,purchaseCanUndo,purchaseUndoLabel,liveState?.level,liveState?.characterClass,plannerChoice]);
 if(signature===plannerSignature)return;plannerSignature=signature;
 const baseLimit=guideClassMismatch()?(innerHeight<1150?8:10):(innerHeight<1150?10:12);
 const planned=[...needed,...next],extraRows=planned.filter(n=>route(n).vendor==='Siosa'||(n==='Momentum'&&earlyMomentum())).length;
 const rowLimit=Math.max(4,Math.floor(baseLimit/(1+.4*extraRows/Math.max(1,planned.length)))),firstLimit=needed.length?Math.min(needed.length,next.length?Math.max(4,rowLimit-Math.min(next.length,8)):rowLimit):0,nextLimit=rowLimit-firstLimit;
 const complete=needed.length===0;
 planner.innerHTML=`<header class="prephead"><p class="eyebrow">Your character · across all tabs</p><h2>Buy next</h2><p>${esc(purchaseCharacter||'Choose your character in My gems')}${liveState?.level?' · recorded level '+liveState.level:''}</p><label class="prepselect">Planning from<select id="planningStage"><option value="auto" ${plannerChoice==='auto'?'selected':''}>Follow recorded level</option>${D.sets.map(s=>`<option value="${s.key}" ${plannerChoice===s.key?'selected':''}>${esc(s.short+' · '+s.nav)}</option>`).join('')}</select></label><p class="prephint">${plannerChoice==='auto'&&!liveState?.level?'No recorded level yet: planning from level 1. ':''}Use level ≠ purchase unlock. Finish the quest shown. Checked gems leave this list.</p></header><div class="preplists">${needed.length?plannerGroup('For '+D.sets[i].nav,needed,i,firstLimit):'<div class="prepcomplete"><b>✓ Current gems ready</b><p>Your shopping list is clear for '+esc(D.sets[i].short+' · '+D.sets[i].nav)+'.</p></div>'}${nextIndex!==null?plannerGroup('Prepare for '+D.sets[nextIndex].short+' · '+D.sets[nextIndex].nav,next,nextIndex,nextLimit):'<div class="prepcomplete"><b>All future gems accounted for</b><p>You have checked every gem needed by the remaining guide milestones.</p></div>'}</div><footer class="prepfooter">${needed.length+next.length>rowLimit?`<button id="plannerAll">All ${needed.length+next.length} remaining gems ↗</button>`:''}<button data-progress-action="undo">↶ Undo</button><button id="plannerOwned">${Object.keys(purchaseOwned).length} owned · Manage / reset ↗</button><span id="progressStatus" role="status"></span><p>The links and tree on the right follow the tab you select. This list follows your planning level.</p></footer>`;
 decorateBeforePlanner();
 if(guideClassMismatch()){const hint=document.createElement('p');hint.className='prepclasswarning';hint.textContent=`This guide is for ${D.build.className}; the log character is ${liveState.characterClass}. Choose the intended character in My gems and its planning level before recording purchases.`;planner.querySelector('.prephead').append(hint);}
}
const decorateBeforePlanner=decorateOwnership;
decorateOwnership=function(){decorateBeforePlanner();renderPlanner();};
document.addEventListener('change',e=>{if(e.target.id==='planningStage'){plannerChoice=e.target.value;try{localStorage.setItem('slayer-planning-stage',plannerChoice);}catch{}renderPlanner();}});
document.addEventListener('click',e=>{if(e.target.closest('#plannerOwned'))showMyGems();if(e.target.closest('#plannerAll')){const {i,needed,next,nextIndex}=planningLists();record('Your remaining gem purchases',plannerGroup('For '+D.sets[i].nav,needed,i,needed.length)+(nextIndex!==null?plannerGroup('Prepare for '+D.sets[nextIndex].short+' · '+D.sets[nextIndex].nav,next,nextIndex,next.length):''));}});
renderPlanner();
