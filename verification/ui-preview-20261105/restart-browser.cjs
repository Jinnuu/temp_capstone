const {chromium}=require('/tmp/snp-browser/node_modules/playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
const phase=process.argv[2],base='http://127.0.0.1:8011',state='.ui-preview/browser-session.json';
assert.ok(['before','after'].includes(phase));
(async()=>{
const browser=await chromium.launch({headless:true,executablePath:'/home/woohyeak/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome',args:['--no-sandbox']});
const context=await browser.newContext(phase==='after'?{storageState:state}:{}),page=await context.newPage();
try{
if(phase==='before'){
 await page.goto(base+'/accounts/login/');await page.locator('[name=username]').fill('verify-nutritionist');await page.locator('[name=password]').fill(fs.readFileSync('.ui-preview/demo_password','utf8').trim());await page.getByRole('button',{name:'로그인',exact:true}).click();await page.locator('[data-ui-mode=green]').click();await context.storageState({path:state});fs.chmodSync(state,0o600);
}
await page.goto(base+'/procurement/workflow/ledger/?start_date=2026-11-02&end_date=2026-11-08');assert.ok(!page.url().includes('accounts/login'));assert.equal(await page.locator('html').getAttribute('data-snp-mode'),'green');
const text=await page.locator('table').first().innerText();assert.match(text,/5\.9/);assert.match(text,/0\.9/);
fs.writeFileSync('verification/ui-preview-20261105/restart-'+phase+'.json',JSON.stringify({passed:true,sessionRetained:true,mode:'green',ledgerRetained:true},null,2));console.log('RESTART_BROWSER_'+phase.toUpperCase()+'_PASS');
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
