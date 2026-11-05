// Exercise the deployed preview without creating/resetting any real account.
const {chromium}=require('/tmp/snp-browser/node_modules/playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
const base='https://ui.jinnuu.site',root='verification/rbac-20261105';
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/home/woohyeak/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome',args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1920,height:1080}}),page=await context.newPage(),steps=[],errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 const navigate=page.goto.bind(page);page.goto=async(url,options)=>{if(new URL(url).pathname==='/accounts/login/')await page.waitForTimeout(7000);return navigate(url,options);};
 const login=async(password)=>{await page.goto(base+'/accounts/login/');await page.locator('[name=username]').fill('verify-nutritionist');await page.locator('[name=password]').fill(password);const [r]=await Promise.all([page.waitForResponse(r=>r.request().method()==='POST'&&new URL(r.url()).pathname==='/accounts/login/'),page.getByRole('button',{name:'로그인',exact:true}).click()]);return r;};
 try{
  await page.goto(base+'/accounts/login/');await page.getByRole('button',{name:'로그인',exact:true}).click();assert.equal(await page.locator('main .errorlist').count(),2);assert.ok((await page.locator('main').innerText()).includes('필수'));steps.push('empty login form renders both required-field errors');
  const bad=await login('Wrong-Test-Only-Password');assert.equal(bad.status(),200);assert.ok(page.url().includes('/login/'));steps.push('invalid password rejected by form, not a CSRF/proxy error');
  const ok=await login(fs.readFileSync('.ui-preview/demo_password','utf8').trim());assert.equal(ok.status(),302);await page.waitForURL(base+'/');await page.reload();assert.equal(page.url(),base+'/');
  const cookies=await context.cookies(base);for(const name of ['snp_ui_preview_session','snp_ui_preview_csrf'])assert.equal(cookies.find(c=>c.name===name).secure,true);steps.push('existing active account HTTPS login, session reload and Secure cookies');
  for(const path of ['/meals/api/ingredients/search/?q=preview','/meals/api/menus/search/?q=preview']){const api=await context.request.get(base+path);assert.equal(api.status(),200);await api.json();}steps.push('existing business search APIs preserve HTTPS session and JSON responses');
  await page.getByRole('button',{name:'로그아웃',exact:true}).click();await page.waitForURL(/accounts\/login/);steps.push('CSRF-protected POST logout');
  for(const mode of ['reference','green','civic']){
   await page.locator(`[data-ui-mode=${mode}]`).click();
   for(const path of ['/accounts/login/','/accounts/signup/','/accounts/recovery/username/','/accounts/recovery/password/']){
    const r=await page.goto(base+path);assert.equal(r.status(),200);assert.equal(await page.locator('html').getAttribute('data-snp-mode'),mode);await page.locator('h1').waitFor();
    if(path.endsWith('/signup/')){assert.ok(await page.locator('[name=email]').isVisible());assert.match(await page.locator('main').innerText(),/회원가입 후 바로 로그인/);}
    if(path.includes('/recovery/')){assert.match(await page.locator('main').innerText(),/현재 실제 이메일 발송이 설정되지 않았습니다/);assert.ok(await page.getByRole('button',{name:'안내 메일 요청'}).isDisabled());}
   }
   await page.screenshot({path:root+'/public-'+mode+'-recovery.png'});
  }
  steps.push('all three modes show login/signup/username/password pages; email signup field present');
  steps.push('live recovery explicitly unavailable; no false delivery success');
  const token=(await context.cookies(base)).find(c=>c.name==='snp_ui_preview_csrf').value;
  for(const kind of ['username','password']){
   const r=await context.request.post(base+'/accounts/recovery/'+kind+'/',{form:{email:'not-a-real-recipient@example.invalid'},headers:{'X-CSRFToken':token,Origin:base,Referer:base+'/accounts/recovery/'+kind+'/'}});
   assert.equal(r.status(),503);assert.match(await r.text(),/메일이 발송되지 않았습니다/);
  }
  steps.push('valid-CSRF recovery POST fails explicitly with 503 while SMTP disabled');
  const missing=await context.request.post(base+'/accounts/login/',{form:{username:'verify-nutritionist',password:'Wrong-Test-Only-Password'}});assert.equal(missing.status(),403);steps.push('missing login CSRF token rejected');
  for(const origin of ['http://127.0.0.1:8011','http://100.65.149.96:8011']){const p=await context.newPage();const r=await p.goto(origin+'/accounts/login/');assert.equal(r.status(),200);assert.ok(await p.locator('[name=username]').isVisible());await p.close();}steps.push('local and Tailscale login pages remain reachable');
  await page.goto(base+'/accounts/login/');await page.locator('[name=username]').fill('verify-admin');await page.locator('[name=password]').fill(fs.readFileSync('.ui-preview/demo_password','utf8').trim());await page.getByRole('button',{name:'로그인',exact:true}).click();await page.waitForURL(base+'/');
  for(const mode of ['reference','green','civic']){await page.goto(base+'/accounts/manage/permissions/');await page.locator(`[data-ui-mode=${mode}]`).click();assert.match(await page.locator('main').innerText(),/accounts.manage/);assert.match(await page.locator('main').innerText(),/시스템 관리자/);await page.screenshot({path:root+'/public-'+mode+'-matrix.png'});}steps.push('HTTPS app-admin matrix works in all three modes');
  for(const username of ['wlsdngur12','swwlsdngur12']){await page.goto(base+'/accounts/manage/?q='+username);const row=page.locator('tbody tr').filter({has:page.getByRole('cell',{name:username,exact:true})});assert.match(await row.innerText(),/승인 완료/);}steps.push('confirmed signup accounts show approved status in live admin UI; owner passwords not used');
  await page.goto(base+'/accounts/manage/audit/');assert.match(await page.locator('main').innerText(),/account.approved_or_restored/);steps.push('HTTPS audit screen contains approval records');
  await page.getByRole('button',{name:'로그아웃',exact:true}).click();await page.waitForURL(/login/);
  assert.deepEqual(errors,[]);fs.writeFileSync(root+'/browser-public.json',JSON.stringify({passed:true,steps,pageErrors:errors,actualExternalEmailDelivery:false,newLiveAccountsCreated:false,livePasswordsReset:false},null,2));console.log('PUBLIC_AUTH_BROWSER_PASS',steps.length,'checkpoints');
 }catch(e){await page.screenshot({path:'.ui-preview/audit/rbac-20261105/public-browser-failure.png'});fs.writeFileSync('.ui-preview/audit/rbac-20261105/public-browser-error.txt',String(e.stack));console.error('Public auth browser failed; inspect private diagnostics.');process.exitCode=1;}
 finally{await browser.close();}
})();
