const {chromium}=require('/tmp/snp-browser/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
const base='http://127.0.0.1:18031',root='verification/tutorial-preview-20261106',guide=base+'/procurement/workflow/';
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/home/woohyeak/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome',args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1920,height:1080},acceptDownloads:true}),p=await context.newPage(),steps=[],errors=[];
 let tracking=false,mutations=[];p.on('pageerror',e=>errors.push(e.message));p.on('request',r=>{if(tracking&&!['GET','HEAD'].includes(r.method()))mutations.push(r.method());});
 const login=async(page,name)=>{await page.goto(base+'/accounts/login/');await page.locator('[name=username]').fill(name);await page.locator('[name=password]').fill('isolated-browser-only');await page.getByRole('button',{name:'로그인',exact:true}).click();};
 const checkpoint=name=>steps.push(name);
 try{
  await login(p,'verify-nutritionist');await p.goto(guide);tracking=true;
  assert.match(await p.locator('h1').innerText(),/영양사 업무 가이드/);assert.equal(await p.locator('main [name=manual]').count(),0);assert.equal(await p.locator('[data-guide-step]').count(),6);checkpoint('old bookmark opens six-step guide without operational headcount form');
  await p.locator('[data-guide-reset]').click();await p.locator('[data-guide-next]').click();assert.equal(await p.locator('[data-guide-go][aria-current=step]').getAttribute('data-guide-go'),'2');assert.match(await p.locator('[data-guide-progress-text]').innerText(),/0 \/ 6/);
  await p.locator('[data-guide-read]').click();await p.reload();assert.match(await p.locator('[data-guide-progress-text]').innerText(),/1 \/ 6/);assert.equal(await p.locator('[data-guide-go][aria-current=step]').getAttribute('data-guide-go'),'2');checkpoint('previous-next and reading acknowledgement persist separately across reload');
  await p.locator('[data-guide-go="1"]').focus();await p.keyboard.press('End');assert.equal(await p.locator('[data-guide-go][aria-current=step]').getAttribute('data-guide-go'),'6');await p.keyboard.press('Home');assert.equal(await p.locator('[data-guide-go][aria-current=step]').getAttribute('data-guide-go'),'1');checkpoint('keyboard Home and End change steps without completing them');
  for(let i=1;i<=6;i++){await p.locator(`[data-guide-go="${i}"]`).click();await p.locator('[data-guide-read]').click();}
  assert.match(await p.locator('[data-guide-progress-text]').innerText(),/100%/);assert.match(await p.locator('#guide-progress-note').innerText(),/실제 업무 완료율이 아닙니다/);assert.deepEqual(mutations,[]);checkpoint('six explicit acknowledgements reach100 percent with no POST or business API calls');
  const key=await p.locator('[data-guide]').getAttribute('data-progress-key');const state=JSON.parse(await p.evaluate(k=>localStorage.getItem(k),key));assert.deepEqual(Object.keys(state).sort(),['completed','current']);
  await p.locator('[data-guide-go="2"]').click();await p.getByRole('link',{name:'예상·최종 식수 관리',exact:true}).last().click();assert.match(p.url(),/headcounts\//);assert.ok(await p.locator('[name=manual]').isVisible());await p.goBack();assert.match(await p.locator('[data-guide-progress-text]').innerText(),/100%/);checkpoint('guide opens preserved independent headcount function and keeps reading progress on return');
  await p.locator('[data-guide-go="3"]').click();await p.getByRole('link',{name:'저장한 발주예정서',exact:true}).last().click();assert.ok((await p.locator('tbody a').count())>0);checkpoint('saved procurement plans remain reachable with detail links');
  await p.goto(guide);await p.locator('[data-guide-reset]').click();assert.match(await p.locator('[data-guide-progress-text]').innerText(),/0 \/ 6/);checkpoint('restart clears only this user reading progress');
  for(const mode of ['green','civic','reference']){
   await p.goto(guide);await p.locator(`[data-ui-mode=${mode}]`).click();await p.locator('[data-guide-go="1"]').click();
   await p.screenshot({path:`${root}/screenshots/${mode}-guide-desktop.png`});
   await p.setViewportSize({width:390,height:844});assert.ok(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));await p.screenshot({path:`${root}/screenshots/${mode}-guide-mobile.png`});
   await p.setViewportSize({width:1920,height:1080});
  }checkpoint('Green Civic Reference desktop and mobile guide layouts have no body overflow');
  await p.route('**/fresh-produce-original.png',route=>route.abort());await p.reload();assert.ok(await p.locator('[data-guide-next]').isEnabled());await p.locator('[data-guide-next]').click();assert.equal(await p.locator('[data-guide-go][aria-current=step]').getAttribute('data-guide-go'),'2');await p.unroute('**/fresh-produce-original.png');checkpoint('missing photograph does not block guide controls or content');
  await p.locator('[data-guide-read]').click();tracking=false;
  await login(p,'guide-second');await p.goto(guide);assert.match(await p.locator('[data-guide-progress-text]').innerText(),/0 \/ 6/);assert.notEqual(await p.locator('[data-guide]').getAttribute('data-progress-key'),key);checkpoint('different login on shared browser does not inherit another user reading progress');
  await login(p,'guide-viewer');await p.goto(guide);assert.equal(await p.locator('main a[href="/forecasting/predict/"]').count(),0);await p.goto(base+'/procurement/workflow/headcounts/');assert.equal(await p.locator('[name=manual]').count(),0);checkpoint('viewer receives authorized reading links and read-only headcounts');
  await login(p,'guide-cook');await p.goto(guide);assert.equal(await p.locator('main a[href="/procurement/workflow/headcounts/"]').count(),0);await p.locator('[data-guide-go="5"]').click();assert.ok(await p.getByRole('link',{name:'조리지시서 조회·수정·출력',exact:true}).isVisible());checkpoint('cook guide hides forecast and procurement links but exposes cooking');
  await login(p,'fresh-supplier-a');assert.equal((await context.request.get(guide)).status(),403);assert.equal((await context.request.get(base+'/procurement/portal/')).status(),200);checkpoint('ordinary supplier stays in portal and cannot open internal guide');
  const blocked=await browser.newContext();await blocked.addInitScript(()=>Object.defineProperty(window,'localStorage',{get(){throw new DOMException('Storage disabled','SecurityError');}}));const bp=await blocked.newPage();await login(bp,'verify-nutritionist');await bp.goto(guide);await bp.locator('[data-guide-next]').click();assert.match(await bp.locator('[data-guide-status]').innerText(),/현재 화면에서만/);await blocked.close();checkpoint('blocked browser storage preserves current-page navigation and visible explanation');
  const plain=await browser.newContext({javaScriptEnabled:false}),np=await plain.newPage();await login(np,'verify-nutritionist');await np.goto(guide);assert.equal(await np.locator('[data-guide-step][open]').count(),6);assert.ok(await np.getByRole('link',{name:'조리지시서 조회·수정·출력',exact:true}).isVisible());await plain.close();checkpoint('without JavaScript all six native details and real work links remain readable');
  assert.deepEqual(errors,[]);fs.writeFileSync(root+'/browser-guide.json',JSON.stringify({passed:true,steps,pageErrors:errors,scope:'task SQLite only; progress is local reading state'},null,2));console.log('GUIDE_BROWSER_PASS',steps.length,'checkpoints');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
