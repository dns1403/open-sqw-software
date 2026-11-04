import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { post, formatError } from './api';
import LanguageSwitcher from './LanguageSwitcher';
import { formatNumber } from './i18n/format';
import GraphView from './GraphView';
import MatrixEditor, { presets } from './MatrixEditor';
import ProbabilityPlot from './ProbabilityPlot';
import ResearchPanels, { VertexControls } from './ResearchPanels';
import StationaryPanel from './StationaryPanel';
import StatisticsPanel from './StatisticsPanel';
import type { Frame, GraphData, GraphKind, Matrix, Mode, Preset, Simulation, SimulationRequest, Strategy, VertexParameters } from './types';

const graphKinds: GraphKind[] = ['path', 'cycle', 'complete', 'star'];
const modes: { key: Mode; symbol: string }[] = [
  { key: 'unitary', symbol: 'U' }, { key: 'open', symbol: 'Φ' }, { key: 'trajectory', symbol: 'ψ' }, { key: 'vertex', symbol: 'Ψ' },
];

export default function App() {
  const { t, i18n } = useTranslation('app');
  const language = i18n.resolvedLanguage ?? 'en';
  const number = (value: number, digits = 4) => formatNumber(value, language, digits);
  const [kind, setKind] = useState<GraphKind>('cycle');
  const [size, setSize] = useState(6);
  const [preset, setPreset] = useState<Preset>('dft');
  const [seed, setSeed] = useState(42);
  const [seedDraft, setSeedDraft] = useState('42');
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [selected, setSelected] = useState(0);
  const [mode, setMode] = useState<Mode>('unitary');
  const [initialKind, setInitialKind] = useState<'basis' | 'uniform' | 'maximally_mixed'>('basis');
  const [edgeIndex, setEdgeIndex] = useState(0);
  const [initialVertex, setInitialVertex] = useState(0);
  const [strategy, setStrategy] = useState<Strategy>('optimized');
  const [vertexDynamics, setVertexDynamics] = useState<'trajectory' | 'mean'>('trajectory');
  const [vertexParameters, setVertexParameters] = useState<VertexParameters>({});
  const [playing, setPlaying] = useState(false);
  const [steps, setSteps] = useState(12);
  const [simulation, setSimulation] = useState<Simulation | null>(null);
  const [cursor, setCursor] = useState(0);
  const [busy, setBusy] = useState(false);
  const [graphLoading, setGraphLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  const [retry, setRetry] = useState(0);
  const [distribution, setDistribution] = useState<'vertex' | 'edge'>('vertex');
  const request = useRef<AbortController | null>(null);
  const locked = busy || graphLoading;

  function reset() { setPlaying(false); request.current?.abort(); setBusy(false); setSimulation(null); setCursor(0); setError(null); }
  useEffect(() => {
    const controller = new AbortController();
    request.current?.abort(); request.current = controller;
    setPlaying(false); setVertexParameters({}); setInitialVertex(0);
    setGraphLoading(true); setBusy(false); setError(null); setSimulation(null); setCursor(0); setGraph(null);
    void post<GraphData>('graph', { kind, size, preset, seed }, controller.signal)
      .then((data) => { if (!controller.signal.aborted) { setGraph(data); setSelected(data.vertices[0]); setEdgeIndex(0); } })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setError(reason); })
      .finally(() => { if (!controller.signal.aborted) setGraphLoading(false); });
    return () => controller.abort();
  }, [kind, size, preset, seed, retry]);
  useEffect(() => () => request.current?.abort(), []);

  const initialFrame = useMemo<Frame | null>(() => {
    if (!graph) return null;
    const vertex = mode === 'vertex';
    const probabilities = vertex ? [] : graph.directed_edges.map((_, i) => initialKind !== 'basis' ? 1 / graph.dimension : Number(i === edgeIndex));
    const vertexProbabilities = vertex ? graph.vertices.map((x) => initialKind !== 'basis' ? 1 / graph.vertices.length : Number(x === initialVertex))
      : graph.vertices.map((x) => graph.directed_edges.reduce((sum, [target], i) => sum + (target === x ? probabilities[i] : 0), 0));
    return {
      step: 0, edge_probabilities: probabilities,
      vertex_probabilities: vertexProbabilities,
      purity: initialKind === 'maximally_mixed' ? 1 / (vertex ? graph.vertices.length : graph.dimension) : 1, trace: 1, measurement: null, measurement_probability: null, measurement_probabilities: null,
    };
  }, [graph, initialKind, edgeIndex, initialVertex, mode]);
  const frame = simulation?.frames[cursor] ?? initialFrame;
  const maxStep = simulation ? simulation.frames.length - 1 : 0;
  const currentNeighbors = graph?.neighbors[String(selected)] ?? [];

  function payload(count: number, scattering = graph!.scattering): SimulationRequest {
    return { graph: { kind, size }, scattering, preset, mode,
      initial: { kind: initialKind, edge: graph!.directed_edges[edgeIndex], vertex: initialVertex }, steps: count, seed,
      strategy, vertex_dynamics: vertexDynamics, vertex_parameters: vertexParameters };
  }
  async function run(count: number) {
    if (!graph || locked) return;
    const controller = new AbortController(); request.current?.abort(); request.current = controller;
    setBusy(true); setError(null);
    try {
      const result = await post<Simulation>('simulate', payload(count), controller.signal);
      if (!controller.signal.aborted) { setSimulation(result); setCursor(count); }
    } catch (reason) { if (!controller.signal.aborted) setError(reason); }
    finally { if (request.current === controller) setBusy(false); }
  }
  async function applyMatrix(matrix: Matrix): Promise<boolean> {
    if (!graph) return false;
    setBusy(true); setError(null);
    const controller = new AbortController(); request.current?.abort(); request.current = controller;
    try {
      const scattering = { ...graph.scattering, [selected]: matrix };
      await post<Simulation>('simulate', payload(0, scattering), controller.signal);
      if (controller.signal.aborted) return false;
      setPlaying(false); setGraph({ ...graph, scattering }); setSimulation(null); setCursor(0); return true;
    } catch (reason) { if (!controller.signal.aborted) setError(reason); return false; }
    finally { if (request.current === controller) setBusy(false); }
  }
  async function nodePreset(value: Preset) {
    if (!graph || locked) return;
    setBusy(true); setError(null);
    const controller = new AbortController(); request.current?.abort(); request.current = controller;
    try {
      const result = await post<{ matrix: Matrix }>('scattering', { preset: value, degree: currentNeighbors.length, seed }, controller.signal);
      if (!controller.signal.aborted) await applyMatrix(result.matrix);
    } catch (reason) { if (!controller.signal.aborted) { setError(reason); setBusy(false); } }
  }
  function changeMode(value: Mode) { setMode(value); if (value === 'vertex') setDistribution('vertex'); reset(); }
  function singleStep() { if (cursor < maxStep) setCursor(cursor + 1); else void run(cursor + 1); }

  useEffect(() => {
    if (!playing || locked || !graph) return;
    if (cursor >= steps) { setPlaying(false); return; }
    const timer = window.setTimeout(() => singleStep(), 600);
    return () => window.clearTimeout(timer);
  }, [playing, locked, cursor, maxStep, steps, graph, mode, strategy]);

  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><span /><span /><span /><span /></div><div>{t('brand.lineOne')}<span>{t('brand.lineTwo')}</span></div></div>
      <div className="sidebar-caption">{t('experiment.configure')}</div>
      <section className="sidebar-section">
        <h2><span>01</span> {t('graph.title')}</h2>
        <label htmlFor="graph-kind">{t('graph.topology')}</label>
        <select id="graph-kind" value={kind} disabled={locked} onChange={(event) => { const next = event.target.value as GraphKind; setKind(next); if (next !== 'cycle' && preset === 'hadamard') setPreset('dft'); if (next === 'cycle' && size < 3) setSize(3); }}>
          {graphKinds.map((key) => <option key={key} value={key}>{t(`graph.presets.${key}`)}</option>)}
        </select>
        <label htmlFor="graph-size">{t('graph.size')} <span className="input-note">{kind === 'star' ? t('graph.includesCenter') : t('graph.sizeRange', { min: kind === 'cycle' ? 3 : 2, max: 12 })}</span></label>
        <select id="graph-size" value={size} disabled={locked} onChange={(event) => setSize(Number(event.target.value))}>
          {Array.from({ length: kind === 'cycle' ? 10 : 11 }, (_, i) => i + (kind === 'cycle' ? 3 : 2)).map((n) => <option key={n} value={n}>{t('graph.vertices', { count: n })}</option>)}
        </select>
        <label htmlFor="global-preset">{t('graph.globalScattering')}</label>
        <select id="global-preset" value={preset} disabled={locked} onChange={(event) => setPreset(event.target.value as Preset)}>
          {presets.map((item) => <option key={item.value} value={item.value} disabled={item.value === 'hadamard' && kind !== 'cycle'}>{t(item.labelKey, { ns: 'components' })}</option>)}
        </select>
        <p className="sidebar-hint">{t('graph.matrixHint')}</p>
      </section>
      <section className="sidebar-section">
        <h2><span>02</span> {t('initial.title')}</h2>
        <label htmlFor="initial-kind">{t('initial.preparation')}</label>
        <select id="initial-kind" value={initialKind} disabled={locked} onChange={(event) => { setInitialKind(event.target.value as 'basis' | 'uniform' | 'maximally_mixed'); reset(); }}>
          <option value="basis">{t(mode === 'vertex' ? 'research:initial.vertexBasis' : 'initial.basis')}</option><option value="uniform">{t('initial.uniform')}</option><option value="maximally_mixed">{t('research:initial.mixed')}</option>
        </select>
        {mode === 'vertex' ? <><label htmlFor="initial-vertex">{t('research:initial.vertex')}</label><select id="initial-vertex" value={initialVertex} disabled={locked || initialKind !== 'basis'} onChange={(event) => { setInitialVertex(Number(event.target.value)); reset(); }}>{graph?.vertices.map((x) => <option key={x} value={x}>{x}</option>)}</select></> : <>
        <label htmlFor="initial-edge">{t('initial.directedEdge')}</label>
        <select id="initial-edge" value={edgeIndex} disabled={locked || !graph || initialKind !== 'basis'} onChange={(event) => { setEdgeIndex(Number(event.target.value)); reset(); }}>
          {graph?.directed_edges.map(([x, y], i) => <option key={`${x},${y}`} value={i}>|{x},{y}⟩ · {y} → {x}</option>)}
        </select>
        <p className="sidebar-hint">{t('initial.convention')}</p></>}
      </section>
      <section className="sidebar-section">
        <h2><span>03</span> {t('simulation.title')}</h2>
        {mode !== 'unitary' && <><label htmlFor="strategy">{t('research:strategy.label')}</label><select id="strategy" value={strategy} disabled={locked} onChange={(event) => { setStrategy(event.target.value as Strategy); reset(); }}><option value="optimized">{t('research:strategy.optimized')}</option><option value="reference">{t('research:strategy.reference')}</option></select></>}
        {mode === 'vertex' && <><label htmlFor="vertex-dynamics">{t('research:vertex.dynamics')}</label><select id="vertex-dynamics" value={vertexDynamics} disabled={locked} onChange={(event) => { setVertexDynamics(event.target.value as 'trajectory' | 'mean'); reset(); }}><option value="trajectory">{t('research:vertex.trajectory')}</option><option value="mean">{t('research:vertex.mean')}</option></select></>}
        <div className="input-pair"><div><label htmlFor="steps">{t('simulation.steps')}</label><input id="steps" type="number" min="1" max="200" step="1" value={steps} disabled={locked} onChange={(event) => setSteps(Math.max(1, Math.min(200, Math.trunc(Number(event.target.value)) || 1)))} /></div>
          <div><label htmlFor="seed">{t('simulation.seed')}</label><input id="seed" type="number" min="0" max="2147483647" value={seedDraft} disabled={locked} onChange={(event) => setSeedDraft(event.target.value)} onBlur={(event) => { if (event.relatedTarget instanceof Element && event.relatedTarget.closest('.language-switcher')) return; const next = Math.max(0, Math.min(2147483647, Math.floor(Number(seedDraft) || 0))); setSeedDraft(String(next)); setSeed(next); }} onKeyDown={(event) => { if (event.key === 'Enter') event.currentTarget.blur(); }} /></div></div>
        <button className="run-button" disabled={locked || !graph} onClick={() => void run(steps)}><span>{busy ? '◌' : '▶'}</span>{t(busy ? 'simulation.computing' : 'simulation.run')}</button>
        <button className="reset-button" disabled={locked || !graph} onClick={reset}>↺ {t('simulation.reset')}</button>
      </section>
      <div className="sidebar-footer"><span className="status-dot" /> {t('experiment.local')}<span>Joye · arXiv:2409.08428v2</span></div>
    </aside>

    <main className="workspace">
      <header className="page-header"><div><div className="eyebrow">{t('brand.research')} <span> / </span> {t('brand.edgeWalks')}</div><h1>{t('brand.title')}<span className="version">v0.1</span></h1><p>{t('brand.tagline')}</p></div>
        <div className="header-actions"><LanguageSwitcher /><a className="reference-link" href="https://arxiv.org/abs/2409.08428v2" target="_blank" rel="noreferrer">{t('brand.reference')} ↗</a></div></header>

      <div className="mode-bar" role="group" aria-label={t('modes.label')}>{modes.map((item) => <button key={item.key} className={mode === item.key ? 'mode active' : 'mode'} aria-pressed={mode === item.key} disabled={locked} onClick={() => changeMode(item.key)}><span>{item.symbol}</span>{t(`modes.${item.key}`)}</button>)}</div>

      {error !== null && <div className="error-banner" role="alert"><strong>{t('error.heading')}</strong><span>{formatError(error, t)}</span>{!graph && !graphLoading && <button className="text-button" onClick={() => setRetry(retry + 1)}>{t('error.retry')}</button>}</div>}

      <div className="metrics-row"><div className="metric"><span>{t('metrics.model')}</span><strong>{t(`modes.${mode}Full`)}</strong></div><div className="metric"><span>{t('metrics.hilbertSpace')}</span><strong>{graph ? `ℂ${superscript(mode === 'vertex' ? graph.vertices.length : graph.dimension)}` : '—'}<small>{graph ? t(mode === 'vertex' ? 'graph.vertices' : 'graph.directedEdges', { count: mode === 'vertex' ? graph.vertices.length : graph.dimension }) : t('graph.loading')}</small></strong></div><div className="metric"><span>{t('metrics.time')}</span><strong>t = {frame?.step ?? 0}<small>{maxStep > 0 ? t('metrics.ofSteps', { count: maxStep }) : t('initial.title')}</small></strong></div><div className="metric"><span>{t('metrics.purity')}</span><strong>{frame ? number(frame.purity) : '—'}<small>{t(frame && frame.purity > 1 - 1e-8 ? 'metrics.pure' : 'metrics.mixed')}</small></strong></div></div>

      <div className="research-grid">
        <section className="panel graph-panel"><div className="panel-header"><div><div className="eyebrow">{t('graph.space')}</div><h2>{t(`graph.presets.${kind}`)} <span className="subtle">/ {t('graph.vertices', { count: size })}</span></h2></div><span className="pill">{graph ? t('graph.edges', { count: graph.edges.length }) : t('graph.unknownEdges')}</span></div>
          {graph && frame ? <GraphView graph={graph} probabilities={frame.vertex_probabilities} selected={selected} onSelect={(vertex) => { if (!busy) setSelected(vertex); }} /> : <div className="graph-placeholder">{graphLoading ? <><span className="loading-orbit" />{t('graph.preparing')}</> : <>{t('graph.startBackend')}</>}</div>}
          <div className="graph-legend"><span><i className="legend-selected" /> {t('graph.selectedVertex')}</span><span><i className="legend-gradient" /> P(x) = 0 → 1</span><span className="legend-note">{t(mode === 'vertex' ? 'research:born.vertex' : 'graph.incomingMarginal')}</span></div>
        </section>

        <section className="panel inspector-panel"><div className="panel-header"><div><div className="eyebrow">{t('inspector.operator')}</div><h2>{t('inspector.matrix')} <span className="math">S(x)</span></h2></div></div>
          <div className="node-select"><label htmlFor="selected-node">{t('inspector.vertex')}</label><select id="selected-node" value={selected} disabled={locked || !graph} onChange={(event) => setSelected(Number(event.target.value))}>{graph?.vertices.map((vertex) => <option key={vertex} value={vertex}>{vertex}</option>)}</select><span>{t('inspector.degree', { degree: currentNeighbors.length || '—' })}</span></div>
          {graph ? <MatrixEditor vertex={selected} neighbors={currentNeighbors} matrix={graph.scattering[String(selected)]} busy={locked} onApply={applyMatrix} onPreset={(value) => void nodePreset(value)} /> : <p className="muted">{t('inspector.empty')}</p>}
          <div className="operator-formula">U<sub>S</sub> |xy⟩ = ∑<sub>z∼x</sub> S<sub>zy</sub>(x) |zx⟩</div>
        </section>

        <section className="panel distribution-panel"><div className="panel-header"><div><div className="eyebrow">{t('distribution.observable')}</div><h2>{t('distribution.title')}</h2></div><div className="segmented"><button className={distribution === 'vertex' ? 'active' : ''} onClick={() => setDistribution('vertex')} aria-pressed={distribution === 'vertex'}>{t('distribution.vertices')}</button><button className={distribution === 'edge' ? 'active' : ''} disabled={mode === 'vertex'} onClick={() => setDistribution('edge')} aria-pressed={distribution === 'edge'}>{t('distribution.edges')}</button></div></div>
          {graph && frame ? <ProbabilityPlot labels={distribution === 'vertex' ? graph.vertices.map((x) => t('distribution.vertexLabel', { vertex: x })) : graph.directed_edges.map(([x, y]) => t('distribution.edgeLabel', { source: y, target: x }))} probabilities={distribution === 'vertex' ? frame.vertex_probabilities : frame.edge_probabilities} selected={distribution === 'vertex' ? graph.vertices.indexOf(selected) : undefined} /> : <div className="chart-placeholder">{t('distribution.empty')}</div>}
          <div className="distribution-footer"><span>{distribution === 'vertex' ? (mode === 'vertex' ? 'Pₜ(x) = ⟨x|ρₜ|x⟩' : 'Pₜ(x) = ∑ᵧ∼ₓ ⟨xy|ρₜ|xy⟩') : 'Pₜ(xy) = ⟨xy|ρₜ|xy⟩'}</span><span>Σ P = {frame ? number((mode === 'vertex' ? frame.vertex_probabilities : frame.edge_probabilities).reduce((sum, p) => sum + p, 0), 6) : '—'}</span></div>
        </section>

        <section className="panel time-panel"><div className="panel-header"><div><div className="eyebrow">{t('dynamics.label')}</div><h2>{t('dynamics.title')}</h2></div><span className="pill">{simulation ? t('dynamics.states', { count: maxStep + 1 }) : 't = 0'}</span></div>
          {simulation && graph ? <ProbabilityPlot labels={graph.vertices.map((x) => t('distribution.vertexLabel', { vertex: x }))} probabilities={frame?.vertex_probabilities ?? []} history={simulation.frames.map((item) => ({ step: item.step, probabilities: item.vertex_probabilities }))} /> : <div className="timeline-empty"><div className="wave-symbol">∿</div><strong>{t('dynamics.emptyTitle')}</strong><p>{t('dynamics.emptyRun')}<br />{t('dynamics.emptyHistory')}</p></div>}
        </section>
      </div>

      <section className="playback-bar" aria-label={t('simulation.controls')}><div className="playback-buttons"><button title={t('simulation.previous')} aria-label={t('simulation.previous')} disabled={locked || cursor === 0} onClick={() => { setPlaying(false); setCursor(cursor - 1); }}>←</button><button disabled={!graph || graphLoading || (!playing && cursor >= steps)} onClick={() => setPlaying(!playing)} aria-pressed={playing}>{t(playing ? 'research:playback.pause' : 'research:playback.play')}</button><button className="step-button" disabled={locked || !graph || cursor >= 200} onClick={singleStep}>{t('simulation.step')} <span>→</span></button></div><div className="scrubber"><label htmlFor="time-slider">{t('simulation.timeline')} <strong>t = {frame?.step ?? 0}</strong></label><input id="time-slider" type="range" min="0" max={Math.max(1, maxStep)} value={cursor} disabled={locked || maxStep === 0} onChange={(event) => { setPlaying(false); setCursor(Number(event.target.value)); }} /></div><span className="playback-end">{t('simulation.stepCount', { count: maxStep })}</span></section>

      {(mode === 'trajectory' || (mode === 'vertex' && vertexDynamics === 'trajectory')) && <section className="panel trajectory-panel"><div className="panel-header"><div><div className="eyebrow">{t('trajectory.log')}</div><h2>{t('trajectory.title')}</h2></div><span className="pill">{t('simulation.seed')} {seed}</span></div><p className="muted small">{t(mode === 'vertex' ? 'research:vertex.timing' : 'trajectory.timing')}</p>
        {simulation && cursor > 0 ? <><div className="outcome-list">{simulation.frames.slice(1, cursor + 1).map((item) => <button key={item.step} className={item.step === cursor ? 'outcome active' : 'outcome'} onClick={() => setCursor(item.step)} title={t('trajectory.conditionalProbability', { probability: item.measurement_probability === null ? '—' : number(item.measurement_probability, 6) })}><small>n = {item.step}</small><strong>x = {item.measurement}</strong><span>p = {item.measurement_probability === null ? '—' : number(item.measurement_probability, 3)}</span></button>)}</div><p className="small muted">{t('trajectory.probabilities')} {frame?.measurement_probabilities?.map((p, i) => `x=${graph?.vertices[i]}: ${number(p)}`).join(' · ')}</p></> : <p className="muted">{t('trajectory.empty')}</p>}
      </section>}
      {mode === 'vertex' && graph && <VertexControls key={`${kind}/${size}`} graph={graph} parameters={vertexParameters} busy={locked} onApply={(params) => { setVertexParameters(params); reset(); }} />}
      {(mode === 'trajectory' || mode === 'vertex' || mode === 'open') && graph && frame && <ResearchPanels
        graph={graph} experiment={payload(steps)} cursor={cursor} frame={frame} />}
      {mode !== 'unitary' && graph && <><nav className="research-navigation" aria-label={t('statistics:navigation')}><a href="#trajectory-statistics">{t('statistics:title')} ↓</a></nav><StationaryPanel experiment={payload(steps)} /><StatisticsPanel experiment={payload(steps)} graph={graph} /></>}
      <footer className="workspace-footer"><span>|xy⟩ ≡ y → x <span>·</span> {t('footer.graphClass')}</span><span>{t('footer.distinction')}</span></footer>
    </main>
  </div>;
}

function superscript(value: number) { return String(value).split('').map((digit) => '⁰¹²³⁴⁵⁶⁷⁸⁹'[Number(digit)]).join(''); }
