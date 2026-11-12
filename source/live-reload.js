// Only companion-hosted pages poll for app changes; standalone HTML stays offline.
let appVersion=null,updatePending=false,reloadBusy=false;
try{const saved=JSON.parse(sessionStorage.getItem('slayer-reload-view')||'null');if(saved){liveFollow=saved.follow!==false;liveResumeAtMilestone=saved.resume!==false;sessionStorage.removeItem('slayer-reload-view');}}catch{}
async function checkAppUpdate(){
 if(location.protocol==='file:'||reloadBusy)return;
 try{
  const r=await fetch('/api/version',{cache:'no-store',signal:AbortSignal.timeout(2500)});if(!r.ok)return;
  const data=await r.json();if(appVersion===null){appVersion=data.version;return;}
  if(data.version!==appVersion)updatePending=true;
  if(!updatePending)return;
  const busy=purchasePending.size>0||document.querySelector('dialog[open]')||document.activeElement?.matches('input,textarea,select');
  if(busy)return;
  try{sessionStorage.setItem('slayer-reload-view',JSON.stringify({follow:liveFollow,resume:liveResumeAtMilestone}));}catch{}
  reloadBusy=true;location.reload();
 }catch{/* Keep the page usable while the local server restarts. */}
}
checkAppUpdate();setInterval(checkAppUpdate,1000);
