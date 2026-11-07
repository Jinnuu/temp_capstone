import {normalizeProgress,markRead,move,percentage,progressKey} from './guide-progress.mjs';

export function initGuide(){
 const element=document.querySelector<HTMLElement>('[data-guide]');if(element)setupGuide(element);
}

function setupGuide(guide:HTMLElement){
 guide.dataset.guideEnhanced='true';
 const index=guide.querySelector<HTMLDetailsElement>('[data-guide-index]');
 const preview=document.documentElement.dataset.snpPreview==='true';
 const key=progressKey(guide.dataset.progressKey?.split('.').pop()||'');
 let state=normalizeProgress(null),storageOK=true;
 const status=guide.querySelector<HTMLElement>('[data-guide-status]');
 if(!preview&&key){try{const saved=localStorage.getItem(key);if(saved)state=normalizeProgress(JSON.parse(saved));}catch{storageOK=false;}}
 const steps=Array.from(guide.querySelectorAll<HTMLDetailsElement>('[data-guide-step]'));
 const choices=Array.from(guide.querySelectorAll<HTMLButtonElement>('[data-guide-go]'));
 function save(){if(preview||!key)return;try{localStorage.setItem(key,JSON.stringify(state));}catch{storageOK=false;}}
 function render(focus=false){
  const selected=state.current;guide.dataset.guideStorage=storageOK?'ok':'blocked';
  for(const step of steps){const active=Number(step.dataset.guideStep)===selected;step.hidden=!active;step.open=active;step.classList.toggle('is-current',active);}
  for(const button of choices){const number=Number(button.dataset.guideGo);button.toggleAttribute('data-read',state.completed.includes(number));if(number===selected)button.setAttribute('aria-current','step');else button.removeAttribute('aria-current');}
  const progress=guide.querySelector<HTMLProgressElement>('[data-guide-progress]');if(progress)progress.value=state.completed.length;
  const text=guide.querySelector<HTMLElement>('[data-guide-progress-text]');if(text)text.textContent=`읽은 단계 ${state.completed.length} / 6 (${percentage(state)}%)`;
  const previous=guide.querySelector<HTMLButtonElement>('[data-guide-prev]');if(previous)previous.disabled=preview||selected===1;
  const next=guide.querySelector<HTMLButtonElement>('[data-guide-next]');if(next)next.disabled=preview||selected===6;
  const read=guide.querySelector<HTMLButtonElement>('[data-guide-read]');if(read){read.setAttribute('aria-pressed',String(state.completed.includes(selected)));read.textContent=state.completed.includes(selected)?'이해했어요 ✓':'이해했어요';}
  if(status)status.textContent=storageOK?(state.completed.length===6?'6단계를 모두 읽었어요. 실제 업무는 각 화면에서 확인하고 저장하세요.':`${selected}단계예요. 읽었다면 이해했어요를 눌러 주세요.`):'브라우저 저장을 사용할 수 없어 현재 화면에서만 진행합니다. 업무 메뉴는 정상 이용할 수 있습니다.';
  if(focus)steps[selected-1]?.querySelector<HTMLElement>('h2')?.focus();
 }
 function select(value:number,keyboardList=false){state=normalizeProgress({...state,current:value});save();if(index&&!keyboardList)index.open=false;render(!keyboardList);}
 for(const button of choices){
  button.addEventListener('click',()=>select(Number(button.dataset.guideGo)));
  button.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();select(event.key==='Home'?1:event.key==='End'?6:move(state,event.key==='ArrowLeft'?-1:1).current,true);choices[state.current-1]?.focus();});
 }
 for(const step of steps)step.querySelector('summary')?.addEventListener('click',event=>{event.preventDefault();const number=Number(step.dataset.guideStep);if(number===state.current){step.open=!step.open;}else select(number);});
 guide.querySelector('[data-guide-prev]')?.addEventListener('click',()=>select(move(state,-1).current));
 guide.querySelector('[data-guide-next]')?.addEventListener('click',()=>select(move(state,1).current));
 guide.querySelector('[data-guide-read]')?.addEventListener('click',()=>{state=markRead(state);save();render();});
 guide.querySelector('[data-guide-reset]')?.addEventListener('click',()=>{state=normalizeProgress(null);save();if(index)index.open=false;render(true);});
 render();
}
