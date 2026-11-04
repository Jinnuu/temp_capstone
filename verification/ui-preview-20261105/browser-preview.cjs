// Execute the existing business assertions through the real preview proxy.
// Keep demo credentials outside Git and avoid passing them as command arguments.
const fs=require('node:fs'),Module=require('node:module'),path=require('node:path');
const password=fs.readFileSync('.ui-preview/demo_password','utf8').trim();
let source=fs.readFileSync('verification/ui-three-modes-20261105/business-flow.cjs','utf8').replaceAll("'isolated-browser-only'",'process.env.SNP_PREVIEW_TEST_PASSWORD');
if(process.env.SNP_PREVIEW_RESUME==='after-meals'){
 const start=source.indexOf('  // No business fixtures:');
 const end=source.indexOf("  await page.goto(base+'/procurement/workflow/preview/');",start);
 if(start<0||end<start)throw new Error('Resume boundary not found');
 source=source.slice(0,start)+"  await login(page,'verify-admin');\n"+source.slice(end);
}
process.env.SNP_PREVIEW_TEST_PASSWORD=password;
const file=path.resolve('verification/ui-three-modes-20261105/business-flow.cjs');
const runner=new Module(file,module);runner.filename=file;runner.paths=module.paths;runner._compile(source,file);
