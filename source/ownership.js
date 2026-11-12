let purchaseCharacter='',purchaseOwned={},purchaseReady=false,purchaseError='',purchaseOverride='',purchaseCanUndo=false,purchaseUndoLabel='';
try{purchaseOverride=localStorage.getItem('slayer-purchase-character')||'';}catch{}
const purchasePending=new Set();
const gemsButton=document.createElement('button');gemsButton.id='myGems';gemsButton.textContent='My gems';document.querySelector('.topactions').prepend(gemsButton);
function isGemOwned(n){return purchaseReady&&purchaseOwned[n]===true;}
function decorateOwnership(){
 const desired=purchaseOverride||liveState?.character||'';
 if(desired!==purchaseCharacter){purchaseCharacter=desired;purchaseReady=false;purchaseOwned={};purchaseCanUndo=false;purchaseUndoLabel='';if(desired)loadPurchases(desired);}
 document.querySelectorAll('.buytablerow[data-record-gem]').forEach(row=>{
  if(row.parentElement.classList.contains('ownedrow'))return;
  const wrap=document.createElement('div');wrap.className='ownedrow';row.before(wrap);wrap.append(row);
  const box=document.createElement('input');box.type='checkbox';box.dataset.ownedGem=row.dataset.recordGem;box.title='I already bought or obtained this gem';box.setAttribute('aria-label','Owned: '+row.dataset.recordGem);wrap.prepend(box);
 });
 document.querySelectorAll('[data-owned-gem]').forEach(box=>{const name=box.dataset.ownedGem;box.checked=isGemOwned(name);box.disabled=!purchaseReady||purchasePending.size>0;box.closest('.ownedrow')?.classList.toggle('isowned',box.checked);});
 document.querySelectorAll('[data-progress-action=undo]').forEach(button=>{button.disabled=!purchaseReady||purchasePending.size>0||!purchaseCanUndo;button.title=purchaseCanUndo?'Undo: '+purchaseUndoLabel:'No changes to undo for this character';});
 document.querySelectorAll('[data-progress-reset]').forEach(button=>{button.disabled=!purchaseReady||purchasePending.size>0||!Object.keys(purchaseOwned).length;});
 if($('progressStatus'))$('progressStatus').textContent=purchaseError;
 gemsButton.textContent=`My gems · ${Object.keys(purchaseOwned).length} owned`;
 gemsButton.title=purchaseError||`Saved for ${purchaseCharacter||'choose a character'}`;
 if(document.getElementById('purchaseSaveStatus'))document.getElementById('purchaseSaveStatus').textContent=purchaseError||(purchaseReady?`Saved locally for ${purchaseCharacter}`:'Loading saved purchases…');
}
function offlinePurchases(character){return {owned:JSON.parse(localStorage.getItem('slayer-owned:'+character)||'{}'),history:JSON.parse(localStorage.getItem('slayer-owned-history:'+character)||'[]')};}
function acceptPurchases(data){purchaseOwned=data.owned;purchaseCanUndo=!!data.canUndo;purchaseUndoLabel=data.undoLabel||'';purchaseReady=true;purchaseError='';}
async function loadPurchases(character){try{
 let data;if(location.protocol==='file:'){const saved=offlinePurchases(character);data={owned:saved.owned,canUndo:!!saved.history.length,undoLabel:saved.history.at(-1)?.label};}else{const r=await fetch('/api/purchases?character='+encodeURIComponent(character),{cache:'no-store'});data=await r.json();if(!r.ok)throw Error(data.error||'Could not load saved gems.');}
 if(character!==purchaseCharacter)return;acceptPurchases(data);
 }catch(e){if(character===purchaseCharacter){purchaseReady=false;purchaseError=e.message;}}decorateOwnership();}
