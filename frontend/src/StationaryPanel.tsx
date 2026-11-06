import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { formatError, post } from './api';
import { formatNumber } from './i18n/format';
import ReducedMarkovGraph, { atomLabel, classColor } from './ReducedMarkovGraph';
import StationaryPlot from './StationaryPlot';
import { DensityTable } from './ResearchPanels';
import type { SimulationRequest, StationaryResult } from './types';

export default function StationaryPanel({ experiment }: { experiment: SimulationRequest }) {
  const { t, i18n } = useTranslation('stationary');
  const language = i18n.resolvedLanguage ?? 'en';
  const number = (v: number, digits = 6) => formatNumber(v, language, digits);
  const scientific = (v: number) => new Intl.NumberFormat(language, { notation: 'scientific', maximumFractionDigits: 3 }).format(v);
  const [steps, setSteps] = useState(200);
  const [tolerance, setTolerance] = useState('1e-14');
  const [result, setResult] = useState<StationaryResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [selected, setSelected] = useState(0);
  const [stationaryClass, setStationaryClass] = useState(-1);
  const [cursor, setCursor] = useState(0);
  const pending = useRef<AbortController | null>(null);
  const configuration = JSON.stringify(experiment);
  useEffect(() => {
    pending.current?.abort(); setResult(null); setBusy(false); setError(null); setSelected(0); setStationaryClass(-1); setCursor(0);
    return () => pending.current?.abort();
  }, [configuration]);
  async function analyze(includeDensity = false) {
    const controller = new AbortController(); pending.current?.abort(); pending.current = controller;
    setBusy(true); setError(null);
    try {
      const data = await post<StationaryResult>('stationary', { ...experiment, analysis_steps: steps,
        support_atol: Number(tolerance), include_density: includeDensity,
        stationary_class: stationaryClass < 0 ? null : stationaryClass }, controller.signal);
      if (!controller.signal.aborted) { setResult(data); if (!includeDensity) setCursor(data.frames.length-1); }
    } catch (reason) { if (!controller.signal.aborted) setError(reason); }
    finally { if (pending.current === controller) setBusy(false); }
  }
  const labels = result?.atom_labels.map(atomLabel) ?? [];
  const weights = result ? (stationaryClass < 0 ? result.stationary_mixture : result.stationary_family[stationaryClass]) : [];
  const frame = result?.frames[cursor];
  const quantum = result?.quantum && result.quantum.class_index === (stationaryClass < 0 ? null : stationaryClass) ? result.quantum : null;
  const validTolerance = tolerance.trim() !== '' && Number.isFinite(Number(tolerance)) && Number(tolerance) >= 0 && Number(tolerance) <= 1e-6;
  return <section className="panel research-panel stationary-panel">
    <div className="eyebrow">{t('eyebrow')}</div><h2>{t('title')}</h2><p className="muted small">{t('intro')}</p>
    <div className="stationary-controls" data-tour="stationary-run"><label>{t('steps')}<input type="number" min="0" max="5000" value={steps} disabled={busy} onChange={(e) => { setSteps(Math.min(5000,Math.max(0,Math.trunc(Number(e.target.value))||0))); setResult(null); }} /></label>
      <label>{t('tolerance')}<input type="number" min="0" max="0.000001" step="any" value={tolerance} disabled={busy} onChange={(e) => { setTolerance(e.target.value); setResult(null); }} /></label>
      <button className="secondary-button" disabled={busy || !validTolerance} onClick={() => void analyze()}>{t(busy ? 'analyzing' : 'analyze')}</button></div>
    {!validTolerance && <p role="alert" className="field-error">{t('errors:stationary_tolerance')}</p>}
    {error !== null && <p role="alert" className="field-error">{formatError(error,t)}</p>}
    {result && frame && <>
      <p className="muted small">{t('timing',{start:result.start_step,steps:result.analysis_steps})}</p>
      <div className="stationary-badges"><span className="pill">{t(result.irreducible ? 'irreducible' : 'reducible')}</span><span className="pill">{t(result.unique_stationary ? 'unique' : 'nonunique')}</span><span className="pill">{t(result.bistochastic ? 'bistochastic' : 'rowStochastic')}</span></div>
      <div className="stationary-interpretation"><p>{t(result.ordinary_guaranteed ? 'ordinary' : 'periodic',{periods:[...new Set(result.reachable_periods)].join(', ')})}</p>
        {!result.unique_stationary && <p>{t('multiple',{count:result.closed_class_ids.length})}</p>}
        {result.transient_states.length > 0 && <p>{t('transientHelp')}</p>}</div>
      <p className="muted small">{t(result.model==='edge' ? 'edgeInterpretation' : 'vertexInterpretation')}</p>
      <p className={result.support.source==='numerical' ? 'support-notice' : 'muted small'}>{t(result.support.source==='numerical' ? 'numericalSupport' : 'analyticSupport',{tolerance:scientific(result.support.tolerance)})}</p>
      <details><summary>{t('diagnostics')}</summary><p>{t('supportDetails',{count:result.support.discarded_entries,mass:scientific(result.support.discarded_max_row_mass),change:scientific(result.support.matrix_change_max_row_l1)})}</p>
        <p>{t('rowResidual')}: {scientific(result.diagnostics.row_residual)} · {t('columnResidual')}: {scientific(result.diagnostics.column_residual)} · {t('absorptionResidual')}: {scientific(result.diagnostics.absorption_raw_residual)}</p></details>

      <h3>{t('classes')}</h3><div className="research-table-scroll" data-tour="classes"><table className="research-table"><thead><tr><th>{t('classes')}</th><th>{t('states')}</th><th>{t('recurrent')} / {t('transient')}</th><th>{t('period')}</th><th>{t('cyclic')}</th></tr></thead>
        <tbody>{result.classes.map((c) => <tr key={c.id}><th><span className="class-swatch" style={{background:classColor(c.id)}} />{t('class',{id:c.id+1})}</th><td>{c.states.map((id) => labels[id]).join(', ')}</td><td>{t(c.closed?'recurrent':'transient')}</td><td>{c.period ?? t('noCycle')}</td><td>{c.cyclic_subclasses.map((group) => `{${group.map((id) => labels[id]).join(', ')}}`).join(' → ') || '—'}</td></tr>)}</tbody></table></div>

      <h3>{t('stationaryTitle')}</h3><label className="stationary-select">{t('distribution')}<select value={stationaryClass} disabled={busy} onChange={(e) => setStationaryClass(Number(e.target.value))}><option value={-1}>{t('mixture')}</option>{result.closed_class_ids.map((id,index) => <option key={id} value={index}>{t('class',{id:id+1})}</option>)}</select></label>
      <div className="research-table-scroll"><table className="research-table"><thead><tr><th>{t('classes')}</th><th>{t('classWeight')}</th><th>{t('stationarityResidual')}</th></tr></thead><tbody>{result.closed_class_ids.map((id,i) => <tr key={id}><th>{t('class',{id:id+1})}</th><td>{number(result.class_weights[i])}</td><td>{scientific(result.classes[id].raw_residual ?? 0)}</td></tr>)}</tbody></table></div>
      <h3>{t('graphTitle')}</h3><p className="muted small">{t(result.model==='edge'?'graphEdgeHelp':'graphVertexHelp')}</p>
      <label className="stationary-select">{t('selectedState')}<select value={selected} onChange={(e) => setSelected(Number(e.target.value))}>{labels.map((label,i) => <option key={i} value={i}>{label} · {t('class',{id:result.membership[i]+1})}</option>)}</select></label>
      <ReducedMarkovGraph result={result} weights={weights} selected={selected} onSelect={setSelected} />
      <div className="research-columns"><div><h3>{t('weight')}</h3><div className="research-table-scroll"><table className="research-table probability-comparison"><thead><tr><th>{t('label')}</th><th>{t('weight')}</th></tr></thead><tbody>{weights.map((p,i) => <tr key={i}><th>{labels[i]}</th><td style={{background:`linear-gradient(to right, #d9f0ec ${p*100}%, transparent 0)`}}>{number(p)}</td></tr>)}</tbody></table></div></div>
        <div><h3>{t('transitionTitle')} · {labels[selected]}</h3><div className="research-table-scroll"><table className="research-table"><thead><tr><th>{t('destination')}</th><th>{t('probability')}</th><th>{t('retained')}</th></tr></thead><tbody>{result.transitions.filter((e) => e.source===selected).map((e) => <tr key={e.target}><th>{labels[e.target]}</th><td title={String(e.probability)}>{e.probability < 1e-6 ? scientific(e.probability) : number(e.probability)}</td><td>{t(e.analysis_probability > 0 ? 'yes':'no')}</td></tr>)}</tbody></table></div></div></div>
      <details><summary>{t('absorption')}</summary><div className="research-table-scroll"><table className="research-table"><thead><tr><th>{t('label')}</th>{result.closed_class_ids.map((id) => <th key={id}>{t('class',{id:id+1})}</th>)}</tr></thead><tbody>{result.absorption.map((row,i) => <tr key={i}><th>{labels[i]}</th>{row.map((p,j) => <td key={j}>{number(p)}</td>)}</tr>)}</tbody></table></div></details>
      <details><summary>{t('matrix')}</summary><p>{t(result.orientation==='column'?'columnConvention':'rowConvention')}</p>{result.transition_matrix ? <div className="research-table-scroll"><table className="research-table"><thead><tr><th>{result.orientation==='column'?'M':'P'}</th>{labels.map((label) => <th key={label}>{label}</th>)}</tr></thead><tbody>{result.transition_matrix.map((row,i) => <tr key={i}><th>{labels[i]}</th>{row.map((p,j) => <td key={j} title={String(p)}>{number(p,3)}</td>)}</tr>)}</tbody></table></div> : <p>{t('sparseMatrix')}</p>}</details>

      <h3>{t('evolutionTitle')}</h3><p className="muted small">{t('referenceHelp')}</p>
      <div className="stationary-charts" data-tour="cesaro"><StationaryPlot result={result} selected={selected} /><StationaryPlot result={result} selected={selected} distance /></div>
      <label className="research-slider">{t('time')} · t = {frame.step}<input type="range" min="0" max={result.frames.length-1} value={cursor} onChange={(e) => setCursor(Number(e.target.value))} /></label>
      <p>{t('ordinaryTrace')} ({labels[selected]}): <strong>{number(frame.probabilities[selected])}</strong> · {t('cesaroTrace')}: <strong>{number(frame.cesaro[selected])}</strong> · {t('stationaryTrace')}: <strong>{number(result.stationary_mixture[selected])}</strong></p>
      <p>{t('ordinaryDistance')}: <strong>{number(frame.total_variation)}</strong> · {t('cesaroDistance')}: <strong>{number(frame.cesaro_total_variation)}</strong></p>

      <h3>{t('quantumTitle')}</h3><p className="muted small">{t('quantumHelp')}</p><button className="secondary-button" disabled={busy || labels.length>64} onClick={() => void analyze(true)}>{t('reconstruct')}</button>
      {quantum && <><p>{t('trace')}: {number(quantum.trace)} · {t('purity')}: {number(quantum.purity)} · {t('channelResidual')}: {scientific(quantum.channel_residual)}</p><DensityTable matrix={quantum.density} labels={labels.map((label)=>`|${label}⟩`)} caption={t('densityCaption')} /></>}
    </>}
  </section>;
}
