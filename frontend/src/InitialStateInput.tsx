import { useTranslation } from 'react-i18next';
import type { GraphData,InitialStateSpec } from './types';

export default function InitialStateInput({graph,vertex,state,draft,onDraft,apply,busy}:{graph:GraphData;vertex:boolean;state:InitialStateSpec;draft:string;onDraft:(text:string)=>void;apply:()=>void;busy:boolean}) {
  const {t}=useTranslation('components');const dimension=vertex?graph.vertices.length:graph.dimension;
  const labels=vertex?graph.vertices.map(x=>`|${x}⟩`):graph.directed_edges.map(([x,y])=>`|${x},${y}⟩`);
  return <div className="initial-json"><p className="sidebar-hint">{t('editor.stateHelp',{dimension})}</p>
    <details><summary>{t('editor.basisOrder')}</summary><p className="record-line">{labels.join(', ')}</p></details>
    <label htmlFor="initial-json">{t(state.kind==='pure'?'editor.pureJSON':'editor.mixedJSON')}</label>
    <textarea id="initial-json" value={draft} spellCheck={false} disabled={busy} onChange={e=>onDraft(e.target.value)} />
    <button className="reset-button" disabled={busy||dimension<1} onClick={()=>onDraft(JSON.stringify(state.kind==='pure'?Array.from({length:dimension},(_,i)=>[Number(i===0),0]):Array.from({length:dimension},(_,i)=>Array.from({length:dimension},(_,j)=>[Number(i===j)/dimension,0])),null,2))}>{t('editor.stateTemplate')}</button>
    <button className="reset-button" disabled={busy} onClick={apply}>{t('editor.applyInitial')}</button>
  </div>;
}
