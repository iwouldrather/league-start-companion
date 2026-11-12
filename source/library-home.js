function renderLibraryHome(){
 document.body.classList.add('libraryhome');document.body.dataset.design='board';
 document.title='Your builds · League Start Companion';
 document.querySelector('.brand strong').textContent='LEAGUE START COMPANION';
 $('stage').setAttribute('role','main');$('stage').removeAttribute('aria-labelledby');
 $('stage').innerHTML=`<header class="libraryhero"><p class="eyebrow">League Start Companion</p><h1>Your builds</h1><p>Import a PoB to get your gem shopping list, passive tree changes, ascendancy and equipment in one place.</p><button data-open-library>Import PoB / manage builds →</button></header><div id="homeBuilds" aria-live="polite"><p>Loading your saved builds…</p></div><p class="libraryprivacy">Builds and character progress stay on this computer.</p>`;
 if(location.protocol==='file:'){$('homeBuilds').innerHTML='<section class="libraryempty"><h2>Start your local companion</h2><p>Double-click Start Slayer Companion.bat to open your saved builds and import PoBs.</p></section>';return;}
 refreshLibraryHome();
}
async function refreshLibraryHome(){
 if(!$('homeBuilds'))return;
 try{
  const response=await fetch('/api/builds',{cache:'no-store'});if(!response.ok)throw Error('Could not load your saved builds.');const data=await response.json();
  if(!$('homeBuilds'))return;
  $('homeBuilds').innerHTML=data.builds.length?`<div class="librarycards">${data.builds.map(b=>`<a class="librarycard" href="/guide?build=${encodeURIComponent(b.id)}"><span class="eyebrow">Saved guide</span><h2>${esc(b.name)}</h2><span>Open guide →</span></a>`).join('')}</div>`:'<section class="libraryempty"><h2>Ready for your first build</h2><p>Paste a PoB code or pobb.in link to create a guide. Your gem progress stays saved when you switch builds.</p><button data-open-library>Import your first PoB →</button></section>';
 }catch(error){if($('homeBuilds'))$('homeBuilds').textContent=error.message;}
}
document.addEventListener('click',e=>{if(e.target.closest('[data-open-library]'))openImporter();});
