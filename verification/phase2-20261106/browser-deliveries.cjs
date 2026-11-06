// Isolated MariaDB + synthetic credentials only; never public Preview.
const {chromium}=require('/tmp/snp-browser/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
const base='http://127.0.0.1:18041',root='verification/phase2-20261106';
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/home/woohyeak/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome',args:['--no-sandbox']});
 const steps=[],errors=[],serverErrors=[];
 const contexts=[];
 const login=async(suffix)=>{
  const c=await browser.newContext({viewport:{width:1920,height:1080}});contexts.push(c);
  await c.route('https://**/*',r=>r.abort());
  const p=await c.newPage();p.on('pageerror',e=>errors.push(e.message));p.on('response',r=>{if(r.url().startsWith(base)&&r.status()>=500)serverErrors.push(r.status());});
  await p.goto(base+'/accounts/login/');await p.locator('[name=username]').fill('phase2-browser-'+suffix);await p.locator('[name=password]').fill('isolated-browser-only');await p.getByRole('button',{name:'로그인',exact:true}).click();return p;
 };
 try{
  const supplier=await login('a'),buyer=await login('buyer');
  await supplier.goto(base+'/procurement/portal/orders/');
  const href=await supplier.locator('main a[href^="/procurement/portal/orders/"]').first().getAttribute('href');
  // Order is unique in the isolated fixture. Use its rendered order URL.
  const order=href.match(/orders\/(\d+)\//)[1];
  const own=base+`/procurement/portal/orders/${order}/deliveries/`, internal=base+`/procurement/orders/${order}/deliveries/`;
  for(const [quantity,accepted] of [[60,55],[40,40],[5,5]]){
   await supplier.goto(own);const form=supplier.locator('form').filter({has:supplier.locator('[name=request_key]')});
   await form.locator('[name=expected_date]').fill(new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date()));
   await form.locator('[name=contact]').fill('합성 납품 담당자');await form.locator('[name^=q_]').fill(String(quantity));await form.getByRole('button',{name:'회차 등록',exact:true}).click();await supplier.reload();
   assert.match(await supplier.locator('main').innerText(),/구매자 검수 대기/);steps.push(`supplier registers ${quantity}kg and rereads pending inspection`);
   await buyer.goto(internal);const f=buyer.locator('form').filter({has:buyer.locator('[name=line]')});assert.equal(await f.count(),1);
   await f.locator('[name=delivered]').fill(String(quantity));await f.locator('[name=accepted]').fill(String(accepted));await f.locator('[name=notes]').fill(accepted<quantity?'5kg 품질 불합격':'합성 검사 확인');
   await f.getByRole('button',{name:'검수 확정 · 합격량 입고',exact:true}).click();await buyer.reload();
   assert.equal(await buyer.locator('form [name=line]').count(),0);steps.push(`buyer inspects ${accepted}/${quantity}kg and rereads immutable receipt`);
  }
  const values=await buyer.locator('main table tbody tr').first().locator('td').allTextContents();
  assert.match(values[1],/20.*통/);assert.equal(values[3].trim(),'105.000000');assert.equal(values[4].trim(),'100.000000');assert.equal(values[5].trim(),'5.000000');assert.equal(values[6].trim(),'0');
  assert.match(await buyer.locator('main').innerText(),/구매자 상태: 완료/);steps.push('20 explicit 5kg packages; delivered105 accepted100 rejected5 remaining0 completed');
  for(const mode of ['green','civic','reference']){
   await buyer.locator(`[data-ui-mode=${mode}]`).click();await buyer.screenshot({path:`${root}/screenshots/${mode}-buyer-desktop.png`});
   await supplier.goto(own);await supplier.locator(`[data-ui-mode=${mode}]`).click();await supplier.screenshot({path:`${root}/screenshots/${mode}-supplier-desktop.png`});
   await supplier.reload();assert.equal(await supplier.locator('html').getAttribute('data-snp-mode'),mode);
   await buyer.setViewportSize({width:390,height:844});assert.ok(await buyer.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));await buyer.screenshot({path:`${root}/screenshots/${mode}-buyer-mobile.png`});await buyer.setViewportSize({width:1920,height:1080});
  }steps.push('all three modes persist; desktop supplier/buyer and mobile buyer screenshots');
  const stranger=await login('b');assert.equal((await stranger.request.get(own)).status(),404);assert.equal((await supplier.request.get(internal)).status(),403);steps.push('cross-company IDOR404; supplier buyer-inspection403');
  await buyer.goto(base+'/procurement/workflow/ledger/');const ledger=await buyer.locator('main').innerText();assert.match(ledger,/분할 납품 검증 감자/);steps.push('weekly ledger includes synthetic ingredient');
  assert.deepEqual(errors,[]);assert.deepEqual(serverErrors,[]);
  fs.writeFileSync(root+'/browser-results.json',JSON.stringify({passed:true,steps,pageErrors:errors,serverErrors,scope:'new task-only MariaDB; synthetic users and orders'},null,2));console.log('BROWSER_PASS',steps.length,'checkpoints');
 }finally{for(const c of contexts)await c.close();await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
