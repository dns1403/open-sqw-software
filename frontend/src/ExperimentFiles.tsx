import { useRef,useState } from 'react';
import { useTranslation } from 'react-i18next';
import { ApiError,formatError,post } from './api';
import type { ExperimentDocument } from './customGraph';
import type { GraphData } from './types';

export default function ExperimentFiles({exportDocument,onImport,canExport,busy,onBusy}:{
  exportDocument:()=>ExperimentDocument;onImport:(document:ExperimentDocument,graph:GraphData)=>boolean|Promise<boolean>;canExport:boolean;busy:boolean;onBusy:(value:boolean)=>void;
}) {
  const {t}=useTranslation('components'),input=useRef<HTMLInputElement>(null);
  const [working,setWorking]=useState(false),[error,setError]=useState<unknown>(null),[status,setStatus]=useState<string|null>(null);
  async function load(file:File) {
    setWorking(true);onBusy(true);setError(null);setStatus(null);
    try {
      if(file.size>2_000_000)throw new ApiError('experiment_size');
      let raw:unknown;try{raw=JSON.parse(await file.text());}catch{throw new ApiError('experiment_document');}
      const validated=await post<{document:ExperimentDocument;graph:GraphData}>('experiments/validate',raw);
      setStatus(await onImport(validated.document,validated.graph)?'imported':'cancelled');
    } catch(reason){setError(reason);} finally{setWorking(false);onBusy(false);if(input.current)input.current.value='';}
  }
  async function save() {
    setWorking(true);onBusy(true);setError(null);setStatus(null);
    try {
      const document=exportDocument();
      await post('experiments/validate',document);
      const url=URL.createObjectURL(new Blob([JSON.stringify(document,null,2)],{type:'application/json'}));
      const anchor=window.document.createElement('a');anchor.href=url;anchor.download='sqw-experiment.json';anchor.click();
      window.setTimeout(()=>URL.revokeObjectURL(url),1000);setStatus('exported');
    }catch(reason){setError(reason);}finally{setWorking(false);onBusy(false);}
  }
  return <div className="experiment-files"><h3>{t('editor.files')}</h3>
    <button className="reset-button" disabled={busy||working||!canExport} onClick={()=>void save()}>{t('editor.export')}</button>
    <button className="reset-button" disabled={busy||working} onClick={()=>input.current?.click()}>{t('editor.import')}</button>
    <input ref={input} className="sr-only" type="file" accept=".json,application/json" aria-label={t('editor.importFile')} disabled={busy||working} onChange={e=>{const file=e.target.files?.[0];if(file)void load(file);}} />
    <p className="sidebar-hint">{t('editor.filesHelp')}</p>
    {error!==null&&<p role="alert" className="editor-warning">{formatError(error,t)}</p>}
    {status&&<p role="status" className="sidebar-hint">{t(`editor.${status}`)}</p>}
  </div>;
}
