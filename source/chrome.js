function uiIcon(name){
 if(name==='builds')return '<svg class="uiicon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="7" y="7" width="14" height="14" rx="2"/><path d="M17 3H5a2 2 0 0 0-2 2v12M11 12h6M11 16h4"/></svg>';
 const paths={settings:'<path d="m9 3 1-2h4l1 2 2 1 2-.2 2 3-1 2v3l1 2-2 3-2-.2-2 1-1 2h-4l-1-2-2-1-2 .2-2-3 1-2V9L3 7l2-3 2 .2Z"/><circle cx="12" cy="10.5" r="3"/>',text:'<path d="M5 3h14v18H5zM8 7h8M8 11h8M8 15h5"/>',info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v1"/>'};
 return `<svg class="uiicon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]||paths.info}</svg>`;
}
function infoTip(text,label='More information'){
 return `<button type="button" class="infobutton" data-info="${esc(text)}" aria-label="${esc(label)}">${uiIcon('info')}</button>`;
}
const chromeTooltip=document.createElement('div');chromeTooltip.id='chromeTooltip';chromeTooltip.className='chrome-tooltip';chromeTooltip.setAttribute('role','tooltip');chromeTooltip.hidden=true;document.body.append(chromeTooltip);
let tooltipOwner=null;
function hideChromeTooltip(){tooltipOwner?.removeAttribute('aria-describedby');tooltipOwner=null;chromeTooltip.hidden=true;}
function showChromeTooltip(button){
 hideChromeTooltip();tooltipOwner=button;button.setAttribute('aria-describedby','chromeTooltip');chromeTooltip.textContent=button.dataset.info;chromeTooltip.hidden=false;
 const rect=button.getBoundingClientRect(),box=chromeTooltip.getBoundingClientRect();
 chromeTooltip.style.left=Math.max(8,Math.min(innerWidth-box.width-8,rect.left))+'px';
 chromeTooltip.style.top=(rect.bottom+box.height+16<innerHeight?rect.bottom+8:Math.max(8,rect.top-box.height-8))+'px';
}
document.addEventListener('mouseover',e=>{const button=e.target.closest('[data-info]');if(button&&button!==tooltipOwner)showChromeTooltip(button);});
document.addEventListener('mouseout',e=>{if(tooltipOwner&&e.target.closest('[data-info]')===tooltipOwner&&!tooltipOwner.contains(e.relatedTarget))hideChromeTooltip();});
document.addEventListener('focusin',e=>{if(e.target.matches('[data-info]'))showChromeTooltip(e.target);});
document.addEventListener('focusout',e=>{if(e.target===tooltipOwner)hideChromeTooltip();});
document.addEventListener('click',e=>{
 const info=e.target.closest('[data-info]');if(info){if(tooltipOwner!==info)showChromeTooltip(info);return;}
 hideChromeTooltip();const tools=$('toolsMenu');if(tools?.open&&(!tools.contains(e.target)||e.target.closest('button')))tools.open=false;
});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){hideChromeTooltip();const tools=$('toolsMenu');if(tools?.open){tools.open=false;tools.querySelector('summary').focus();}}});
window.addEventListener('resize',hideChromeTooltip);
document.addEventListener('scroll',hideChromeTooltip,true);
