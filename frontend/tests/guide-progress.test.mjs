import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeProgress,markRead,move,percentage,progressKey} from '../src/guide-progress.mjs';

test('malformed progress resets to a safe reading state',()=>{
 for(const value of [null,[],1,'oops',{current:NaN},{current:99}])assert.deepEqual(normalizeProgress(value),{current:1,completed:[]});
});
test('completion is a distinct bounded set of step integers',()=>{
 assert.deepEqual(normalizeProgress({current:3,completed:[0,1,1,2,'3',4,7,-1,true]}),{current:3,completed:[1,2,4]});
});
test('unknown fields and business values never enter stored state',()=>{
 assert.deepEqual(normalizeProgress({current:2,completed:[1],final_headcount:999,order_status:'완료'}),{current:2,completed:[1]});
});
test('previous next do not complete any business or reading task',()=>{
 assert.deepEqual(move({current:1,completed:[]},1),{current:2,completed:[]});
 assert.equal(move({current:1,completed:[]},-1).current,1);
 assert.equal(move({current:6,completed:[]},1).current,6);
});
test('reading acknowledgement is idempotent and remains local state',()=>{
 assert.deepEqual(markRead(markRead({current:2,completed:[]})),{current:2,completed:[2]});
});
test('100 percent requires six explicit reading acknowledgements',()=>{
 let state=normalizeProgress(null);assert.equal(percentage(state),0);
 for(let i=1;i<=6;i++)state=markRead({...state,current:i});
 assert.equal(percentage(state),100);assert.deepEqual(Object.keys(state).sort(),['completed','current']);
});
test('storage namespaces are user scoped without usernames',()=>{
 assert.notEqual(progressKey('1'),progressKey('2'));assert.equal(progressKey(''),null);assert.equal(progressKey('admin'),null);
});
