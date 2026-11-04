import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { formatError, post } from './api';
import { formatNumber } from './i18n/format';
import type { Analysis, Ensemble, Frame, GraphData, Matrix, SimulationRequest, VertexParameters } from './types';

function complex([real, imaginary]: [number, number]) {
  const n = (v: number) => Number(v.toPrecision(5)).toString();
  return imaginary === 0 ? n(real) : `${n(real)} ${imaginary < 0 ? '−' : '+'} ${n(Math.abs(imaginary))}i`;
}

export function DensityTable({ matrix, labels, caption }: { matrix: Matrix; labels: string[]; caption: string }) {
  return <div className="research-table-scroll"><table className="research-table density-table"><caption>{caption}</caption>
    <thead><tr><th /><th colSpan={labels.length}>ρ</th></tr><tr><th /><>{labels.map((label) => <th key={label}>{label}</th>)}</></tr></thead>
    <tbody>{matrix.map((row, i) => <tr key={i}><th>{labels[i]}</th>{row.map((value, j) => <td key={j} title={`${value[0]} + (${value[1]})i`}>{complex(value)}</td>)}</tr>)}</tbody>
  </table></div>;
}

export function VertexControls({ graph, parameters = {}, busy, onApply }: { graph: GraphData; parameters?: VertexParameters; busy: boolean; onApply: (params: VertexParameters) => void }) {
  const { t } = useTranslation('research');
  const [omega, setOmega] = useState(() => JSON.stringify(parameters.omega ?? Object.fromEntries(graph.vertices.map((x) => [x, graph.neighbors[x].map(() => [1 / Math.sqrt(graph.neighbors[x].length), 0])])), null, 2));
  const [beta, setBeta] = useState(() => JSON.stringify(parameters.beta ?? Object.fromEntries(graph.vertices.map((x) => [x, 0])), null, 2));
  const [invalid, setInvalid] = useState(false);
  const [applied, setApplied] = useState(false);
  return <section className="panel research-panel"><details><summary>{t('vertex.parameters')}</summary>
    <p className="muted small">{t('vertex.parametersHelp')}</p><div className="research-columns">
      <label>{t('vertex.omega')}<textarea aria-label={t('vertex.omega')} value={omega} disabled={busy} spellCheck={false} onChange={(e) => { setOmega(e.target.value); setApplied(false); }} /></label>
      <label>{t('vertex.beta')}<textarea aria-label={t('vertex.beta')} value={beta} disabled={busy} spellCheck={false} onChange={(e) => { setBeta(e.target.value); setApplied(false); }} /></label>
    </div>
    <button className="secondary-button" disabled={busy} onClick={() => {
      try {
        const w: unknown = JSON.parse(omega), b: unknown = JSON.parse(beta);
        if (!w || !b || typeof w !== 'object' || typeof b !== 'object' || Array.isArray(w) || Array.isArray(b)) throw new Error();
        onApply({ omega: w as VertexParameters['omega'], beta: b as VertexParameters['beta'] }); setInvalid(false); setApplied(true);
      } catch { setInvalid(true); }
    }}>{t('vertex.apply')}</button>
    {invalid && <p role="alert">{t('vertex.jsonError')}</p>}{applied && <p role="status">{t('vertex.applied')}</p>}
  </details></section>;
}

