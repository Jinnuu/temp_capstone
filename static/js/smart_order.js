/* Replenishments carry forward across every meal, menu, and order-day group. */
function calculateSmartOrderQuantities(items) {
  const balances = new Map();
  const round = value => Math.round((value + Number.EPSILON) * 100) / 100;
  return items.map(item => {
    const key = String(item.ingredientId);
    const currentStock = balances.has(key) ? balances.get(key) : Number(item.initialStock);
    const neededQty = round(Number(item.neededQty));
    const orderQty = round(Math.max(0, neededQty + Number(item.safeStock) - currentStock));
    balances.set(key, round(currentStock + orderQty - neededQty));
    return {neededQty, currentStock, orderQty};
  });
}
if (typeof module !== 'undefined') module.exports = {calculateSmartOrderQuantities};
