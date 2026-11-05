import { useEffect,useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { CustomGraphDraft,EditMode } from './customGraph';
import type { GraphData } from './types';
import { graphProblems,matrixProblem,parameterProblems } from './customGraph';

interface Props {
  draft:CustomGraphDraft;graph:GraphData;mode:EditMode;setMode:(mode:EditMode)=>void;busy:boolean;
  selected:number;edge:[number,number]|null;edgeStart:number|null;error:string|null;
  addNow:()=>void;connect:(a:number,b:number)=>void;selectEdge:(edge:[number,number]|null)=>void;
  deleteVertex:()=>void;deleteEdge:()=>void;clear:()=>void;
}
export default function CustomGraphTools(p:Props) {
  const {t}=useTranslation('components');
  const [a,setA]=useState(''),[b,setB]=useState('');
  const label=(x:number)=>`${p.draft.vertices.find(v=>v.id===x)?.label??x} · ${x}`;
  const problems=graphProblems(p.graph),matrices=p.graph.vertices.filter(x=>matrixProblem(p.draft,x,p.graph));
  const parameters=parameterProblems(p.draft,p.graph);
  return <div className="custom-tools">
    <p className="sidebar-hint">{t('editor.draftHelp')}</p>
    <div className="editor-modes" role="group" aria-label={t('editor.tools')}>{(['select','addVertex','addEdge','delete'] as EditMode[]).map(m=><button key={m} disabled={p.busy} className={m===p.mode?'active':''} aria-pressed={m===p.mode} onClick={()=>p.setMode(m)}>{t(`editor.modes.${m}`)}</button>)}</div>
    <p className="sidebar-hint">{t(`editor.modes.${p.mode}Help`)}</p>
    {p.edgeStart!==null && <p role="status" className="editor-feedback">{t('editor.edgeStart',{vertex:label(p.edgeStart)})}</p>}
    <button className="reset-button" disabled={p.busy||p.graph.vertices.length>=32} onClick={p.addNow}>{t('editor.addNow')}</button>
    <details><summary>{t('editor.keyboardTools')}</summary>
      <label>{t('editor.from')}<select value={a} disabled={p.busy} onChange={e=>setA(e.target.value)}><option value="">{t('editor.choose')}</option>{p.graph.vertices.map(x=><option key={x} value={x}>{label(x)}</option>)}</select></label>
      <label>{t('editor.to')}<select value={b} disabled={p.busy} onChange={e=>setB(e.target.value)}><option value="">{t('editor.choose')}</option>{p.graph.vertices.map(x=><option key={x} value={x}>{label(x)}</option>)}</select></label>
      <button className="reset-button" disabled={p.busy||!p.graph.vertices.includes(Number(a))||!p.graph.vertices.includes(Number(b))||a===''||b===''} onClick={()=>p.connect(Number(a),Number(b))}>{t('editor.connect')}</button>
      <label>{t('editor.selectedEdge')}<select value={p.edge?JSON.stringify(p.edge):''} disabled={p.busy} onChange={e=>p.selectEdge(e.target.value?JSON.parse(e.target.value):null)}><option value="">{t('editor.choose')}</option>{p.graph.edges.map(edge=><option key={String(edge)} value={JSON.stringify(edge)}>{label(edge[0])} — {label(edge[1])}</option>)}</select></label>
    </details>
    <button className="reset-button" disabled={p.busy||!p.graph.vertices.includes(p.selected)} onClick={p.deleteVertex}>{t('editor.deleteVertex')}</button>
    <button className="reset-button" disabled={p.busy||!p.edge} onClick={p.deleteEdge}>{t('editor.deleteEdge')}</button>
    <button className="reset-button" disabled={p.busy} onClick={p.clear}>{t('editor.clear')}</button>
    {p.error && <p role="alert" className="editor-warning">{t(`editor.problems.${p.error}`)}</p>}
    <div className="editor-validation" aria-live="polite">{problems.map(key=><p key={key}>{t(`editor.problems.${key}`)}</p>)}
      {matrices.length>0 && <p>{t('editor.matrixAttention',{vertices:matrices.map(label).join(', ')})}</p>}
      {parameters.length>0 && <p>{t('editor.parameterAttention',{vertices:parameters.map(label).join(', ')})}</p>}
      {!problems.length&&!matrices.length&&!parameters.length && <p>{t('editor.structureReady')}</p>}
    </div>
  </div>;
}

export function VertexName({id,label,busy,onRename}:{id:number;label:string;busy:boolean;onRename:(label:string)=>void}) {
  const {t}=useTranslation('components');const [name,setName]=useState(label);
  useEffect(()=>setName(label),[id,label]);
  return <div className="vertex-name"><label>{t('editor.displayLabel',{id})}<input value={name} maxLength={64} disabled={busy} onChange={e=>setName(e.target.value)} /></label><button className="text-button" disabled={busy||!name.trim()} onClick={()=>onRename(name)}>{t('editor.rename')}</button></div>;
}
