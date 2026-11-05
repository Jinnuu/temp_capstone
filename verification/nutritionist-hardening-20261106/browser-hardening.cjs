const {chromium}=require('/tmp/snp-browser/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs');
const root='verification/nutritionist-hardening-20261106',base='http://127.0.0.1:18021';
const fixture=JSON.parse(fs.readFileSync(root+'/hardening-fixture.json'));
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/home/woohyeak/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome',args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1920,height:1080},acceptDownloads:true});
 const page=await context.newPage(),steps=[],errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const login=async name=>{await page.goto(base+'/accounts/login/');await page.locator('[name=username]').fill(name);await page.locator('[name=password]').fill('isolated-browser-only');await page.getByRole('button',{name:'로그인',exact:true}).click();};
 const save=name=>steps.push(name);
 try{
  await login('fresh-sub');await page.goto(base+'/procurement/workflow/suppliers/');
  const token=await page.locator('[name=csrfmiddlewaretoken]').first().inputValue();
  let r=await context.request.post(`${base}/procurement/workflow/suppliers/${fixture.protected_user}/`,{form:{csrfmiddlewaretoken:token,username:'forged-browser-admin',name:'금지 변경',phone_number:''}});
  assert.equal(r.status(),403);
  r=await context.request.post(`${base}/procurement/suppliers/${fixture.protected_profile}/update/`,{form:{csrfmiddlewaretoken:token,user:String(fixture.protected_user),name:'금지 변경',category:'농산물'}});
  assert.equal(r.status(),403);save('SUB cannot edit supplier-admin through either legacy POST with valid CSRF');
  await page.goto(base+'/procurement/workflow/suppliers/');assert.match(await page.locator('main').innerText(),/보호 관리자 업체/);save('rejected edits preserve original account and profile');
  await login('verify-nutritionist');await page.goto(base+'/forecasting/weekly-forecast-report/?date=2026-11-06');
  for(const text of ['AI 예측 식수','수동 예상 식수','최종 확정 식수','실제 식수','미입력','산출 불가'])assert.match(await page.locator('main').innerText(),new RegExp(text));
  let json=await(await context.request.get(base+'/forecasting/weekly-forecast-report/?date=2026-11-06&format=json')).json();
  const dinner=json.report_items.find(x=>x.date==='2026-11-06'&&x.meal_type==='석식');assert.equal(dinner.manual_count,360);assert.equal(dinner.final_count,351);assert.equal(dinner.actual_count,null);assert.equal(dinner.error_rate,null);save('HTML and JSON preserve AI/manual360/final351/actual-null semantics');
  const download=page.waitForEvent('download');await page.getByRole('link',{name:'엑셀 다운로드',exact:true}).click();await(await download).saveAs(root+'/forecast.xlsx');save('actual attendance report Excel downloads from real browser');
  await page.goto(base+'/meals/mealplan/upload/');await page.locator('[name=file]').setInputFiles({name:'protected.csv',mimeType:'text/csv',buffer:Buffer.from('\ufeff날짜,끼니,메뉴명,식수\n2026-11-04,중식,덮어쓰기,999\n')});await page.getByRole('button',{name:'식단 일괄 등록',exact:true}).click();assert.match(await page.locator('body').innerText(),/사용 완료/);
  json=await(await context.request.get(base+'/forecasting/weekly-forecast-report/?date=2026-11-04&format=json')).json();const served=json.report_items.find(x=>x.date==='2026-11-04');assert.equal(served.manual_count,120);assert.equal(served.final_count,100);assert.deepEqual(served.menus,['보존 식단 메뉴']);save('served meal upload fails with original headcounts and menu intact');
  await page.goto(base+'/procurement/orders/3/');assert.match(await page.locator('main').innerText(),/세금 기준 미등록/);assert.doesNotMatch(await page.locator('main').innerText(),/부가가치세 \(10%\)/);save('order detail never fabricates a 10-percent payable amount');
  for(const mode of ['green','civic']){
   await page.goto(base+'/?date=2026-11-06');await page.locator(`[data-ui-mode=${mode}]`).click();
   assert.ok(await page.locator('.fresh-confirmed td').first().evaluate(e=>parseFloat(getComputedStyle(e).fontSize)>=14));
   await page.screenshot({path:`${root}/${mode}-dashboard.png`});
   await page.setViewportSize({width:390,height:844});assert.ok(await page.locator('.fresh-dashboard-intro .fresh-hero img').evaluate(e=>e.getBoundingClientRect().height<=73));
   await page.screenshot({path:`${root}/${mode}-mobile.png`});await page.setViewportSize({width:1920,height:1080});
  }save('Green/Civic summary text is at least14px and mobile banner photo at most73px');
  await login('fresh-supplier-a');await page.goto(base+'/procurement/portal/');
  for(const detail of await page.locator('.snp-nav details').all())assert.ok((await detail.locator('a').count())>0);
  save('supplier navigation has no empty internal groups');
  assert.deepEqual(errors,[]);fs.writeFileSync(root+'/browser-hardening.json',JSON.stringify({passed:true,steps,pageErrors:errors,scope:'task tmpfs SQLite only'},null,2));console.log('HARDENING_BROWSER_PASS',steps.length,'checkpoints');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
