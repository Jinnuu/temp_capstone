const {chromium}=require('/tmp/snp-browser/node_modules/playwright');
const fs=require('node:fs'),assert=require('node:assert/strict'),crypto=require('node:crypto');
let stage='initial';
const base='https://ui.jinnuu.site',root='verification/tutorial-preview-20261106';
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:'/home/woohyeak/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome',args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1920,height:1080}}),page=await context.newPage(),steps=[],errors=[],mutations=[],telemetry=[];
 await context.route('**/cdn-cgi/rum',route=>route.abort());
 page.on('pageerror',e=>errors.push(e.name));page.on('request',r=>{if(r.url().startsWith(base)&&!['GET','HEAD'].includes(r.method())){const path=new URL(r.url()).pathname;if(path==='/cdn-cgi/rum')telemetry.push(path);else mutations.push({method:r.method(),path});}});
 try{
  stage='login-page';const response=await page.goto(base+'/accounts/login/');assert.equal(response.status(),200);assert.ok(await page.locator('[name=username]').isVisible());assert.ok(await page.locator('[name=password]').isVisible());steps.push('public HTTPS login form renders without submitting credentials');fs.writeFileSync(root+'/public-progress.json',JSON.stringify({stage,steps},null,2));
  for(const mode of ['green','civic','reference']){stage='mode-'+mode;
   await page.locator(`[data-ui-mode=${mode}]`).click();await page.goto(base+'/accounts/signup/');
   assert.equal(await page.locator('html').getAttribute('data-snp-mode'),mode);assert.match(await page.locator('main').innerText(),/관리자 승인 후 업무/);await page.getByLabel('공급업체로 가입',{exact:true}).check();assert.match(await page.locator('main').innerText(),/계정 승인 후 로그인/);assert.doesNotMatch(await page.locator('main').innerText(),/회원가입 후 바로 로그인/);
   await page.screenshot({path:`${root}/screenshots/public-${mode}-signup.png`});await page.goto(base+'/accounts/login/');await page.reload();assert.equal(await page.locator('html').getAttribute('data-snp-mode'),mode);steps.push(mode+' persists across signup/login/reload; approval-required copy verified');fs.writeFileSync(root+'/public-progress.json',JSON.stringify({stage,steps},null,2));
  }
  for(const path of ['/procurement/workflow/','/procurement/workflow/headcounts/','/procurement/workflow/plans/','/accounts/manage/']){
   stage='protected-route'+path;const r=await context.request.get(base+path,{maxRedirects:0});assert.equal(r.status(),302);
  }steps.push('anonymous guide/headcount/plans/admin routes retain authentication redirects');fs.writeFileSync(root+'/public-progress.json',JSON.stringify({stage,steps},null,2));
  stage='secure-cookie';const secure=(await context.cookies()).filter(c=>c.name==='snp_ui_preview_csrf').every(c=>c.secure);assert.ok(secure);assert.ok((await context.cookies()).some(c=>c.name==='snp_ui_preview_csrf'));steps.push('anonymous CSRF cookie is Secure over Cloudflare HTTPS; values never recorded');fs.writeFileSync(root+'/public-progress.json',JSON.stringify({stage,steps},null,2));
  for(const file of ['snp-ui.js','snp-ui.css']){
   stage='asset-'+file;const r=await context.request.get(base+'/static/ui/build/'+file+'?v=tutorial-20261106');assert.equal(r.status(),200);
   const remote=crypto.createHash('sha256').update(await r.body()).digest('hex'),local=crypto.createHash('sha256').update(fs.readFileSync('static/ui/build/'+file)).digest('hex');assert.equal(remote,local);
  }steps.push('public JS/CSS bytes match tested build with new cache version');fs.writeFileSync(root+'/public-progress.json',JSON.stringify({stage,steps},null,2));
  assert.deepEqual(mutations,[]);assert.deepEqual(errors,[]);
  fs.writeFileSync(root+'/browser-public-readonly.json',JSON.stringify({passed:true,steps,pageErrors:errors,applicationMutationRequests:mutations,blockedCloudflareRumAttempts:telemetry.length,realUserLoginAttempted:false,realSignupSubmitted:false},null,2));console.log('PUBLIC_READONLY_PASS',steps.length,'checkpoints');
 }finally{await browser.close();}
})().catch(error=>{fs.writeFileSync(root+'/public-error.json',JSON.stringify({stage,name:error.name,actual:typeof error.actual==='number'||typeof error.actual==='boolean'?error.actual:undefined,expected:typeof error.expected==='number'||typeof error.expected==='boolean'?error.expected:undefined,message:String(error.message).replace(/https?:\/\/[^\s]+/g,'[URL]').slice(0,600)},null,2));console.error('Public read-only browser failed at',stage,error.name);process.exitCode=1;});
