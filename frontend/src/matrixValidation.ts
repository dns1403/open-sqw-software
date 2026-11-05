import type { Complex, Matrix } from './types';
export const UNITARY_TOLERANCE = 1e-10;
const realPattern = '[+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][+-]?\\d+)?';
const realRegex = new RegExp(`^${realPattern}$`);
/** Small grammar, never eval: decimal/exponent real or a+bi; JSON pairs also work. */
export function parseComplex(value: unknown): Complex {
  if (Array.isArray(value) && value.length===2 && value.every(x=>typeof x==='number' && Number.isFinite(x))) return [value[0],value[1]];
  if (typeof value==='number' && Number.isFinite(value)) return [value,0];
  if (typeof value!=='string') throw new Error('complex');
  const s=value.trim().replace(/−/g,'-');
  if (realRegex.test(s) && Number.isFinite(Number(s))) return [Number(s),0];
  if (!s.endsWith('i')) throw new Error('complex');
  const body=s.slice(0,-1).trim();
  const split=Array.from(body).findIndex((c,i)=>i>0 && (c==='+'||c==='-') && !/[eE]/.test(body[i-1]));
  const real=split<0?'0':body.slice(0,split).trim(), imag=(split<0?body:body.slice(split)).trim();
  const coefficient=imag===''||imag==='+'?'1':imag==='-'?'-1':imag.replace(/^([+-])\s+/, '$1');
  if (!realRegex.test(real) || !realRegex.test(coefficient)) throw new Error('complex');
  const result:Complex=[Number(real),Number(coefficient)];
  if (!result.every(Number.isFinite)) throw new Error('complex');
  return result;
}
export function parseMatrix(text:string,degree:number): Matrix {
  let data:unknown;
  try { data=JSON.parse(text); } catch { throw new Error('json'); }
  if (!Array.isArray(data) || data.length!==degree || degree<1 || data.some(row=>!Array.isArray(row)||row.length!==degree)) throw new Error('shape');
  return data.map(row=>row.map(parseComplex));
}
export function unitaryResidual(matrix:Matrix):number {
  const d=matrix.length; let residual=0;
  for(let i=0;i<d;i++) for(let j=0;j<d;j++) {
    let re=-(i===j?1:0),im=0;
    for(let k=0;k<d;k++) {const a=matrix[k][i],b=matrix[k][j]; re+=a[0]*b[0]+a[1]*b[1];im+=a[0]*b[1]-a[1]*b[0];}
    residual=Math.max(residual,Math.hypot(re,im));
  }
  return residual;
}
export function matrixCheck(text:string,degree:number):{matrix?:Matrix; residual?:number; error?:string} {
  try { const matrix=parseMatrix(text,degree),residual=unitaryResidual(matrix);
    return Number.isFinite(residual) && residual<=UNITARY_TOLERANCE ? {matrix,residual}:{residual,error:'unitary'};
  } catch(error) { return {error:error instanceof Error?error.message:'complex'}; }
}
