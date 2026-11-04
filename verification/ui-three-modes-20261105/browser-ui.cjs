const {chromium}=require('/tmp/snp-browser/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const base=process.env.SNP_BROWSER_BASE;assert.ok(base);
const root='verification/ui-three-modes-20261105',shots='docs/ui-redesign/screenshots';
const modes=['reference','green','civic'],steps=[],errors=[];
const executablePath='/home/woohyeak/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome';
(async()=>{
const profile=fs.mkdtempSync(path.join(os.tmpdir(),'snp-ui-profile-'));
let context=await chromium.launchPersistentContext(profile,{headless:true,executablePath,args:['--no-sandbox'],viewport:{width:1920,height:1080}});
const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
const save=(name,detail)=>steps.push({name,detail});
const switchMode=async(mode)=>{await page.locator(`[data-ui-mode=${mode}]`).click();await page.waitForFunction(m=>document.documentElement.dataset.snpMode===m,mode);assert.equal(await page.locator(`[data-ui-mode=${mode}]`).getAttribute('aria-pressed'),'true');};
try{
await page.goto(base+'/accounts/login/');await page.locator('[name=username]').fill('verify-admin');await page.locator('[name=password]').fill('isolated-browser-only');await page.getByRole('button',{name:'로그인',exact:true}).click();
await page.goto(base+'/procurement/workflow/');await page.locator('[name=manual]').fill('407');await page.locator('[name=final]').fill('399');await page.locator('[name=confirm]').check();await page.evaluate(()=>window.__originalInput=document.querySelector('[name=manual]'));
const dimensions=[];
for(const mode of modes){await switchMode(mode);assert.equal(await page.locator('[name=manual]').inputValue(),'407');assert.equal(await page.locator('[name=final]').inputValue(),'399');assert.ok(await page.locator('[name=confirm]').isChecked());assert.ok(await page.evaluate(()=>window.__originalInput===document.querySelector('[name=manual]')));dimensions.push(await page.evaluate(()=>{const n=document.querySelector('#snp-navigation').getBoundingClientRect(),h=document.querySelector('.snp-header').getBoundingClientRect();return {mode:document.documentElement.dataset.snpMode,nav:{x:n.x,y:n.y,width:n.width},header:{x:h.x,y:h.y,width:h.width},accent:getComputedStyle(document.documentElement).getPropertyValue('--snp-accent').trim()};}));}
assert.equal(dimensions[0].nav.x,0);assert.ok(dimensions[1].header.x>200);assert.equal(dimensions[2].header.x,0);assert.ok(dimensions[2].nav.width<250);assert.equal(dimensions[1].accent,'#286447');save('three independent layouts + unsaved work',{dimensions,unchangedDOM:true});
await page.locator('[data-ui-mode=civic]').press('Home');assert.equal(await page.locator('html').getAttribute('data-snp-mode'),'reference');await page.locator('[data-ui-mode=reference]').press('ArrowRight');assert.equal(await page.locator('html').getAttribute('data-snp-mode'),'green');await page.goto(base+'/inventory/ingredients/');assert.equal(await page.locator('html').getAttribute('data-snp-mode'),'green');save('keyboard and navigation persistence','Home/ArrowRight selects green; subsequent page green');
await page.goto(base+'/meals/menu/upload-excel/');await page.locator('[name=file]').setInputFiles(root+'/flows/civic/recipe-upload.xlsx');for(const mode of modes){await switchMode(mode);assert.equal(await page.locator('[name=file]').evaluate(e=>e.files[0].name),'recipe-upload.xlsx');}save('file selection preserved','same input/file survives all three switches without submit');
await page.goto(base+'/meals/cooking/?date=2026-11-06');const cookingUrl=await page.getByRole('link',{name:'2026-11-06 석식 조리지시서',exact:true}).getAttribute('href');
const pages=[['dashboard','/?date=2026-11-06&year=2026&month=11'],['inventory','/inventory/ingredients/'],['headcount','/procurement/workflow/'],['procurement','/procurement/workflow/plans/1/'],['ledger','/procurement/workflow/ledger/?start_date=2026-11-02&end_date=2026-11-08'],['cooking',cookingUrl],['mealplan','/meals/mealplan/weekly/?start_date=2026-11-02'],['recipe','/procurement/workflow/recipes/']];
for(const [name,url] of pages){await page.goto(base+url);await page.locator('#snp-workspace').waitFor();let sameData;
 for(const mode of modes){await switchMode(mode);await page.waitForTimeout(90);const data=await page.locator('#snp-workspace').innerText();if(sameData===undefined)sameData=data;else assert.equal(data,sameData,name+' data changes across mode');await page.screenshot({path:`${shots}/${mode}-${name}.png`,fullPage:false});assert.ok((await page.locator('[data-ui-mode='+mode+']').boundingBox()).y>=0);}
 save('same live data: '+name,'three 1920x1080 screenshots; text invariant');
}
await page.goto(base+'/ui/compare/');
for(const mode of modes){const frame=page.frameLocator(`[data-snp-preview-mode=${mode}]`);await frame.locator('html[data-snp-mode='+mode+']').waitFor();await frame.locator('main input, main select, main button').first().waitFor({state:'attached'});assert.equal(await frame.locator('main input:not([disabled]),main button:not([disabled]),main select:not([disabled])').count(),0);}
const stored=await page.evaluate(()=>localStorage.getItem('snp.ui.mode.v1'));await page.locator('#snp-compare-page').selectOption('/inventory/ingredients/');
for(const mode of modes){const frame=page.frameLocator(`[data-snp-preview-mode=${mode}]`);await frame.locator('html[data-snp-mode='+mode+']').waitFor();await frame.getByRole('heading',{name:'식자재',exact:true}).waitFor();}
assert.equal(await page.evaluate(()=>localStorage.getItem('snp.ui.mode.v1')),stored);await page.screenshot({path:shots+'/comparison.png'});save('comparison isolation','same views; frames pinned, controls disabled, parent selection unchanged');
await page.goto(base+'/procurement/workflow/ledger/?start_date=2026-11-02&end_date=2026-11-08');await page.setViewportSize({width:768,height:1024});
for(const mode of modes){await switchMode(mode);assert.ok(await page.locator('#snp-nav-toggle').isVisible());await page.locator('#snp-nav-toggle').click();assert.equal(await page.locator('#snp-nav-toggle').getAttribute('aria-expanded'),'true');await page.keyboard.press('Escape');assert.equal(await page.locator('#snp-nav-toggle').getAttribute('aria-expanded'),'false');assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2),'body overflow '+mode);await page.screenshot({path:shots+'/'+mode+'-tablet.png'});}
save('tablet/keyboard navigation','768px all modes, Escape closes, horizontal tables contained');
await page.setViewportSize({width:1920,height:1080});await page.goto(base+cookingUrl);
for(const mode of modes){await switchMode(mode);await page.emulateMedia({media:'print'});assert.equal(await page.locator('.snp-header').isVisible(),false);await page.pdf({path:root+'/'+mode+'-cooking.pdf',preferCSSPageSize:true,printBackground:true});await page.emulateMedia({media:'screen'});}save('print chrome excluded','all three PDFs with actual business sheet');
await page.goto(base+'/admin/');await switchMode('green');assert.ok(await page.locator('#site-name').isVisible());save('admin compatibility','native admin + mode selector, no Bootstrap global admin replacement');
await context.close();context=await chromium.launchPersistentContext(profile,{headless:true,executablePath,args:['--no-sandbox'],viewport:{width:1920,height:1080}});const reopened=await context.newPage();await reopened.goto(base+'/');assert.equal(await reopened.locator('html').getAttribute('data-snp-mode'),'green');save('browser restart persistence','new Chromium process retained last selection');
assert.deepEqual(errors,[]);fs.writeFileSync(root+'/ui-result.json',JSON.stringify({passed:true,steps,pageErrors:errors},null,2));console.log('UI_E2E_PASS',steps.length,'checkpoints');
}finally{await context.close();fs.rmSync(profile,{recursive:true,force:true});}
})().catch(e=>{console.error(e);process.exitCode=1;});
