// Limited developer smoke check, not a WCAG certification or browser-zoom audit.
const {chromium}=require('/tmp/snp-browser/node_modules/playwright');
const fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const b=await chromium.launch({headless:true,executablePath:'/home/woohyeak/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome',args:['--no-sandbox']});
 try{
  const p=await b.newPage({viewport:{width:1920,height:1080}}),root='verification/nutritionist-hardening-20261106';
  await p.goto('http://127.0.0.1:18021/accounts/login/');await p.locator('[name=username]').fill('verify-nutritionist');await p.locator('[name=password]').fill('isolated-browser-only');await p.getByRole('button',{name:'로그인',exact:true}).click();
  const rows=[];
  for(const mode of ['green','civic']){
   await p.goto('http://127.0.0.1:18021/?date=2026-11-06');await p.locator(`[data-ui-mode=${mode}]`).click();
   await p.evaluate(()=>document.body.style.zoom='200%');
   const metrics=await p.evaluate(()=>({viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,hasHeading:!!document.querySelector('h1')}));
   const focused=[];for(let i=0;i<12;i++){await p.keyboard.press('Tab');focused.push(await p.evaluate(()=>document.activeElement.tagName));}
   rows.push({mode,method:'CSS body zoom 200%, not browser native zoom',...metrics,noBodyOverflow:metrics.documentWidth<=metrics.viewport+2,keyboardReachesControls:focused.some(tag=>['BUTTON','INPUT','A','SUMMARY'].includes(tag))});
   await p.screenshot({path:`${root}/${mode}-css-zoom200.png`});
  }
  fs.writeFileSync(root+'/accessibility-smoke.json',JSON.stringify({rows,limitations:['Only dashboard smoke checks','No native browser zoom, screen-reader, contrast or WCAG acceptance certification']},null,2));
  assert.ok(rows.every(row=>row.noBodyOverflow&&row.keyboardReachesControls&&row.hasHeading));console.log('ACCESSIBILITY_SMOKE_PASS',rows.length,'mode checks');
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
