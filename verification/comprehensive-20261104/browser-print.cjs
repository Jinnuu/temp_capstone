const {chromium}=require('/tmp/snp-browser/node_modules/playwright');const assert=require('node:assert/strict'),fs=require('node:fs');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'/home/woohyeak/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome',args:['--no-sandbox']});try{
 const page=await browser.newPage({viewport:{width:1920,height:1080}});const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route('https://**/*',r=>r.abort());
 const base=process.env.SNP_BROWSER_BASE;assert.ok(base);await page.goto(base+'/accounts/login/');await page.locator('[name=username]').fill('verify-admin');await page.locator('[name=password]').fill('isolated-browser-only');await page.getByRole('button',{name:'로그인',exact:true}).click();
 await page.goto(base+'/procurement/docs/monthly-settlement/?month=2026-11');assert.match(await page.locator('body').innerText(),/11700/);
 let called=false;await page.exposeFunction('recordQaPrint',()=>{called=true;});await page.evaluate(()=>{window.print=()=>window.recordQaPrint();});await page.getByRole('button',{name:'인쇄하기',exact:true}).click();await page.waitForTimeout(100);assert.equal(called,true);
 await page.emulateMedia({media:'print'});assert.equal(await page.locator('footer').isVisible(),false);assert.equal(await page.locator('.sp-top-button').isVisible(),false);assert.equal(await page.locator('.sp-main').evaluate(e=>getComputedStyle(e).padding),'0px');
 await page.pdf({path:'verification/comprehensive-20261104/settlement.pdf',preferCSSPageSize:true,printBackground:true});assert.deepEqual(errors,[]);
 fs.writeFileSync('verification/comprehensive-20261104/browser-print.json',JSON.stringify({passed:true,printButton:true,footerHidden:true,floatingButtonHidden:true,pageErrors:errors},null,2));console.log('MONTHLY_PRINT_PASS');
 }finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
