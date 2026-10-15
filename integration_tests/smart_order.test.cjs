const assert = require('node:assert/strict');
const {test} = require('node:test');
const {calculateSmartOrderQuantities} = require('../static/js/smart_order.js');

test('batch serving reserves safety stock once across repeated ingredients', () => {
  const result = calculateSmartOrderQuantities([10,10,10].map(neededQty => ({ingredientId:1,initialStock:8,safeStock:5,neededQty})));
  assert.deepEqual(result.map(x=>x.orderQty),[7,10,10]);
  assert.equal(result.reduce((s,x)=>s+x.orderQty,0),27);
});
test('each ingredient starts from its own real stock', () => {
  const result = calculateSmartOrderQuantities([
    {ingredientId:1,initialStock:20,safeStock:5,neededQty:10},
    {ingredientId:2,initialStock:0,safeStock:3,neededQty:2},
    {ingredientId:1,initialStock:20,safeStock:5,neededQty:10}
  ]);
  assert.deepEqual(result.map(x=>x.orderQty),[0,5,5]);
});
test('reapplying a different headcount starts from real stock', () => {
  const rows=[1,1,1].map(ingredientId=>({ingredientId,initialStock:8,safeStock:5,neededQty:2}));
  assert.equal(calculateSmartOrderQuantities(rows).reduce((s,x)=>s+x.orderQty,0),3);
  assert.equal(calculateSmartOrderQuantities(rows.map(x=>({...x,neededQty:10}))).reduce((s,x)=>s+x.orderQty,0),27);
});
test('fractional quantities remain stable to two decimal places', () => {
  const result=calculateSmartOrderQuantities([0.1,0.2].map(neededQty=>({ingredientId:1,initialStock:0,safeStock:0.1,neededQty})));
  assert.deepEqual(result.map(x=>x.orderQty),[0.2,0.2]);
});
