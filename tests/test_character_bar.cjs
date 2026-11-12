const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
class Element{
 constructor(id=''){this.id=id;this.textContent='';this.attributes={};this.listeners={};this.classes=new Set();this.classList={toggle:(name,on)=>on?this.classes.add(name):this.classes.delete(name),remove:name=>this.classes.delete(name)};}
 setAttribute(key,value){this.attributes[key]=value;}
 append(child){child.parent=this;}
 after(child){this.afterNode=child;}
 addEventListener(name,handler){this.listeners[name]=handler;}
}
const elements=new Map();const get=id=>{if(!elements.has(id))elements.set(id,new Element(id));return elements.get(id);};
const topbar=new Element('topbar');
const context=vm.createContext({
 document:{createElement:()=>new Element(),querySelector:selector=>{assert.equal(selector,'.topbar');return topbar;},querySelectorAll:()=>[],addEventListener:()=>{}},
 $:get,location:{protocol:'file:'},sessionStorage:{getItem:()=>null,setItem:()=>{}},queueMicrotask:()=>{},setInterval:()=>{},
 D:{imported:true,build:{className:'Marauder',ascendClassName:'Berserker'},sets:[{startLevel:1},{startLevel:33},{startLevel:50}],meta:{}},
 current:0,render:i=>{context.current=i;},isGemOwned:()=>false,esc:value=>String(value),buyNames:()=>[],record:()=>{}
});
vm.runInContext(fs.readFileSync(path.join(__dirname,'../source/live-guide.js'),'utf8'),context);
assert.equal(topbar.afterNode.className,'characterbar');
const state=level=>`applyLiveState({status:'reading',character:'ExampleExile',characterClass:'Slayer',level:${level},area:'The Forest Encampment'})`;
vm.runInContext(state(33),context);
assert.equal(vm.runInContext('liveButton.textContent',context),'ExampleExile');
assert.equal(vm.runInContext('liveButton.parent.id',context),'characterNameSlot');
assert.equal(get('characterLevel').textContent,33);
assert.equal(get('characterArea').textContent,'The Forest Encampment');
assert.equal(get('characterConnection').hidden,true,'Healthy log status should not duplicate Following game');
assert.match(vm.runInContext('resumeButton.title',context),/Reading local log/);
assert.equal(get('characterWarning').hidden,false);
assert.equal(get('characterWarning').textContent,'Slayer character · Berserker guide');
assert.equal(context.current,1);
vm.runInContext('resumeButton.listeners.click()',context);
assert.equal(vm.runInContext('liveFollow',context),false);
assert.equal(vm.runInContext('resumeButton.textContent',context),'Resume following');
vm.runInContext(state(50),context);
assert.equal(context.current,1,'Explicit pause must survive a new milestone');
vm.runInContext('resumeButton.listeners.click()',context);
assert.equal(context.current,2,'Resume should jump to the current recorded milestone');
context.location.protocol='http:';
vm.runInContext("applyLiveState({status:'missing'})",context);
assert.equal(get('characterConnection').textContent,'Game log not found');
assert.equal(get('characterConnection').hidden,false,'Missing logs must stay visible');
assert.equal(vm.runInContext('resumeButton.textContent',context),'Follow game');
assert.equal(vm.runInContext('resumeButton.disabled',context),true);
context.D.sets=[];
vm.runInContext(state(46),context);
assert.equal(vm.runInContext('resumeButton.disabled',context),true,'No guide means no milestone-follow action');
console.log('Character bar: separate context, mismatch, pause/resume, missing log and library states passed.');
