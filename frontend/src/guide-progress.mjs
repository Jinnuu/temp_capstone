export const stepCount=6;
const validStep=value=>Number.isInteger(value)&&value>=1&&value<=stepCount;
export function normalizeProgress(value){
 if(!value||typeof value!=='object'||Array.isArray(value)||!validStep(value.current))return {current:1,completed:[]};
 const completed=Array.isArray(value.completed)?[...new Set(value.completed.filter(validStep))].sort((a,b)=>a-b):[];
 return {current:value.current,completed};
}
export function markRead(value){const state=normalizeProgress(value);return normalizeProgress({...state,completed:[...state.completed,state.current]});}
export function move(value,delta){const state=normalizeProgress(value);return {...state,current:Math.max(1,Math.min(stepCount,state.current+(delta===-1?-1:1)))};}
export function percentage(value){return Math.round(normalizeProgress(value).completed.length/stepCount*100);}
export function progressKey(userId){return /^\d+$/.test(userId)?`snp.guide.nutritionist.v1.${userId}`:null;}
