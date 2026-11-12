// Reads only the companion's deliberately limited, local state endpoint.
let liveState=null,liveFollow=true,liveConnected=false,liveTarget=null;
let liveResumeAtMilestone=true,livePreviousTarget=null;
try{const prior=sessionStorage.getItem('slayer-last-target');if(prior!==null)livePreviousTarget=Number(prior);}catch{}
const liveButton=document.createElement('button');liveButton.id='liveStatus';
liveButton.textContent=location.protocol==='file:'?'Live companion · How to start':'Connecting to local log…';
const characterBar=document.createElement('section');characterBar.className='characterbar';characterBar.setAttribute('aria-label','Current character');
characterBar.innerHTML='<div class="characterlevel"><small>LEVEL</small><strong id="characterLevel">—</strong></div><div class="characteridentity"><span class="characterlabel">Current character</span><div class="characteridentityrow"><span id="characterNameSlot"></span><span id="characterClass"></span></div><span id="characterWarning" role="status" hidden></span></div><div class="characterarea"><small>Current area</small><span id="characterArea">Waiting for area</span></div><div class="charactercontrols"><span id="characterConnection" role="status">Connecting to log…</span><span id="characterFollowSlot"></span></div>';
document.querySelector('.topbar').after(characterBar);$('characterNameSlot').append(liveButton);
const resumeButton=document.createElement('button');resumeButton.id='resumeLive';$('characterFollowSlot').append(resumeButton);
resumeButton.addEventListener('click',()=>{liveFollow=!liveFollow;liveResumeAtMilestone=liveFollow;if(liveFollow&&liveTarget!==null)render(liveTarget);liveDecorate();});
function suggestedStage(level){if(!level||!D.sets.length)return null;let i=0;D.sets.forEach((s,j)=>{if(level>=(s.startLevel??100))i=j;});return i;}
function guideClassMismatch(){return !!(D.imported&&liveState?.characterClass&&![D.build.className,D.build.ascendClassName].includes(liveState.characterClass));}
function liveDecorate(){
 resumeButton.hidden=false;resumeButton.disabled=!liveConnected||!liveState?.level||!D.sets.length;
 resumeButton.textContent=liveFollow?'Following game':'Resume following';resumeButton.setAttribute('aria-pressed',String(liveFollow));
 resumeButton.title=liveFollow?'Pause automatic milestone selection':'Follow your recorded level';
 if(typeof decorateOwnership==='function')decorateOwnership();
 document.querySelectorAll('[data-record-gem]').forEach(b=>{const name=b.dataset.recordGem,m=D.meta[name];if(!m)return;
 const upcoming=!isGemOwned(name)&&liveConnected&&liveState?.level&&m.minLevel>liveState.level&&m.minLevel<=liveState.level+4;
 b.classList.toggle('liveupcoming',!!upcoming);
 if(upcoming)b.title=`Usable in ${m.minLevel-liveState.level} level(s). Purchase still requires the listed quest.`;
 });
 const s=liveState||{};
 liveButton.textContent=s.character||(!liveConnected?'Game log unavailable':'Waiting for character');
 liveButton.setAttribute('aria-label','Current character: '+(s.character||'not recorded')+'. Open recorded character details.');
 liveButton.title='Last recorded character. Open details and vendor reminders.';
 $('characterLevel').textContent=s.level||'—';$('characterClass').textContent=s.characterClass||'Class not recorded';
 $('characterArea').textContent=s.area||'Area not recorded';
 $('characterConnection').textContent=liveConnected?(s.character?'Reading local log':'Waiting for a level-up'):location.protocol==='file:'?'Offline guide':s.status==='missing'?'Game log not found':'Log disconnected';
 characterBar.classList.toggle('isdisconnected',!liveConnected);
 const mismatch=guideClassMismatch();$('characterWarning').hidden=!mismatch;
 $('characterWarning').textContent=mismatch?`${s.characterClass} character · ${D.build.ascendClassName||D.build.className} guide`:'';
}
const preLiveRender=render;render=function(i,focus=false){preLiveRender(i,focus);liveDecorate();};
function liveDetails(){
 const s=liveState;if(!s||!liveConnected){record('Local game companion',`<p>${location.protocol==='file:'?'Open League Start Companion to follow your game.':'The game log is not connected.'}</p><p>Open the settings gear and choose your Path of Exile <b>Client.txt</b>. Character details come from recorded level-ups and area entries.</p><p>The log is read locally. No game inputs or log uploads.</p>`);return;}
 const target=suggestedStage(s.level),names=target===null?[]:[...new Set([...buyNames(D.sets[target]),...(target+1<D.sets.length?buyNames(D.sets[target+1]):[])])];
 const next=names.filter(n=>!isGemOwned(n)&&D.meta[n].minLevel>s.level&&D.meta[n].minLevel<=s.level+4);
 const now=names.filter(n=>!isGemOwned(n)&&D.meta[n].minLevel<=s.level&&route(n).act===s.act);
 record('Your last recorded game state',`<div class="livefacts"><p><b>${esc(s.character||'Unknown character')}</b> · ${esc(s.characterClass||'Class unknown')} · ${s.level?'Level '+s.level:'Level unknown'}</p><p>${esc(s.area||'Area unknown')}${s.act?' · Act '+s.act:''}${s.areaLevel?' · Area level '+s.areaLevel:''}</p><p class="muted">Level event: ${esc(s.levelAt||'not found')}<br>Area event: ${esc(s.areaAt||'not found')}<br>Times are from your game log. These can be old; a character switch may remain undetected until the next level-up.</p></div><button id="liveFollowToggle">${liveFollow?'Pause automatic milestone selection':'Follow my level'}</button><p>Milestone selection uses level only. It does not confirm Lab completion, gems owned, equipment or passives. Confirm the build swap yourself.</p><h3>Coming up · next four levels</h3><p>Checks this loadout and the next milestone so you can prepare for the swap.</p>${next.length?purchaseTable(D.sets[target],next):'<p>No new gem use-levels in the next four levels for this loadout or its next milestone.</p>'}<h3>Check vendors in your current act</h3><p>These gems meet the use-level requirement. Buy only after the listed quest; the log does not confirm quest completion or ownership.</p>${now.length?purchaseTable(D.sets[target],now):'<p>No matching campaign vendor reminders for this act.</p>'}<p class="muted">Only level and area events are processed locally. No chat is sent to this page or uploaded. This product is not affiliated with or endorsed by Grinding Gear Games.</p>`);
}
liveButton.addEventListener('click',liveDetails);

