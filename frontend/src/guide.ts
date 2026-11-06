import {normalizeProgress,markRead,move,percentage,progressKey} from './guide-progress.mjs';

export function initGuide(){
 const element=document.querySelector<HTMLElement>('[data-guide]');if(element)setupGuide(element);
}

function setupGuide(guide:HTMLElement){
 const preview=document.documentElement.dataset.snpPreview==='true';
 const key=progressKey(guide.dataset.progressKey?.split('.').pop()||'');
 let state=normalizeProgress(null),storageOK=true;
 const status=guide.querySelector<HTMLElement>('[data-guide-status]');
 if(!preview&&key){try{const saved=localStorage.getItem(key);if(saved)state=normalizeProgress(JSON.parse(saved));}catch{storageOK=false;}}
 const steps=Array.from(guide.querySelectorAll<HTMLDetailsElement>('[data-guide-step]'));
 const choices=Array.from(guide.querySelectorAll<HTMLButtonElement>('[data-guide-go]'));
 function save(){if(preview||!key)return;try{localStorage.setItem(key,JSON.stringify(state));}catch{storageOK=false;}}
 function render(focus=false){
  const selected=state.current;
  for(const step of steps){const active=Number(step.dataset.guideStep)===selected;step.open=active;step.classList.toggle('is-current',active);}
  for(const button of choices){const number=Number(button.dataset.guideGo);button.toggleAttribute('data-read',state.completed.includes(number));if(number===selected)button.setAttribute('aria-current','step');else button.removeAttribute('aria-current');}
  const progress=guide.querySelector<HTMLProgressElement>('[data-guide-progress]');if(progress)progress.value=state.completed.length;
  const text=guide.querySelector<HTMLElement>('[data-guide-progress-text]');if(text)text.textContent=`읽은 단계 ${state.completed.length} / 6 (${percentage(state)}%)`;
  const previous=guide.querySelector<HTMLButtonElement>('[data-guide-prev]');if(previous)previous.disabled=preview||selected===1;
  const next=guide.querySelector<HTMLButtonElement>('[data-guide-next]');if(next)next.disabled=preview||selected===6;
  const read=guide.querySelector<HTMLButtonElement>('[data-guide-read]');if(read){read.setAttribute('aria-pressed',String(state.completed.includes(selected)));read.textContent=state.completed.includes(selected)?'이 단계 읽음 표시됨':'이 단계 읽음 표시';}
  if(status)status.textContent=storageOK?`${selected}단계 안내입니다. 읽음 표시는 실제 업무를 저장하거나 확정하지 않습니다.`:'브라우저 저장을 사용할 수 없어 현재 화면에서만 진행합니다. 업무 메뉴는 정상 이용할 수 있습니다.';
  if(focus)steps[selected-1]?.querySelector<HTMLElement>('h2')?.focus();
 }
 function select(value:number){state=normalizeProgress({...state,current:value});save();render(true);}
 for(const button of choices){
  button.addEventListener('click',()=>select(Number(button.dataset.guideGo)));
  button.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();select(event.key==='Home'?1:event.key==='End'?6:move(state,event.key==='ArrowLeft'?-1:1).current);choices[state.current-1]?.focus();});
 }
 for(const step of steps)step.querySelector('summary')?.addEventListener('click',event=>{event.preventDefault();const number=Number(step.dataset.guideStep);if(number===state.current){step.open=!step.open;}else select(number);});
 guide.querySelector('[data-guide-prev]')?.addEventListener('click',()=>select(move(state,-1).current));
 guide.querySelector('[data-guide-next]')?.addEventListener('click',()=>select(move(state,1).current));
 guide.querySelector('[data-guide-read]')?.addEventListener('click',()=>{state=markRead(state);save();render();});
 guide.querySelector('[data-guide-reset]')?.addEventListener('click',()=>{state=normalizeProgress(null);save();render(true);});
 render();
}