export default function ResearchPanels({ graph, experiment, cursor, frame }: { graph: GraphData; experiment: SimulationRequest; cursor: number; frame: Frame }) {
  const { t, i18n } = useTranslation('research');
  const number = (v: number, digits = 4) => formatNumber(v, i18n.resolvedLanguage ?? 'en', digits);
  const vertex = experiment.mode === 'vertex';
  const [count, setCount] = useState(1000);
  const [ensemble, setEnsemble] = useState<Ensemble | null>(null);
  const [ensembleStep, setEnsembleStep] = useState(0);
  const [ensembleBusy, setEnsembleBusy] = useState(false);
  const [ensembleError, setEnsembleError] = useState<unknown>(null);
  const [atom, setAtom] = useState(0);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [analysisBusy, setAnalysisBusy] = useState(false);
  const [analysisError, setAnalysisError] = useState<unknown>(null);
  const ensembleRequest = useRef<AbortController | null>(null);
  const analysisRequest = useRef<AbortController | null>(null);
  // Only mathematical inputs invalidate results; translations never do.
  const configuration = JSON.stringify(experiment);
  useEffect(() => {
    ensembleRequest.current?.abort(); analysisRequest.current?.abort();
    setEnsemble(null); setAnalysis(null); setEnsembleBusy(false); setAnalysisBusy(false);
    setEnsembleError(null); setAnalysisError(null); setAtom(0);
    return () => { ensembleRequest.current?.abort(); analysisRequest.current?.abort(); };
  }, [configuration]);
  useEffect(() => { analysisRequest.current?.abort(); setAnalysis(null); setAnalysisBusy(false); setAnalysisError(null); }, [cursor]);
  const labels = vertex ? graph.vertices.map((x) => `|${x}⟩`) : graph.directed_edges.map(([x, y]) => `|${x},${y}⟩`);
  const atomLabels = vertex ? graph.vertices.map(String) : graph.directed_edges.map(([x, y]) => `(${x}, ${y})`);
  const snapshot = ensemble?.frames[ensembleStep];

  async function simulateEnsemble() {
    const controller = new AbortController(); ensembleRequest.current?.abort(); ensembleRequest.current = controller;
    setEnsembleBusy(true); setEnsembleError(null);
    try {
      const result = await post<Ensemble>('ensemble', { ...experiment, mode: vertex ? 'vertex' : 'trajectory',
        vertex_dynamics: 'trajectory', trajectories: count, selected_histories: Math.min(3, count) }, controller.signal);
      if (!controller.signal.aborted) { setEnsemble(result); setEnsembleStep(result.frames.length - 1); }
    } catch (error) { if (!controller.signal.aborted) setEnsembleError(error); }
    finally { if (ensembleRequest.current === controller) setEnsembleBusy(false); }
  }

  async function inspect() {
    const controller = new AbortController(); analysisRequest.current?.abort(); analysisRequest.current = controller;
    setAnalysisBusy(true); setAnalysisError(null);
    try {
      const result = await post<Analysis>('analysis', { ...experiment, steps: cursor, atom_id: atom }, controller.signal);
      if (!controller.signal.aborted) setAnalysis(result);
    } catch (error) { if (!controller.signal.aborted) setAnalysisError(error); }
    finally { if (analysisRequest.current === controller) setAnalysisBusy(false); }
  }

  return <>
    <section className="panel research-panel state-summary">
      <div className="eyebrow">{t('state.title')}</div><h2>{t(`stage.${frame.stage ?? 'initial'}`)} <span className="subtle">t = {frame.step}</span></h2>
      <p>{t(vertex ? 'state.vertexMeaning' : 'state.edgeMeaning')}</p>
      {frame.atom_id != null && <p><strong>{t('state.currentAtom')}: </strong>{vertex ? frame.atom_vertex : `(${frame.atom_edge?.join(', ')})`} · {vertex ? 'χ(Xₙ)' : 'ηₑ = U|e⟩'}</p>}
      {frame.measurement != null && <p>{t('state.outcome')}: <strong>Xₙ = {frame.measurement}</strong></p>}
      <p className="muted small">{t(vertex ? 'state.vertexTiming' : 'state.edgeTiming')}</p>
    </section>

    <section className="panel research-panel ensemble-panel">
      <div className="panel-header"><div><div className="eyebrow">{t('ensemble.eyebrow')}</div><h2>{t('ensemble.title')}</h2></div><span className="pill">{t(`strategy.${experiment.strategy ?? 'reference'}`)}</span></div>
      <p className="muted small">{t('ensemble.help')}</p>
      <div className="research-actions"><label htmlFor="trajectory-count">{t('ensemble.count')}</label><input id="trajectory-count" type="number" min="1" max="100000" value={count} disabled={ensembleBusy} onChange={(e) => { setCount(Math.max(1, Math.min(100000, Math.trunc(Number(e.target.value)) || 1))); setEnsemble(null); setEnsembleError(null); }} />
        <button className="secondary-button" disabled={ensembleBusy} onClick={() => void simulateEnsemble()}>{t(ensembleBusy ? 'ensemble.running' : 'ensemble.run')}</button>
        <span className="muted small">{t('ensemble.configuration', { steps: experiment.steps, seed: experiment.seed })}</span></div>
      {ensembleError !== null && <p role="alert" className="field-error">{formatError(ensembleError, t)}</p>}
      {ensemble && snapshot && <>
        <label className="research-slider" htmlFor="ensemble-step">{t('ensemble.step')} · t = {snapshot.step}<input id="ensemble-step" type="range" min="0" max={ensemble.frames.length - 1} value={ensembleStep} onChange={(e) => setEnsembleStep(Number(e.target.value))} /></label>
        <div className="research-statistics"><span>{t('ensemble.bornDeviation')}: <strong>{number(snapshot.born_vertex_total_variation ?? 0, 6)}</strong></span><span>{t('ensemble.labelDeviation')}: <strong>{snapshot.state_total_variation == null ? '—' : number(snapshot.state_total_variation, 6)}</strong></span></div>
        <div className="research-table-scroll"><table className="research-table probability-comparison"><caption>{t('ensemble.comparison')}</caption><thead><tr><th>{t('initial.vertex')}</th><th>{t('ensemble.empirical')}</th><th>{t('ensemble.exact')}</th><th>{t('ensemble.difference')}</th></tr></thead>
          <tbody>{graph.vertices.map((x, i) => <tr key={x}><th>{x}</th><td style={{ background: `linear-gradient(to right, #d9f0ec ${snapshot.empirical_born_vertices[i] * 100}%, transparent 0)` }}>{number(snapshot.empirical_born_vertices[i], 6)}</td><td>{number(snapshot.exact_born_vertices[i], 6)}</td><td>{number(snapshot.empirical_born_vertices[i] - snapshot.exact_born_vertices[i], 6)}</td></tr>)}</tbody></table></div>
        <details><summary>{t('ensemble.heatmap')}</summary><div className="research-table-scroll heatmap"><table className="research-table"><caption>{t('ensemble.heatmapCaption')}</caption><thead><tr><th>t</th>{graph.vertices.map((x) => <th key={x}>{x}</th>)}</tr></thead><tbody>{ensemble.frames.map((row) => <tr key={row.step}><th>{row.step}</th>{row.empirical_born_vertices.map((p, i) => <td key={i} style={{ backgroundColor: `rgba(21,150,142,${Math.sqrt(p) * .85})` }} title={t('ensemble.cell', { step: row.step, vertex: graph.vertices[i], probability: number(p, 6) })}>{number(p, 3)}</td>)}</tr>)}</tbody></table></div></details>
        <details><summary>{t('ensemble.stateCounts')}</summary><p className="muted small">{t(vertex ? 'ensemble.vertexLabels' : 'ensemble.edgeLabels')}</p>{snapshot.state_counts ? <div className="research-table-scroll"><table className="research-table"><thead><tr><th>{t('state.label')}</th><th>{t('ensemble.count')}</th><th>{t('ensemble.exactWeight')}</th></tr></thead><tbody>{snapshot.state_counts.map((n, i) => <tr key={i}><th>{atomLabels[i]}</th><td>{n}</td><td>{number(snapshot.exact_state_weights?.[i] ?? 0, 6)}</td></tr>)}</tbody></table></div> : <p>{t('ensemble.warmstart')}</p>}</details>
        <details><summary>{t('ensemble.histories')}</summary>{ensemble.selected_outcomes.map((path, i) => <p className="record-line" key={i}>{t('ensemble.path', { index: i + 1 })}: {path.join(' → ') || '—'}</p>)}</details>
      </>}
    </section>

    <section className="panel research-panel markov-panel"><div className="panel-header"><div><div className="eyebrow">{t('markov.eyebrow')}</div><h2>{t('markov.title')}</h2></div></div>
      <p className="muted small">{t(vertex ? 'markov.vertexConvention' : 'markov.edgeConvention')}</p>
      <div className="research-actions"><label htmlFor="atom-select">{t('state.label')}</label><select id="atom-select" value={atom} disabled={analysisBusy} onChange={(e) => { setAtom(Number(e.target.value)); setAnalysis(null); }}>{atomLabels.map((label, i) => <option value={i} key={i}>{label}</option>)}</select><button className="secondary-button" disabled={analysisBusy} onClick={() => void inspect()}>{t(analysisBusy ? 'markov.loading' : 'markov.inspect', { step: cursor })}</button></div>
      {analysisError !== null && <p role="alert" className="field-error">{formatError(analysisError, t)}</p>}
      {analysis && <>
        <p>{t('markov.eligible')} · {t(vertex ? 'markov.vertexAssumptions' : 'markov.edgeAssumptions')}</p>
        <div className="research-columns"><div><h3>{t('markov.ket')}</h3><p>{vertex ? `χ(${atomLabels[analysis.atom_id]})` : `η${atomLabels[analysis.atom_id]} = U|${atomLabels[analysis.atom_id]}⟩`}</p><div className="research-table-scroll"><table className="research-table"><thead><tr><th>{t('markov.basis')}</th><th>{t('markov.amplitude')}</th></tr></thead><tbody>{analysis.atom_ket.map((value, i) => <tr key={i}><th>{labels[i]}</th><td title={`${value[0]} + (${value[1]})i`}>{complex(value)}</td></tr>)}</tbody></table></div></div>
          <div><h3>{t('markov.transitions')}</h3><div className="research-table-scroll"><table className="research-table"><thead><tr><th>{t('state.label')}</th><th>{t('markov.probability')}</th></tr></thead><tbody>{analysis.next_atom_probabilities.map((p, i) => <tr key={i}><th>{atomLabels[i]}</th><td>{number(p, 6)}</td></tr>)}</tbody></table></div></div></div>
        <details><summary>{t('markov.matrix')}</summary><div className="research-table-scroll"><table className="research-table"><caption>{t(vertex ? 'markov.row' : 'markov.column')}</caption><thead><tr><th>{vertex ? 'P' : 'M'}</th>{atomLabels.map((label) => <th key={label}>{label}</th>)}</tr></thead><tbody>{analysis.transition_matrix.map((row, i) => <tr key={i}><th>{atomLabels[i]}</th>{row.map((p, j) => <td key={j} title={number(p, 10)}>{number(p, 3)}</td>)}</tr>)}</tbody></table></div></details>
        <details><summary>{t('state.currentDensity', { step: analysis.state_step })}</summary><DensityTable matrix={analysis.current_density} labels={labels} caption={t('state.afterScattering')} /></details>
        {analysis.after_measurement_density && <details><summary>{t('state.afterMeasurement')}</summary><DensityTable matrix={analysis.after_measurement_density} labels={labels} caption={t('state.beforeScattering')} /></details>}
      </>}
    </section>
  </>;
}