function shouldResumeFollowing(target,previous,viewed,following,resume){return !following&&resume&&target!==null&&((previous!==null&&target>previous)||(previous===null&&target>viewed));}
function applyLiveState(state){
 liveState=state;liveConnected=state.status==='reading';
 if(!liveConnected){liveDecorate();return;}
 liveTarget=suggestedStage(state.level);
 if(shouldResumeFollowing(liveTarget,livePreviousTarget,current,liveFollow,liveResumeAtMilestone))liveFollow=true;
 livePreviousTarget=liveTarget;
 try{if(liveTarget!==null)sessionStorage.setItem('slayer-last-target',String(liveTarget));}catch{}
 if(liveFollow&&liveTarget!==null&&current!==liveTarget)render(liveTarget);
 liveDecorate();
}
async function pollLive(){if(location.protocol==='file:'){queueMicrotask(liveDecorate);return;}try{const response=await fetch('/api/state',{cache:'no-store',signal:AbortSignal.timeout(4000)});if(!response.ok)throw Error('Unavailable');applyLiveState(await response.json());}catch{liveConnected=false;liveDecorate();document.querySelectorAll('.liveupcoming').forEach(b=>b.classList.remove('liveupcoming'));}}
if(location.protocol!=='file:'){
 const gameEvents=new EventSource('/api/events');
 gameEvents.addEventListener('game',e=>{try{applyLiveState(JSON.parse(e.data));}catch{}});
 document.addEventListener('visibilitychange',()=>{if(!document.hidden)pollLive();});
 window.addEventListener('focus',pollLive);
}
pollLive();setInterval(pollLive,10000);
document.addEventListener('click',e=>{if(e.target.closest('[data-tab]')){liveFollow=false;liveResumeAtMilestone=true;livePreviousTarget=liveTarget;liveDecorate();}if(e.target.closest('#liveFollowToggle')){liveFollow=!liveFollow;liveResumeAtMilestone=liveFollow;if(liveFollow&&liveTarget!==null)render(liveTarget);liveDecorate();liveDetails();}});
