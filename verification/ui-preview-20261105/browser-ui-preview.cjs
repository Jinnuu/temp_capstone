const fs=require('node:fs'),Module=require('node:module'),path=require('node:path');
process.env.SNP_PREVIEW_TEST_PASSWORD=fs.readFileSync('.ui-preview/demo_password','utf8').trim();
const file=path.resolve('verification/ui-three-modes-20261105/browser-ui.cjs');
let source=fs.readFileSync(file,'utf8').replaceAll("'isolated-browser-only'",'process.env.SNP_PREVIEW_TEST_PASSWORD').replace("const root='verification/ui-three-modes-20261105',shots='docs/ui-redesign/screenshots';","const root='verification/ui-preview-20261105/ui',shots='docs/ui-redesign/preview-screenshots';");
const runner=new Module(file,module);runner.filename=file;runner.paths=module.paths;runner._compile(source,file);
