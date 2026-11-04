const {chromium}=require('/tmp/snp-browser/node_modules/playwright'),fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
const browser=await chromium.launch({headless:true,executablePath:'/home/woohyeak/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome',args:['--no-sandbox']});const page=await browser.newPage();
try{
await page.goto('http://127.0.0.1:8011/accounts/login/');await page.locator('[name=username]').fill('verify-nutritionist');await page.locator('[name=password]').fill(fs.readFileSync('.ui-preview/demo_password','utf8').trim());await page.getByRole('button',{name:'로그인',exact:true}).click();
await page.goto('http://127.0.0.1:8011/forecasting/');await page.locator('[name=prediction_date]').fill('2026-11-13');await page.locator('form:has([name=prediction_date]) button[type=submit]').click();await page.waitForURL(/results/, {timeout:120000});
const rows=await page.locator('main table').first().locator('tbody tr').allTextContents();assert.equal(rows.length,3);
for(const meal of ['breakfast','lunch','dinner'])assert.ok(rows.some(row=>row.includes('best_model_'+meal+'.pkl')));
fs.writeFileSync('verification/ui-preview-20261105/ai-final-image.json',JSON.stringify({passed:true,syntheticHistory:true,predictionDate:'2026-11-13',threeMealResults:rows,accuracyEvaluation:false},null,2));console.log('FINAL_IMAGE_AI_THREE_MEALS_PASS');
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
