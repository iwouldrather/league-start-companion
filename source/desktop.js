window.addEventListener('pywebviewready',()=>{
 const button=document.createElement('button');button.innerHTML=uiIcon('settings');button.id='appSettings';button.className='iconbutton';button.setAttribute('aria-label','App settings');button.title='App settings';document.querySelector('.topactions').append(button);
 button.addEventListener('click',async()=>{const settings=await window.pywebview.api.settings();record('App settings',`<div class="appsettings"><h3>Updates · Version ${esc(settings.version)}</h3><p>Updates download automatically in the background. You choose when to restart and install.</p><div class="settingsactions"><button id="checkAppUpdates">Check for updates</button><button id="restartAppUpdate" hidden>Restart to update</button></div><p id="appUpdateStatus" role="status"></p><p class="importnotes">Checks run at startup and every 30 minutes. Downloads are verified before installation. Saved builds and progress are kept.</p><h3>Path of Exile game log</h3><p class="importnotes">${esc(settings.logPath)}</p><button id="chooseGameLog">Choose Client.txt…</button><h3>Local saves</h3><p class="importnotes">${esc(settings.dataDir)}</p><div class="settingsactions"><button id="importExistingSaves">Import saves from an existing companion folder…</button><button id="openAppData">Open save folder</button></div><p id="desktopStatus" role="status"></p><p>Imports copy saved builds and progress without replacing existing files. The original folder is left untouched.</p></div>`);});
});
document.addEventListener('click',async e=>{
 const button=e.target.closest('#chooseGameLog,#importExistingSaves,#openAppData,#checkAppUpdates,#restartAppUpdate,#updateReadyBanner,#updateIndicator');if(!button)return;
 button.disabled=true;
 try{
  if(button.id==='updateIndicator'){$('appSettings').click();return;}
  if(button.id==='restartAppUpdate'||button.id==='updateReadyBanner')await window.pywebview.api.restart_to_update();
  if(button.id==='chooseGameLog'){const settings=await window.pywebview.api.choose_game_log();$('desktopStatus').textContent='Reading '+settings.logPath;}
  if(button.id==='importExistingSaves'){const result=await window.pywebview.api.import_existing_saves();$('desktopStatus').textContent=`Copied ${result.copied} save files. Reopen the build library to choose a guide.`;if(!D.sets.length)refreshLibraryHome();}
  if(button.id==='openAppData')await window.pywebview.api.open_data_folder();
  if(button.id==='checkAppUpdates'){const result=await window.pywebview.api.check_updates();if(result.message&&$('desktopStatus'))$('desktopStatus').textContent=result.message;}
 }catch(error){const message=error.message||String(error);if($('desktopStatus'))$('desktopStatus').textContent=message;else record('Update could not start',`<p>${esc(message)}</p>`);}
 finally{button.disabled=false;}
});

window.addEventListener('pywebviewready',()=>{
 async function refreshUpdateStatus(){
  try{
   const state=await window.pywebview.api.update_status();
   const status=$('appUpdateStatus');if(status)status.textContent=state.message;
   const restart=$('restartAppUpdate');if(restart)restart.hidden=state.status!=='ready';
   let indicator=$('updateIndicator');
   if(!indicator){indicator=document.createElement('button');indicator.id='updateIndicator';document.body.append(indicator);}
   const labels={idle:'Auto updates on',checking:'Checking for updates',current:'Up to date',downloading:'Downloading update',ready:'Update ready',error:'Update check failed'};
   indicator.dataset.status=state.status;
   indicator.innerHTML='<span class="updatedot" aria-hidden="true"></span><span>'+esc(labels[state.status]||'Auto updates on')+'<small>'+esc(state.status==='ready'?'Version '+state.version+' · Open updates':state.status==='error'?'Click to retry in settings':'Checks every 30 minutes')+'</small></span>';
   indicator.title=state.message;
   indicator.setAttribute('aria-label',(labels[state.status]||'Auto updates on')+'. '+state.message+' Open update settings.');

  }catch(error){ /* Native bridge may be closing during restart. */ }
 }
 refreshUpdateStatus();setInterval(refreshUpdateStatus,2000);
});
