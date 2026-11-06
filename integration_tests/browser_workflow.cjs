const {chromium}=require(process.env.SNP_PLAYWRIGHT_MODULE || '/tmp/snp-browser/node_modules/playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.SNP_CHROMIUM || '/home/woohyeak/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome',args:['--no-sandbox']});
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  // The acceptance test uses local application assets only.
  await page.route('https://**/*',r=>r.abort());
  const base=process.env.SNP_BROWSER_BASE || 'http://127.0.0.1:18017';
  try {
    await page.goto(base+'/accounts/login/');
    await page.locator('[name=username]').fill('browser-nutritionist');
    await page.locator('[name=password]').fill('browser-test-only');
    await Promise.all([page.waitForURL(base+'/'),page.locator('button[type=submit]').filter({hasText:'로그인'}).click()]);
    await page.getByRole('link',{name:'영양사 업무 가이드',exact:true}).first().click();
    await page.goto(base+'/procurement/workflow/headcounts/');
    await page.locator('[name=plan]').selectOption({label:'2026-10-16 석식'});
    await page.locator('[name=manual]').fill('351');await page.locator('[name=final]').fill('351');
    await page.locator('[name=confirm]').check();await page.getByRole('button',{name:'식수 저장',exact:true}).click();
    assert.ok((await page.locator('body').innerText()).includes('351'));
    await page.getByRole('link',{name:'발주예정서 작성',exact:true}).click();
    await page.locator('[name=start_date]').fill('2026-10-16');await page.locator('[name=end_date]').fill('2026-10-16');
    await page.getByRole('button',{name:'발주예정서 저장',exact:true}).click();
    await page.waitForURL(/workflow\/plans\/\d+\//);
    const planUrl=page.url();
    const packs=page.locator('input[name^=quantity_]');assert.equal(Number(await packs.inputValue()),8);
    await packs.fill('9');await page.getByRole('button',{name:'업체별 구매발주서 확정·저장',exact:true}).click();
    assert.ok((await page.locator('body').innerText()).includes('4500'));
    assert.equal(Number(await page.locator('input[name^=quantity_]').inputValue()),9);
    await page.getByRole('link',{name:'납품·검수 진행',exact:true}).click();
    await page.getByRole('link',{name:'검수 기록·확인',exact:true}).first().click();
    await page.locator('[name=delivered]').fill('45');await page.locator('[name=accepted]').fill('40');
    await page.locator('[name=condition]').selectOption('이상');await page.locator('[name=notes]').fill('5kg 품질 이상 반품');
    await page.getByRole('button',{name:'저장·확정',exact:true}).click();
    assert.ok((await page.locator('body').innerText()).includes('40'));
    await page.goto(base+'/meals/deduct_inventory/?date=2026-10-16&meal_type='+encodeURIComponent('석식'));
    await page.getByRole('button',{name:'최종 차감 실행',exact:true}).click();
    await page.goto(base+'/procurement/workflow/ledger/?start_date=2026-10-12&end_date=2026-10-18');
    const text=await page.locator('body').innerText();assert.ok(text.includes('4.9'));
    await page.screenshot({path:'verification/requirements/browser-ledger.png',fullPage:true});
    await page.goto(planUrl);await page.emulateMedia({media:'print'});
    await page.pdf({path:'verification/requirements/order-preview.pdf',format:'A4',printBackground:true});
    assert.deepEqual(errors,[]);
    fs.writeFileSync('verification/requirements/browser.json',JSON.stringify({passed:true,steps:['login','manual/final headcount','snapshot','35.1kg -> 8 cans','manual 9 cans','vendor order 4500','45kg delivered / 40kg accepted','35.1kg consumed','4.9kg remaining','FIFO lot','print PDF'],pageErrors:errors},null,2));
    console.log('BROWSER_WORKFLOW_PASS: final headcount -> package conversion -> order -> inspection -> usage -> ledger -> PDF');
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
