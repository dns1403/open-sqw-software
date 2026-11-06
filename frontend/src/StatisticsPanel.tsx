import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { formatError, post } from './api';
import { formatNumber } from './i18n/format';
import { atomLabel } from './ReducedMarkovGraph';
import StatisticsPlot from './StatisticsPlot';
import type { GraphData, SimulationRequest } from './types';
import type { ObservableKind, StatisticsResult } from './statisticsTypes';

const kinds: ObservableKind[] = ['label_indicator','outcome_indicator','vertex_probability','coherence_real','coherence_imag'];
export default function StatisticsPanel({ experiment, graph }: { experiment: SimulationRequest; graph: GraphData }) {
  const { t,i18n } = useTranslation('statistics');
  const language = i18n.resolvedLanguage ?? 'en';
  const number = (v:number) => v!==0 && Math.abs(v)<1e-6 ? scientific(v) : formatNumber(v,language,6);
  const scientific = (v:number) => new Intl.NumberFormat(language,{notation:'scientific',maximumFractionDigits:3}).format(v);
  const [kind,setKind] = useState<ObservableKind>('label_indicator');
  const [index,setIndex] = useState(0), [second,setSecond] = useState(1), [vertex,setVertex] = useState(graph.vertices[0]);
  const [samples,setSamples] = useState('2000'), [burn,setBurn] = useState('0'), [seed,setSeed] = useState('42');
  const [confidence,setConfidence] = useState(.95), [start,setStart] = useState('experiment');
  const [selected,setSelected] = useState(0), [classIds,setClassIds] = useState<number[]>([]);
  const [result,setResult] = useState<StatisticsResult | null>(null);
  const [busy,setBusy] = useState(false), [error,setError] = useState<unknown>(null);
  const pending = useRef<AbortController | null>(null);
  const configuration = JSON.stringify(experiment);
  useEffect(() => {
    pending.current?.abort(); setBusy(false); setResult(null); setError(null); setSelected(0); setClassIds([]);
    setIndex(0); setSecond(1); setVertex(graph.vertices[0]);
    return () => pending.current?.abort();
  },[configuration]); // Language changes do not alter experiment identity.
  const labels = (experiment.mode==='vertex' ? graph.vertices : graph.directed_edges).map(atomLabel);
  const coherence = kind.startsWith('coherence');
  const bounded = (v:string,min:number,max:number) => v.trim()!=='' && Number.isInteger(Number(v)) && Number(v)>=min && Number(v)<=max;
  const valid = bounded(samples,1,100000) && bounded(burn,0,10000) && bounded(seed,0,2**32-1) && (!coherence || (index!==second && labels.length<=64));
  const invalidate = () => { setResult(null); setError(null); };
  async function run() {
    pending.current?.abort(); const controller=new AbortController(); pending.current=controller;
    setBusy(true); setError(null);
    try {
      const data = await post<StatisticsResult>('statistics',{...experiment,observable:{kind,index,second,vertex},
        samples:Number(samples),burn_in:Number(burn),trajectory_seed:Number(seed),confidence,
        initialization:start,stationary_class:selected},controller.signal);
      if (!controller.signal.aborted) { setResult(data); setClassIds(data.analysis.classes.map(c => c.class_id)); }
    } catch (reason) { if (!controller.signal.aborted) setError(reason); }
    finally { if (pending.current===controller) setBusy(false); }
  }
  const c = result?.analysis.classes[selected], p = c?.poisson, u = result?.uncertainty[selected], path = result?.trajectory;
  const scalar = (label:string,value:number) => <div><dt>{t(label)}</dt><dd>{number(value)}</dd></div>;
  return <section id="trajectory-statistics" className="panel research-panel statistics-panel" aria-labelledby="statistics-title">
    <div className="eyebrow">{t('eyebrow')}</div><h2 id="statistics-title">{t('title')}</h2><p className="muted small">{t('intro')}</p>
    <div className="statistics-controls" data-tour="statistics">
      <label>{t('observable')}<select value={kind} disabled={busy} onChange={e => { setKind(e.target.value as ObservableKind); invalidate(); }}>{kinds.map(k => <option key={k} value={k}>{t(`presets.${k}`)}</option>)}</select></label>
      {(kind==='label_indicator' || coherence) && <label>{t(coherence?'basisIndex':'atom')}<select value={index} disabled={busy} onChange={e => { setIndex(Number(e.target.value)); invalidate(); }}>{labels.map((label,i)=><option key={i} value={i}>{label}</option>)}</select></label>}
      {coherence && <label>{t('secondIndex')}<select value={second} disabled={busy} onChange={e => { setSecond(Number(e.target.value)); invalidate(); }}>{labels.map((label,i)=><option key={i} value={i}>{label}</option>)}</select></label>}
      {(kind==='outcome_indicator' || kind==='vertex_probability') && <label>{t('vertex')}<select value={vertex} disabled={busy} onChange={e => { setVertex(Number(e.target.value)); invalidate(); }}>{graph.vertices.map(v=><option key={v} value={v}>{v}</option>)}</select></label>}
      <label>{t('samples')}<input type="number" min="1" max="100000" value={samples} disabled={busy} onChange={e => {setSamples(e.target.value);invalidate();}} /></label>
      <label>{t('burn')}<input type="number" min="0" max="10000" value={burn} disabled={busy} onChange={e => {setBurn(e.target.value);invalidate();}} /></label>
      <label>{t('seed')}<input type="number" min="0" max={2**32-1} value={seed} disabled={busy} onChange={e => {setSeed(e.target.value);invalidate();}} /></label>
      <label>{t('confidence')}<select value={confidence} disabled={busy} onChange={e => {setConfidence(Number(e.target.value));invalidate();}}>{[.9,.95,.99].map(v=><option key={v} value={v}>{v*100}%</option>)}</select></label>
      <label>{t('start')}<select value={start} disabled={busy} onChange={e => {setStart(e.target.value);invalidate();}}><option value="experiment">{t('experimentStart')}</option><option value="stationary_class">{t('stationaryStart')}</option></select></label>
      {classIds.length>0 && <label>{t('selectedClass')}<select value={selected} disabled={busy} onChange={e => setSelected(Number(e.target.value))}>{classIds.map((id,i)=><option key={id} value={i}>{t('class',{id:id+1})}</option>)}</select></label>}
    </div>
    <p className="muted small">{t(`semantics.${kind}`)}</p><p className="muted small">{t(start==='experiment'?'warmup':'stationaryHelp')}</p>
    <button className="secondary-button" disabled={busy || !valid} onClick={()=>void run()}>{t(busy?'running':'run')}</button>
    {!valid && <p className="field-error" role="alert">{t('invalid')}</p>}
    {error!==null && <p className="field-error" role="alert">{formatError(error,t)}</p>}
    {result && c && p && u && path && <>
      <div className="stationary-badges"><span className="pill">{t(result.irreducible?'irreducible':'reducible')}</span><span className="pill">{t('period',{period:p.period})}</span><span className="pill">{t('class',{id:c.class_id+1})}</span></div>
      <div className="stationary-interpretation"><p>{t(result.analysis.global_clt_available?'singleClass':'conditional')}</p><p>{t('periodic')}</p></div>
      <p className="muted small">{t('transient',{mass:number(result.analysis.initial_transient_mass)})}</p>
      <h3>{t('summary')}</h3><dl className="statistics-summary">{scalar('mean',p.mean)}{scalar('variance',p.asymptotic_variance)}{scalar('std',p.asymptotic_std)}{scalar('se',u.standard_error)}{scalar('iidVariance',p.instantaneous_variance)}{scalar('iidSe',u.iid_comparison_standard_error)}</dl>
      <p className="muted small">{t('correlationHelp')}</p>
      {p.degenerate && <p className="support-notice">{t('degenerate')}</p>}
      {p.stability_warning && <p className="support-notice">{t('unstable')}</p>}
      <div className="research-table-scroll"><table className="research-table"><caption>{t('classTable')}</caption><thead><tr><th>{t('classLabel')}</th><th>{t('states')}</th><th>aⱼ</th><th>μⱼ</th><th>σⱼ²</th><th>{t('periodLabel')}</th></tr></thead><tbody>{result.analysis.classes.map(item=><tr key={item.index}><th>{t('class',{id:item.class_id+1})}</th><td>{item.states.map(i=>atomLabel(result.atom_labels[i])).join(', ')}</td><td>{number(item.absorption_probability)}</td><td>{number(item.poisson.mean)}</td><td>{number(item.poisson.asymptotic_variance)}</td><td>{item.poisson.period}</td></tr>)}</tbody></table></div>
      <h3>{t('chart')}</h3><p className="muted small">{t('timing',{start:result.start_step,first:path.first_step,last:path.last_step,n:path.samples,seed:path.seed})}</p>
      {path.stationary_start_requested && <p className="muted small">{t('preparedClass',{id:(result.analysis.classes[path.requested_class!]?.class_id??0)+1})}</p>}
      <p>{t('empirical')}: <strong>{number(path.empirical_mean)}</strong> · {t('reference')}: <strong>{number(p.mean)}</strong></p>
      {path.entered_class!==selected && <p className="support-notice">{t('differentClass')}</p>}
      {(path.support_sensitive || path.support_escape) && <p className="support-notice">{t('supportWarning')}</p>}
      <StatisticsPlot result={result} selected={selected} />
      <p className="muted small">{t('bandHelp',{confidence:Math.round(path.confidence*100)})}</p>
      {path.confidence_interval && selected===path.entered_class && <p>{t('interval')}: [{path.confidence_interval.map(number).join('; ')}]</p>}
      <details><summary>{t('values')}</summary><div className="research-table-scroll"><table className="research-table"><thead><tr><th>{t('atom')}</th><th>f</th><th>{t('empiricalWeight')}</th></tr></thead><tbody>{result.observable.values.map((value,i)=><tr key={i}><th>{atomLabel(result.atom_labels[i])}</th><td>{number(value)}</td><td>{number(path.empirical_law[i])}</td></tr>)}</tbody></table></div></details>
      <details><summary>{t('diagnostics')}</summary><p>{t('poissonResidual')}: {scientific(p.relative_residual)} · {t('centeringResidual')}: {scientific(p.centering_residual)} · {t('stationaryResidual')}: {scientific(p.stationary_residual)}</p><p>{t('condition')}: {p.condition_number===null?'—':scientific(p.condition_number)} · {t('pivot')}: {scientific(p.min_scaled_pivot)}</p><p>{t('support',{cutoff:scientific(result.support.tolerance),count:result.support.discarded_entries,change:scientific(result.support.matrix_change_max_row_l1)})}</p><p>{t(result.support.source==='numerical'?'numericalSupport':'analyticSupport')}</p></details>
    </>}
  </section>;
}
