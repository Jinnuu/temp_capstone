import 'bootstrap/dist/css/bootstrap.min.css';
import Alert from 'bootstrap/js/dist/alert';
import './ui.css';
import {greenBrand} from './brand';

const modes=['reference','green','civic'] as const;
type Mode=typeof modes[number];
const valid=(value:unknown):value is Mode=>typeof value==='string'&&modes.includes(value as Mode);
const labels:Record<Mode,string>={reference:'레퍼런스형',green:'그린형',civic:'공공기관형'};
const root=document.documentElement;
const preview=root.dataset.snpPreview==='true';
let current:Mode=valid(root.dataset.snpMode)?root.dataset.snpMode:'reference';
root.dataset.greenStatus=greenBrand.status;
if(greenBrand.status==='confirmed'&&greenBrand.accent&&greenBrand.accentText){
 root.style.setProperty('--green-accent',greenBrand.accent);root.style.setProperty('--green-accent-text',greenBrand.accentText);
}
function apply(mode:Mode,persist:boolean){
 current=mode;root.dataset.snpMode=mode;
 document.querySelectorAll<HTMLButtonElement>('[data-ui-mode]').forEach(button=>{
  const selected=button.dataset.uiMode===mode;button.setAttribute('aria-pressed',String(selected));
 });
 let message=`${labels[mode]}로 전환했습니다. 입력 중인 내용은 유지됩니다.`;
 if(persist&&!preview){try{localStorage.setItem('snp.ui.mode.v1',mode);}catch{message+=' 현재 브라우저에서는 선택을 저장할 수 없습니다.';}}
 const live=document.querySelector<HTMLElement>('#snp-mode-status');if(live)live.textContent=message;
}
apply(current,false);
document.querySelectorAll<HTMLButtonElement>('[data-ui-mode]').forEach(button=>{
 button.addEventListener('click',()=>{const mode=button.dataset.uiMode;if(valid(mode))apply(mode,true);});
 button.addEventListener('keydown',event=>{
  if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
  event.preventDefault();const index=modes.indexOf(current);
  const mode=event.key==='Home'?modes[0]:event.key==='End'?modes[2]:modes[(index+(event.key==='ArrowRight'?1:2))%3];
  apply(mode,true);document.querySelector<HTMLButtonElement>(`[data-ui-mode="${mode}"]`)?.focus();
 });
});
window.addEventListener('storage',event=>{if(!preview&&event.key==='snp.ui.mode.v1'&&valid(event.newValue))apply(event.newValue,false);});
const menuButton=document.querySelector<HTMLButtonElement>('#snp-nav-toggle');
const navigation=document.querySelector<HTMLElement>('#snp-navigation');
function closeMenu(){root.dataset.mobileNav='false';menuButton?.setAttribute('aria-expanded','false');}
menuButton?.addEventListener('click',()=>{const open=root.dataset.mobileNav!=='true';root.dataset.mobileNav=String(open);menuButton.setAttribute('aria-expanded',String(open));});
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&root.dataset.mobileNav==='true'){closeMenu();menuButton?.focus();}});
navigation?.addEventListener('click',event=>{if((event.target as Element).closest('a'))closeMenu();});
const path=window.location.pathname;
document.querySelectorAll<HTMLAnchorElement>('.snp-navigation a').forEach(link=>{
 if(new URL(link.href).pathname===path){link.setAttribute('aria-current','page');link.closest('details')?.setAttribute('open','');}
});
const groups=document.querySelectorAll<HTMLDetailsElement>('.snp-nav details');
if(!document.querySelector('.snp-nav details[open]'))groups[0]?.setAttribute('open','');
groups.forEach(group=>{
 group.addEventListener('pointerenter',()=>{if(current==='reference'&&window.innerWidth>960)group.open=true;});
 group.addEventListener('pointerleave',()=>{if(current==='reference'&&window.innerWidth>960&&!group.contains(document.activeElement))group.open=false;});
});
const workspace=document.querySelector<HTMLElement>('#snp-workspace');
const heading=workspace?.querySelector<HTMLElement>('h1');
const locationLabel=document.querySelector<HTMLElement>('#snp-current-page');
if(locationLabel)locationLabel.textContent=heading?.textContent?.trim()||document.title.split('|')[0].trim();
if(workspace){
 workspace.querySelectorAll<HTMLElement>('table').forEach((table,index)=>{
  if(table.parentElement?.closest('table')||table.parentElement?.classList.contains('snp-table-frame'))return;
  const frame=document.createElement('div');frame.className='snp-table-frame';frame.tabIndex=0;
  frame.setAttribute('role','region');frame.setAttribute('aria-label',`${heading?.textContent?.trim()||'업무'} 표 ${index+1} 가로 스크롤`);
  table.before(frame);frame.append(table);
 });
 workspace.querySelectorAll<HTMLElement>('.errorlist').forEach(error=>error.setAttribute('role','alert'));
 if(preview){
  workspace.querySelectorAll<HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement|HTMLButtonElement>('input,select,textarea,button').forEach(control=>control.disabled=true);
  workspace.addEventListener('submit',event=>event.preventDefault(),true);
  document.addEventListener('click',event=>{if((event.target as Element).closest('a'))event.preventDefault();},true);
 }
}
// Keep Bootstrap's existing dismissible feedback without a remote CDN dependency.
document.querySelectorAll<HTMLElement>('.alert[data-dismissible],.alert-dismissible').forEach(element=>Alert.getOrCreateInstance(element));
// Comparison frames load the very same Django views/data and never persist their mode.
const compareSelect=document.querySelector<HTMLSelectElement>('#snp-compare-page');
compareSelect?.addEventListener('change',()=>{
 const allowed=['/','/procurement/workflow/','/inventory/ingredients/','/meals/mealplan/weekly/','/procurement/workflow/ledger/','/meals/cooking/'];
 if(!allowed.includes(compareSelect.value))return;
 document.querySelectorAll<HTMLIFrameElement>('[data-snp-preview-mode]').forEach(frame=>frame.src=compareSelect.value+'?snp_preview=1');
});
export {};

// Signup identity changes presentation only; the server validates every field.
const supplierFields=document.querySelector<HTMLDetailsElement>('.fresh-supplier-fields');
const signupTypes=document.querySelectorAll<HTMLInputElement>('input[name=signup_type]');
if(supplierFields&&signupTypes.length){
 const updateSignup=()=>{const supplier=Array.from(signupTypes).some(input=>input.checked&&input.value==='SUPPLIER');supplierFields.open=supplier;};
 signupTypes.forEach(input=>input.addEventListener('change',updateSignup));updateSignup();
}
