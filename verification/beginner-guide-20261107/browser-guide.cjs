const {chromium}=require('/tmp/snp-browser/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
const base='http://127.0.0.1:18051',root='verification/beginner-guide-20261107',url=base+'/procurement/workflow/';
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/home/woohyeak/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome',args:['--no-sandbox']});
 const contexts=[],steps=[],errors=[],serverErrors=[];
 const setup=async(options={})=>{const c=await browser.newContext({viewport:{width:1920,height:1080},...options});contexts.push(c);await c.route('https://**/*',r=>r.abort());const p=await c.newPage();p.on('pageerror',e=>errors.push(e.message));p.on('response',r=>{if(r.url().startsWith(base)&&r.status()>=500)serverErrors.push(r.status());});return p;};
 const login=async(p,name)=>{await p.goto(base+'/accounts/login/');await p.locator('[name=username]').fill('beginner-'+name);await p.locator('[name=password]').fill('isolated-browser-only');await p.getByRole('button',{name:'로그인',exact:true}).click();};
 const list=async(p,n)=>{const index=p.locator('[data-guide-index]');if(!(await index.evaluate(e=>e.open)))await index.locator(':scope>summary').click();await p.locator(`[data-guide-go="${n}"]`).click();};
 try{
  const p=await setup();await login(p,'dietitian');await p.goto(url);
  const key=await p.locator('[data-guide]').getAttribute('data-progress-key');
  await p.evaluate(k=>localStorage.setItem(k,JSON.stringify({current:4,completed:[1,2,3]})),key);await p.reload();
  assert.match(await p.locator('[data-guide-progress-text]').innerText(),/3 \/ 6 \(50%\)/);assert.equal(await p.locator('[data-guide-step]:visible').count(),1);assert.match(await p.locator('[data-guide-step]:visible h2').innerText(),/주문한 재료가 잘 도착했나요/);steps.push('legacy v1 current4/read1,2,3 restored unchanged, one step visible');
  let mutations=[];p.on('request',r=>{if(!['GET','HEAD'].includes(r.method()))mutations.push(r.method()+' '+new URL(r.url()).pathname);});
  await p.locator('[data-guide-reset]').click();assert.match(await p.locator('[data-guide-progress-text]').innerText(),/0 \/ 6/);await p.getByRole('button',{name:'다음 단계',exact:true}).click();
  assert.equal(await p.locator('[data-guide-step]:visible').getAttribute('data-guide-step'),'2');assert.match(await p.locator('[data-guide-progress-text]').innerText(),/0 \/ 6/);assert.equal(await p.evaluate(()=>document.activeElement.tagName),'H2');
  await p.getByRole('button',{name:'이해했어요',exact:true}).click();await p.reload();assert.match(await p.locator('[data-guide-progress-text]').innerText(),/1 \/ 6/);steps.push('next focuses heading without auto-completion; explicit reading persists on reload');
  await p.locator('[data-guide-index]>summary').click();await p.locator('[data-guide-go="2"]').focus();await p.keyboard.press('End');assert.equal(await p.locator('[aria-current=step]').getAttribute('data-guide-go'),'6');await p.keyboard.press('Home');assert.equal(await p.locator('[aria-current=step]').getAttribute('data-guide-go'),'1');await p.keyboard.press('Enter');steps.push('full step list supports keyboard Home/End/Enter and closes on selection');
  const expected=['어떤 음식을 만들까요?','몇 명이 먹을까요?','어떤 재료가 얼마나 필요할까요?','주문한 재료가 잘 도착했나요?','이제 음식을 준비해 볼까요?','오늘 급식은 어떻게 마무리할까요?'];
  for(let n=1;n<=6;n++){
   await list(p,n);const card=p.locator('[data-guide-step]:visible');assert.equal(await card.locator('h2').innerText(),expected[n-1]);assert.match(await card.locator('.guide-example').innerText(),/카레/);assert.equal(await card.locator('[data-guide-try]').count(),1);assert.ok(await card.locator('[data-guide-try]').evaluate(e=>parseFloat(getComputedStyle(e).fontSize)>=16));assert.equal(await card.locator('[data-guide-more]').evaluate(e=>e.open),false);
   if(n===3){await card.locator('[data-guide-more]>summary').click();assert.match(await card.innerText(),/실제 레시피나 영양 기준이 아닙니다/);await card.locator('[data-guide-more]>summary').click();}
   const href=await card.locator('[data-guide-try]').getAttribute('href');assert.ok(href.startsWith('/')&&!href.includes('/deliveries/'));await card.locator('[data-guide-try]').click();assert.equal(p.url(),base+href);assert.ok(await p.locator('main h1').first().isVisible());await p.goBack();assert.equal(await p.locator('[data-guide-step]:visible').getAttribute('data-guide-step'),String(n));
   await p.locator('[data-guide-read]').click();
  }assert.match(await p.locator('[data-guide-progress-text]').innerText(),/100%/);assert.match(await p.locator('#guide-progress-note').innerText(),/실제 업무 완료율이 아닙니다/);steps.push('all six titles/curry examples/optional explanations and actual work links checked with back navigation');
  assert.deepEqual(mutations,[]);steps.push('guide reading, reset, navigation and work-link GETs generated zero business POST requests');
  for(const mode of ['green','civic','reference']){
   await p.locator(`[data-ui-mode=${mode}]`).click();await list(p,1);await p.screenshot({path:`${root}/screenshots/${mode}-step1-desktop.png`});
   await list(p,3);await p.screenshot({path:`${root}/screenshots/${mode}-step3-desktop.png`});
   await p.setViewportSize({width:390,height:844});await p.screenshot({path:`${root}/screenshots/${mode}-step3-mobile.png`,fullPage:true});
   for(let n=1;n<=6;n++){await list(p,n);assert.equal(await p.locator('[data-guide-step]:visible').count(),1);assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));const box=await p.locator('[data-guide-next]').boundingBox();assert.ok(box.height>=44);}
   await p.reload();assert.equal(await p.locator('html').getAttribute('data-snp-mode'),mode);await p.setViewportSize({width:1920,height:1080});
  }steps.push('all modes desktop/mobile; all six mobile steps no horizontal overflow and large navigation controls');
  await login(p,'second');await p.goto(url);assert.match(await p.locator('[data-guide-progress-text]').innerText(),/0 \/ 6/);assert.notEqual(await p.locator('[data-guide]').getAttribute('data-progress-key'),key);steps.push('shared browser separates reading progress by user');
  const viewer=await setup();await login(viewer,'viewer');await viewer.goto(url);assert.equal(await viewer.locator('main a[href="/forecasting/predict/"]').count(),0);await list(viewer,1);assert.match(await viewer.locator('[data-guide-try]:visible').getAttribute('href'),/mealplan_list/);steps.push('viewer primary links fall back to allowed read screen');
  const cook=await setup();await login(cook,'cook');await cook.goto(url);await list(cook,2);assert.equal(await cook.locator('[data-guide-try]:visible').count(),0);await list(cook,5);assert.equal(await cook.locator('[data-guide-try]:visible').count(),1);steps.push('cook cannot see forecast action, but can open cooking work');
  const supplier=await setup();await login(supplier,'supplier');assert.equal((await supplier.request.get(url)).status(),403);steps.push('ordinary supplier remains in separate portal');
  const blocked=await setup();await blocked.context().addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Storage disabled','SecurityError');}}));await login(blocked,'dietitian');await blocked.goto(url);await blocked.locator('[data-guide-next]').click();assert.match(await blocked.locator('[data-guide-status]').innerText(),/현재 화면에서만/);assert.equal(await blocked.locator('[data-guide-step]:visible').getAttribute('data-guide-step'),'2');steps.push('blocked storage still permits navigation with visible warning');
  const plain=await setup({javaScriptEnabled:false});await login(plain,'dietitian');await plain.goto(url);assert.equal(await plain.locator('[data-guide-step][open]').count(),6);assert.equal(await plain.locator('.guide-controls').isVisible(),false);assert.equal(await plain.locator('[data-guide-try]').count(),6);steps.push('without JS all six explanations and work links readable, inert controls hidden');
  assert.deepEqual(errors,[]);assert.deepEqual(serverErrors,[]);fs.writeFileSync(root+'/browser-results.json',JSON.stringify({passed:true,steps,pageErrors:errors,serverErrors,scope:'isolated MariaDB; synthetic accounts only; no work data fixtures or writes'},null,2));console.log('BROWSER_PASS',steps.length,'checkpoints');
 }finally{for(const c of contexts)await c.close();await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
