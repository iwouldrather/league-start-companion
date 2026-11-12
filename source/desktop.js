window.addEventListener('pywebviewready',()=>{
 const button=document.createElement('button');button.textContent='App settings';button.id='appSettings';document.querySelector('.topactions').prepend(button);
 button.addEventListener('click',async()=>{const settings=await window.pywebview.api.settings();record('App settings',`<div class="appsettings"><h3>Updates · Version ${esc(settings.version)}</h3><p>Check the latest release in your browser. This private repository requires your GitHub sign-in.</p><button id="checkAppUpdates">Check for updates ↗</button><button id="installAppUpdate" ${settings.installed?'':'disabled'}>Install downloaded update…</button><p class="importnotes">Download LeagueStartCompanion-Setup.exe from the latest release, then select it here. The app closes before setup runs. Your saved builds and progress are kept.</p><h3>Path of Exile game log</h3><p class="importnotes">${esc(settings.logPath)}</p><button id="chooseGameLog">Choose Client.txt…</button><h3>Local saves</h3><p class="importnotes">${esc(settings.dataDir)}</p><button id="importExistingSaves">Import saves from an existing companion folder…</button><button id="openAppData">Open save folder</button><p id="desktopStatus" role="status"></p><p>Imports copy saved builds and progress without replacing existing files. The original folder is left untouched.</p></div>`);});
});
document.addEventListener('click',async e=>{
 const button=e.target.closest('#chooseGameLog,#importExistingSaves,#openAppData,#checkAppUpdates,#installAppUpdate');if(!button)return;
 button.disabled=true;
 try{
  if(button.id==='chooseGameLog'){const settings=await window.pywebview.api.choose_game_log();$('desktopStatus').textContent='Reading '+settings.logPath;}
  if(button.id==='importExistingSaves'){const result=await window.pywebview.api.import_existing_saves();$('desktopStatus').textContent=`Copied ${result.copied} save files. Reopen the build library to choose a guide.`;if(!D.sets.length)refreshLibraryHome();}
  if(button.id==='openAppData')await window.pywebview.api.open_data_folder();
  if(button.id==='checkAppUpdates'||button.id==='installAppUpdate'){const result=await window.pywebview.api[button.id==='checkAppUpdates'?'check_updates':'install_update']();if(result.message&&$('desktopStatus'))$('desktopStatus').textContent=result.message;}
 }catch(error){$('desktopStatus').textContent=error.message||String(error);}
 finally{button.disabled=false;}
});
