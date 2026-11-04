import {test} from 'node:test';import assert from 'node:assert/strict';import {readFileSync} from 'node:fs';import vm from 'node:vm';
const source=readFileSync(new URL('../../static/ui/boot.js',import.meta.url),'utf8');
function boot(saved,frameMode=null,blocked=false){const root={dataset:{}};vm.runInNewContext(source,{window:{frameElement:frameMode===null?null:{getAttribute:()=>frameMode}},document:{documentElement:root},localStorage:{getItem:()=>{if(blocked)throw Error('storage blocked');return saved;}}});return root.dataset;}
test('restores only a valid saved appearance',()=>assert.equal(boot('civic').snpMode,'civic'));
test('invalid stored values cannot create an arbitrary class',()=>assert.equal(boot('prototype').snpMode,'reference'));
test('blocked storage still renders the reference screen',()=>assert.equal(boot(null,null,true).snpMode,'reference'));
test('comparison frame overrides appearance without reading parent selection',()=>{assert.equal(boot('civic','green').snpMode,'green');assert.equal(boot('civic','green').snpPreview,'true');});
test('invalid frame parameters do not enable preview mode',()=>{assert.equal(boot('civic','invalid').snpMode,'civic');assert.equal(boot('civic','invalid').snpPreview,undefined);});
test('fresh browser uses the reference appearance',()=>assert.equal(boot(null).snpMode,'reference'));