async function changeProgress(action,name,owned){
 if(!purchaseReady||purchasePending.size)return;
 const character=purchaseCharacter;purchasePending.add('progress');decorateOwnership();
 try{
  let data;
  if(location.protocol==='file:'){
   const saved=offlinePurchases(character);let gems={...saved.owned},history=saved.history;
   if(action==='undo'){if(history.length)gems=history.pop().owned;}
   else{
    const next=action==='reset'?{}:{...gems};if(action==='set'){if(owned)next[name]=true;else delete next[name];}
    if(JSON.stringify(next)!==JSON.stringify(gems)){history.push({owned:gems,label:action==='reset'?'Reset all gem progress':(owned?'Completed ':'Unchecked ')+name});history=history.slice(-30);gems=next;}
   }
   localStorage.setItem('slayer-owned:'+character,JSON.stringify(gems));localStorage.setItem('slayer-owned-history:'+character,JSON.stringify(history));data={owned:gems,canUndo:!!history.length,undoLabel:history.at(-1)?.label};
  }else{
   const r=await fetch('/api/purchases',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({character,action,gem:name,owned})});data=await r.json();if(!r.ok)throw Error(data.error||'Could not save progress.');
  }
  if(character===purchaseCharacter){acceptPurchases(data);if($('purchaseResetConfirm'))$('purchaseResetConfirm').hidden=true;}
 }catch(e){if(character===purchaseCharacter)purchaseError='Your change was not saved. '+e.message;}
 finally{purchasePending.clear();decorateOwnership();}
}
async function savePurchase(name,owned){return changeProgress('set',name,owned);}
function showMyGems(){record('My gems · '+(purchaseCharacter||'Choose a character'),`<div class="purchaseprofile"><label>Save purchases for character <input id="purchaseCharacterInput" maxlength="120" value="${esc(purchaseCharacter)}" placeholder="Character name"></label><button id="purchaseProfileSave">Use this character</button><button id="purchaseProfileAuto">Use logged character</button></div><p id="purchaseSaveStatus" role="status"></p><div class="progressactions"><button data-progress-action="undo">↶ Undo last change</button><button id="purchaseResetStart" data-progress-reset>Reset all gem progress…</button></div><div id="purchaseResetConfirm" class="progressconfirm" hidden><p>Reset all gem checks for <strong>${esc(purchaseCharacter)}</strong> across every guide? Your recorded level and other characters stay as they are. You can undo this reset.</p><button data-progress-action="reset" data-progress-reset>Reset gem progress</button><button id="purchaseResetCancel">Keep progress</button></div><p>Check a gem once you have bought or obtained it. This applies across every milestone for this character. Uncheck it to put it back on your shopping list. One check means you own the gem type; it does not track copies, gem level or quality.</p><p>${location.protocol==='file:'?'Offline mode saves in this browser only. Start the companion to use the shared local save file.':'Purchases are stored in slayer-purchases.json beside your companion. Keep that file when updating the guide.'}</p>${purchaseTable(D.sets[current],D.names.filter(n=>D.meta[n]&&!D.sets.flatMap(s=>s.groups.flatMap(g=>g.gems)).filter(g=>g.itemGranted).some(g=>g.nameSpec===n)).sort((a,b)=>a.localeCompare(b)))}`);decorateOwnership();}
gemsButton.addEventListener('click',showMyGems);
document.addEventListener('change',e=>{const box=e.target.closest('[data-owned-gem]');if(box)savePurchase(box.dataset.ownedGem,box.checked);});
document.addEventListener('click',e=>{if(e.target.closest('#purchaseProfileSave')){const value=document.getElementById('purchaseCharacterInput').value.trim();if(!value){alert('Enter a character name first.');return;}purchaseOverride=value;try{localStorage.setItem('slayer-purchase-character',value);}catch{}decorateOwnership();showMyGems();}if(e.target.closest('#purchaseProfileAuto')){purchaseOverride='';try{localStorage.removeItem('slayer-purchase-character');}catch{}decorateOwnership();showMyGems();}});
const preOwnedRecord=record;record=function(title,html){preOwnedRecord(title,html);decorateOwnership();};
decorateOwnership();


document.addEventListener('click',e=>{
 const action=e.target.closest('[data-progress-action]');if(action)changeProgress(action.dataset.progressAction);
 if(e.target.closest('#purchaseResetStart'))$('purchaseResetConfirm').hidden=false;
 if(e.target.closest('#purchaseResetCancel'))$('purchaseResetConfirm').hidden=true;
});
