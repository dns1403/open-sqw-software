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
import CustomGraphTools, { VertexName } from './CustomGraphTools';
import InitialStateInput from './InitialStateInput';
import ExperimentFiles from './ExperimentFiles';
import ConfirmationDialog, { useConfirmation } from './ConfirmationDialog';
import { addEdge,addVertex,basisKey,customCopy,customSpec,draftGraph,emptyCustomGraph,fromDocument,graphProblems,initialReady,matrixProblem,moveVertex,parameterProblems,removeEdge,removeVertex,renameVertex,setMatrix,toDocument } from './customGraph';
import type { BoundInitial,CustomGraphDraft,EditMode,ExperimentDocument } from './customGraph';
import { ApiError } from './api';
import type { Frame, GraphData, GraphKind, InitialStateSpec, Matrix, Mode, Preset, Simulation, SimulationRequest, Strategy, VertexParameters } from './types';

const graphKinds: GraphKind[] = ['path', 'cycle', 'complete', 'star', 'custom'];
const emptyMatrix:Matrix=[];
const modes: { key: Mode; symbol: string }[] = [
  { key: 'unitary', symbol: 'U' }, { key: 'open', symbol: 'Φ' }, { key: 'trajectory', symbol: 'ψ' }, { key: 'vertex', symbol: 'Ψ' },
];

export default function App() {
  const { t, i18n } = useTranslation('app');
  const {confirm,confirmation,finish}=useConfirmation();
  const language = i18n.resolvedLanguage ?? 'en';
  const number = (value: number, digits = 4) => formatNumber(value, language, digits);
  const [kind, setKind] = useState<GraphKind>('cycle');
  const [size, setSize] = useState(6);
  const [preset, setPreset] = useState<Preset>('dft');
  const [seed, setSeed] = useState(42);
  const [seedDraft, setSeedDraft] = useState('42');
  const [presetGraph, setPresetGraph] = useState<GraphData | null>(null);
  const [custom,setCustom]=useState<CustomGraphDraft>(emptyCustomGraph);
  const customGraph=useMemo(()=>draftGraph(custom),[custom.vertices,custom.edges,custom.matrices]);
  const graph=kind==='custom'?customGraph:presetGraph;
  const [editMode,setEditMode]=useState<EditMode>('select');
  const [selectedEdge,setSelectedEdge]=useState<[number,number]|null>(null);
  const [edgeStart,setEdgeStart]=useState<number|null>(null);
  const [editorError,setEditorError]=useState<string|null>(null);
  const [presetTags,setPresetTags]=useState<Record<string,Preset|null>>({});
  const [fileBusy,setFileBusy]=useState(false);
  const [importRevision,setImportRevision]=useState(0);
  const [vertexDrafts,setVertexDrafts]=useState<Record<string,{omega:string;beta:string}>>({});
  const [presetDrafts,setPresetDrafts]=useState<Record<string,string>>({});
  const [selected, setSelected] = useState(0);
  const [mode, setMode] = useState<Mode>('unitary');
  const [presetInitial,setPresetInitial]=useState<BoundInitial>({state:{kind:'basis',edge:[0,1],vertex:0},basis:''});
  const [initialDrafts,setInitialDrafts]=useState<Record<string,string>>({});
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
  const locked = busy || graphLoading || fileBusy;
  const vertexMode=mode==='vertex',slot=vertexMode?'vertex':'edge';
  const initialBound=kind==='custom'?custom.initials[slot]:presetInitial;
  const initial=initialBound.state,initialKind=initial.kind;
  const edgeIndex=graph?.directed_edges.findIndex(e=>JSON.stringify(e)===JSON.stringify(initial.edge))??-1;
  const initialVertex=initial.vertex??-1;
  const initialDraftKey=`${kind==='custom'?'custom':'preset'}-${slot}`;
  const initialDraft=initialDrafts[initialDraftKey]??JSON.stringify(initialKind==='pure'?initial.vector??[]:initial.density??[],null,2);
  const effectiveParameters=kind==='custom'?custom.parameters:vertexParameters;
  const topologyReady=!!graph && (kind!=='custom'||graphProblems(graph).length===0);
  const matricesReady=!!graph && (kind==='custom'?graph.vertices.every(x=>!matrixProblem(custom,x,graph)):Object.keys(presetDrafts).length===0);
  const vertexDraftKey=kind==='custom'?'custom':'preset';
  const parametersReady=vertexDrafts[vertexDraftKey]===undefined&&(kind!=='custom'||parameterProblems(custom).length===0);
  const stateReady=!!graph&&initialReady(initialBound,graph,vertexMode)&&(!['pure','mixed'].includes(initialKind)||initialDrafts[initialDraftKey]===undefined);
  const canSimulate=topologyReady&&matricesReady&&stateReady&&(!vertexMode||parametersReady);
  const vertexLabel=(x:number)=>kind==='custom'?`${custom.vertices.find(v=>v.id===x)?.label??x} · ${x}`:String(x);
  function updateInitial(state:InitialStateSpec,accepted=true) {
    const bound={state,basis:accepted&&graph?basisKey(graph,vertexMode):''};
    if(kind==='custom')setCustom(d=>({...d,initials:{...d.initials,[slot]:bound}}));else setPresetInitial(bound);
    reset();
  }
  const setInitialKind=(kind:InitialStateSpec['kind'])=>updateInitial({...initial,kind},kind!=='pure'&&kind!=='mixed');
  const setEdgeIndex=(i:number)=>{if(graph?.directed_edges[i])updateInitial({...initial,edge:graph.directed_edges[i]});};
  const setInitialVertex=(x:number)=>updateInitial({...initial,vertex:x});

  function reset() { setPlaying(false); request.current?.abort(); setBusy(false); setSimulation(null); setCursor(0); setError(null); }
  useEffect(() => {
    if(kind==='custom') {request.current?.abort();setGraphLoading(false);setBusy(false);return;}
    const controller = new AbortController();
    request.current?.abort(); request.current = controller;
    setPlaying(false); setVertexParameters({});setVertexDrafts(d=>{const next={...d};delete next.preset;return next;});setPresetDrafts({});
    setGraphLoading(true); setBusy(false); setError(null); setSimulation(null); setCursor(0); setPresetGraph(null);
    void post<GraphData>('graph', { kind, size, preset, seed }, controller.signal)
      .then((data) => { if (!controller.signal.aborted) { setPresetGraph(data);setPresetTags(Object.fromEntries(data.vertices.map(x=>[x,preset]))); setSelected(data.vertices[0]);setPresetInitial(old=>old.state.kind==='pure'||old.state.kind==='mixed'?old:{state:{...old.state,edge:data.directed_edges[0],vertex:data.vertices[0]},basis:basisKey(data,vertexMode)}); } })
      .catch((reason: unknown) => { if (!controller.signal.aborted) setError(reason); })
      .finally(() => { if (!controller.signal.aborted) setGraphLoading(false); });
    return () => controller.abort();
  }, [kind, size, preset, seed, retry]);
  useEffect(() => () => request.current?.abort(), []);

  const initialFrame = useMemo<Frame | null>(() => {
    if (!graph || !stateReady) return null;
    const vertex = mode === 'vertex';
    const diagonal=(i:number,d:number)=>initialKind==='pure'?Math.hypot(...(initial.vector?.[i]??[0,0]))**2:initialKind==='mixed'?(initial.density?.[i]?.[i]?.[0]??0):1/d;
    const probabilities = vertex ? [] : graph.directed_edges.map((_, i) => initialKind !== 'basis' ? diagonal(i,graph.dimension) : Number(i === edgeIndex));
    const vertexProbabilities = vertex ? graph.vertices.map((x,i) => initialKind !== 'basis' ? diagonal(i,graph.vertices.length) : Number(x === initialVertex))
      : graph.vertices.map((x) => graph.directed_edges.reduce((sum, [target], i) => sum + (target === x ? probabilities[i] : 0), 0));
    return {
      step: 0, edge_probabilities: probabilities,
      vertex_probabilities: vertexProbabilities,
      purity: initialKind==='mixed'?initial.density!.flat().reduce((sum,[re,im])=>sum+re*re+im*im,0):initialKind === 'maximally_mixed' ? 1 / (vertex ? graph.vertices.length : graph.dimension) : 1, trace: 1, measurement: null, measurement_probability: null, measurement_probabilities: null,
    };
  }, [graph, initial, edgeIndex, initialVertex, mode,stateReady]);
  const frame = simulation?.frames[cursor] ?? initialFrame;
  const maxStep = simulation ? simulation.frames.length - 1 : 0;
  const currentNeighbors = graph?.neighbors[String(selected)] ?? [];

  function payload(count: number, scattering = graph!.scattering): SimulationRequest {
    return { graph: kind==='custom'?customSpec(graph!):{ kind, size }, scattering, preset, mode,
      initial, steps: count, seed,
      strategy, vertex_dynamics: vertexDynamics, vertex_parameters: effectiveParameters };
  }
  async function run(count: number) {
    if (!graph || locked || !canSimulate) return;
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
      await post('scattering/validate',{matrix,degree:currentNeighbors.length},controller.signal);
      if (controller.signal.aborted) return false;
      setPlaying(false);if(kind==='custom')setCustom(d=>setMatrix(d,selected,matrix));else {setPresetTags(d=>({...d,[selected]:null}));setPresetGraph({ ...graph, scattering });setPresetDrafts(d=>{const next={...d};delete next[selected];return next;});}setSimulation(null); setCursor(0); return true;
    } catch (reason) { if (!controller.signal.aborted) setError(reason); return false; }
    finally { if (request.current === controller) setBusy(false); }
  }
  async function nodePreset(value: Preset) {
    if (!graph || locked) return;
    setBusy(true); setError(null);
    const controller = new AbortController(); request.current?.abort(); request.current = controller;
    try {
      const result = await post<{ matrix: Matrix }>('scattering', { preset: value, degree: currentNeighbors.length, seed }, controller.signal);
      if (!controller.signal.aborted && await applyMatrix(result.matrix)) {
        if(kind==='custom')setCustom(d=>({...d,matrices:{...d.matrices,[selected]:{...d.matrices[selected],preset:value}}}));
        else setPresetTags(d=>({...d,[selected]:value}));
      }
    } catch (reason) { if (!controller.signal.aborted) { setError(reason); setBusy(false); } }
  }
  function changeMode(value: Mode) { setMode(value); if (value === 'vertex') setDistribution('vertex'); reset();setEdgeStart(null);setEditMode('select'); }
  function singleStep() { if (cursor < maxStep) setCursor(cursor + 1); else void run(cursor + 1); }

  function edit(next:CustomGraphDraft,physical=true) {setCustom(next);setEditorError(null);if(physical)reset();}
  function attempt(operation:()=>void) {try{operation();setEditorError(null);}catch(reason){setEditorError(reason instanceof Error?reason.message:'endpoint');}}
  function createVertex(position:[number,number]) {attempt(()=>{const next=addVertex(custom,position);edit(next);setSelected(next.vertices.at(-1)!.id);setSelectedEdge(null);});}
  function connect(a:number,b:number) {attempt(()=>{edit(addEdge(custom,a,b));setEdgeStart(null);setSelectedEdge([Math.min(a,b),Math.max(a,b)]);});}
  async function deleteNode(id=selected) {if(await confirm('deleteVertexConfirm',{vertex:vertexLabel(id)})){edit(removeVertex(custom,id));setSelected(custom.vertices.find(v=>v.id!==id)?.id??-1);setSelectedEdge(null);setEdgeStart(null);}}
  function deleteConnection(edge=selectedEdge) {if(edge){edit(removeEdge(custom,...edge));setSelectedEdge(null);setEdgeStart(null);}}
  function selectNode(id:number) {
    setSelected(id);setSelectedEdge(null);
    if(editMode==='addEdge'){if(edgeStart===null)setEdgeStart(id);else connect(edgeStart,id);}
    if(editMode==='delete')deleteNode(id);
  }
  async function switchTopology(next:GraphKind) {
    if(kind!=='custom'&&Object.keys(presetDrafts).length&&!await confirm('discardPresetDraft'))return;
    reset();setKind(next);setSelectedEdge(null);setEdgeStart(null);setEditMode('select');setEditorError(null);
    if(next==='custom')setSelected(custom.vertices[0]?.id??-1);
    else {if(next!=='cycle'&&preset==='hadamard')setPreset('dft');if(next==='cycle'&&size<3)setSize(3);}
  }
  async function customize() {
    if(!graph)return;
    if(custom.vertices.length&&!await confirm('replaceDraft'))return;
    const next=customCopy(graph,preset,vertexParameters,initial,vertexMode);
    for(const x of graph.vertices)next.matrices[x].preset=presetTags[x]??null;
    if(!stateReady)next.initials[slot].basis='';
    setInitialDrafts(d=>({...d,[`custom-${slot}`]:initialDrafts[initialDraftKey]}));
    setVertexDrafts(d=>({...d,custom:vertexDrafts.preset}));edit(next);setKind('custom');setSelected(next.vertices[0].id);setEditMode('select');
  }
  async function applyAllPreset() {
    if(!graph||locked||graph.vertices.some(x=>graph.neighbors[x].length===0))return;
    if(!await confirm('replaceMatrices'))return;
    setBusy(true);setError(null);
    try {
      const generated=await Promise.all(graph.vertices.map(async(x,i)=>[x,(await post<{matrix:Matrix}>('scattering',{preset,degree:graph.neighbors[x].length,seed:(seed+i)>>>0})).matrix] as const));
      let next=custom;for(const [x,matrix] of generated)next=setMatrix(next,x,matrix,preset);edit(next);
    }catch(reason){setError(reason);}finally{setBusy(false);}
  }
  async function copyMatrix(source:number,targets:number[]) {
    if(!graph||!graph.scattering[source])return;
    if(!await confirm('copyConfirm',{count:targets.length}))return;
    if(kind==='custom'){let next=custom;for(const x of targets)next=setMatrix(next,x,graph.scattering[source]);edit(next);}
    else {const scattering={...graph.scattering};for(const x of targets)scattering[x]=structuredClone(graph.scattering[source]);setPresetGraph({...graph,scattering});setPresetTags(d=>({...d,...Object.fromEntries(targets.map(x=>[x,null]))}));setPresetDrafts(d=>Object.fromEntries(Object.entries(d).filter(([key])=>!targets.includes(Number(key)))));reset();}
  }
  function matrixDraft(value:string|undefined) {
    if(kind==='custom')setCustom(d=>{const drafts={...d.matrixDrafts};if(value===undefined)delete drafts[selected];else drafts[selected]=value;return {...d,matrixDrafts:drafts};});
    else setPresetDrafts(d=>{const next={...d};if(value===undefined)delete next[selected];else next[selected]=value;return next;});
    reset();
  }
  async function confirmInitial() {
    if(!graph||!topologyReady||!matricesReady)return;
    setBusy(true);setError(null);
    try {
      let value=initial;
      if(initialKind==='pure'||initialKind==='mixed'){
        let parsed:unknown;try{parsed=JSON.parse(initialDraft);}catch{throw new ApiError('initial_state');}
        value={...initial,...(initialKind==='pure'?{vector:parsed as InitialStateSpec['vector']}:{density:parsed as Matrix})};
      }
      await post('simulate',{...payload(0),initial:value});
      updateInitial(value);setInitialDrafts(d=>{const next={...d};delete next[initialDraftKey];return next;});
    }catch(reason){setError(reason);}finally{setBusy(false);}
  }
  async function applyParameters(params:VertexParameters) {
    if(!graph||!topologyReady||!matricesReady)return false;
    setBusy(true);setError(null);
    try {
      await post('simulate',{...payload(0),mode:'vertex',vertex_parameters:params,initial:{kind:'uniform'}});
      if(kind==='custom')setCustom(d=>({...d,parameters:params,omegaPorts:structuredClone(graph.neighbors)}));else setVertexParameters(params);
      setVertexDrafts(d=>{const next={...d};delete next[vertexDraftKey];return next;});reset();return true;
    }catch(reason){setError(reason);return false;}finally{setBusy(false);}
  }
  async function importDocument(document:ExperimentDocument,data:GraphData) {
    if(custom.vertices.length&&!await confirm('replaceDraft'))return false;
    const exp=document.experiment;reset();setCustom(fromDocument(document,data));setKind('custom');setMode(exp.mode);setDistribution('vertex');setPreset(exp.preset);setSeed(exp.seed);setSeedDraft(String(exp.seed));setSteps(exp.steps);setStrategy(exp.strategy??'optimized');setVertexDynamics(exp.vertex_dynamics??'trajectory');setSelected(data.vertices[0]);setSelectedEdge(null);setEdgeStart(null);setEditMode('select');setInitialDrafts(d=>Object.fromEntries(Object.entries(d).filter(([key])=>!key.startsWith('custom-'))));setVertexDrafts(d=>{const next={...d};delete next.custom;return next;});setImportRevision(n=>n+1);return true;
  }

  useEffect(() => {
    if (!playing || locked || !graph || !canSimulate) return;
    if (cursor >= steps) { setPlaying(false); return; }
    const timer = window.setTimeout(() => singleStep(), 600);
    return () => window.clearTimeout(timer);
  }, [playing, locked, cursor, maxStep, steps, graph, mode, strategy, canSimulate]);

  return <div className="app-shell">
    <ConfirmationDialog confirmation={confirmation} finish={finish} />
    <aside className="sidebar">
      <div className="brand"><div className="brand-mark"><span /><span /><span /><span /></div><div>{t('brand.lineOne')}<span>{t('brand.lineTwo')}</span></div></div>
      <div className="sidebar-caption">{t('experiment.configure')}</div>
      <section className="sidebar-section">
        <h2><span>01</span> {t('graph.title')}</h2>
        <label htmlFor="graph-kind">{t('graph.topology')}</label>
        <select id="graph-kind" value={kind} disabled={locked} onChange={(event) => switchTopology(event.target.value as GraphKind)}>
          {graphKinds.map((key) => <option key={key} value={key}>{t(`graph.presets.${key}`)}</option>)}
        </select>
        {kind!=='custom' && <><label htmlFor="graph-size">{t('graph.size')} <span className="input-note">{kind === 'star' ? t('graph.includesCenter') : t('graph.sizeRange', { min: kind === 'cycle' ? 3 : 2, max: 12 })}</span></label>
        <select id="graph-size" value={size} disabled={locked} onChange={(event) => setSize(Number(event.target.value))}>
          {Array.from({ length: kind === 'cycle' ? 10 : 11 }, (_, i) => i + (kind === 'cycle' ? 3 : 2)).map((n) => <option key={n} value={n}>{t('graph.vertices', { count: n })}</option>)}
        </select><button className="reset-button" disabled={locked||!graph||Object.keys(presetDrafts).length>0} onClick={customize}>{t('components:editor.customize')}</button></>}
        {kind==='custom' && <CustomGraphTools draft={custom} graph={customGraph} mode={editMode} setMode={value=>{setEditMode(value);setEdgeStart(null);setEditorError(null);}} busy={locked} selected={selected} edge={selectedEdge} edgeStart={edgeStart} error={editorError}
          addNow={()=>createVertex([120+(custom.vertices.length%4)*110,110+Math.floor(custom.vertices.length/4)*90])} connect={connect} selectEdge={setSelectedEdge} deleteVertex={()=>deleteNode()} deleteEdge={()=>deleteConnection()} clear={async()=>{if(await confirm('clearConfirm')){edit(emptyCustomGraph());setVertexDrafts(d=>{const next={...d};delete next.custom;return next;});setImportRevision(n=>n+1);setSelected(-1);setSelectedEdge(null);setEdgeStart(null);setInitialDrafts({});}}} />}
        <label htmlFor="global-preset">{t('graph.globalScattering')}</label>
        <select id="global-preset" value={preset} disabled={locked} onChange={(event) => setPreset(event.target.value as Preset)}>
          {presets.map((item) => <option key={item.value} value={item.value} disabled={item.value === 'hadamard' && (kind==='custom'?customGraph.vertices.some(x=>customGraph.neighbors[x].length!==2):kind !== 'cycle')}>{t(item.labelKey, { ns: 'components' })}</option>)}
        </select>
        {kind==='custom'?<button className="reset-button" disabled={locked||!customGraph.vertices.length||customGraph.vertices.some(x=>!customGraph.neighbors[x].length||(preset==='hadamard'&&customGraph.neighbors[x].length!==2))} onClick={()=>void applyAllPreset()}>{t('components:editor.applyAll')}</button>:<p className="sidebar-hint">{t('graph.matrixHint')}</p>}
        <ExperimentFiles canExport={kind==='custom'&&canSimulate&&parametersReady} busy={locked} onBusy={setFileBusy} exportDocument={()=>toDocument(custom,payload(steps))} onImport={importDocument} />
      </section>
      <section className="sidebar-section">
        <h2><span>02</span> {t('initial.title')}</h2>
        <label htmlFor="initial-kind">{t('initial.preparation')}</label>
        <select id="initial-kind" value={initialKind} disabled={locked} onChange={(event) => { setInitialKind(event.target.value as InitialStateSpec['kind']); reset(); }}>
          <option value="basis">{t(mode === 'vertex' ? 'research:initial.vertexBasis' : 'initial.basis')}</option><option value="uniform">{t('initial.uniform')}</option><option value="maximally_mixed">{t('research:initial.mixed')}</option>
          <option value="pure">{t('components:editor.pureState')}</option><option value="mixed">{t('components:editor.mixedState')}</option>
        </select>
        {mode === 'vertex' ? <><label htmlFor="initial-vertex">{t('research:initial.vertex')}</label><select id="initial-vertex" value={initialVertex} disabled={locked || initialKind !== 'basis'} onChange={(event) => { setInitialVertex(Number(event.target.value)); reset(); }}><option value={-1} disabled>{t('components:editor.choose')}</option>{graph?.vertices.map((x) => <option key={x} value={x}>{vertexLabel(x)}</option>)}</select></> : <>
        <label htmlFor="initial-edge">{t('initial.directedEdge')}</label>
        <select id="initial-edge" value={edgeIndex} disabled={locked || !graph || initialKind !== 'basis'} onChange={(event) => { setEdgeIndex(Number(event.target.value)); reset(); }}>
          {edgeIndex<0&&<option value={-1} disabled>{t('components:editor.choose')}</option>}
          {graph?.directed_edges.map(([x, y], i) => <option key={`${x},${y}`} value={i}>|{x},{y}⟩ · {y} → {x}</option>)}
        </select>
        <p className="sidebar-hint">{t('initial.convention')}</p></>}
        {graph&&['pure','mixed'].includes(initialKind)&&<InitialStateInput graph={graph} vertex={vertexMode} state={initial} draft={initialDraft} onDraft={text=>{setInitialDrafts(d=>({...d,[initialDraftKey]:text}));reset();}} apply={()=>void confirmInitial()} busy={locked||!topologyReady||!matricesReady|| (vertexMode&&!parametersReady)} />}
        {graph&&!stateReady&&<p className="editor-warning">{t('components:editor.initialReview')}</p>}
        {graph&&!stateReady&&!['pure','mixed'].includes(initialKind)&&<button className="reset-button" disabled={locked||!topologyReady||!matricesReady||(vertexMode&&!parametersReady)} onClick={()=>void confirmInitial()}>{t('components:editor.applyInitial')}</button>}
      </section>
      <section className="sidebar-section">
        <h2><span>03</span> {t('simulation.title')}</h2>
        {mode !== 'unitary' && <><label htmlFor="strategy">{t('research:strategy.label')}</label><select id="strategy" value={strategy} disabled={locked} onChange={(event) => { setStrategy(event.target.value as Strategy); reset(); }}><option value="optimized">{t('research:strategy.optimized')}</option><option value="reference">{t('research:strategy.reference')}</option></select></>}
        {mode === 'vertex' && <><label htmlFor="vertex-dynamics">{t('research:vertex.dynamics')}</label><select id="vertex-dynamics" value={vertexDynamics} disabled={locked} onChange={(event) => { setVertexDynamics(event.target.value as 'trajectory' | 'mean'); reset(); }}><option value="trajectory">{t('research:vertex.trajectory')}</option><option value="mean">{t('research:vertex.mean')}</option></select></>}
        <div className="input-pair"><div><label htmlFor="steps">{t('simulation.steps')}</label><input id="steps" type="number" min="1" max="200" step="1" value={steps} disabled={locked} onChange={(event) => setSteps(Math.max(1, Math.min(200, Math.trunc(Number(event.target.value)) || 1)))} /></div>
          <div><label htmlFor="seed">{t('simulation.seed')}</label><input id="seed" type="number" min="0" max="2147483647" value={seedDraft} disabled={locked} onChange={(event) => setSeedDraft(event.target.value)} onBlur={(event) => { if (event.relatedTarget instanceof Element && event.relatedTarget.closest('.language-switcher')) return; const next = Math.max(0, Math.min(2147483647, Math.floor(Number(seedDraft) || 0))); setSeedDraft(String(next)); setSeed(next); if(kind==='custom')reset(); }} onKeyDown={(event) => { if (event.key === 'Enter') event.currentTarget.blur(); }} /></div></div>
        <button className="run-button" disabled={locked || !canSimulate} onClick={() => void run(steps)}><span>{busy ? '◌' : '▶'}</span>{t(busy ? 'simulation.computing' : 'simulation.run')}</button>
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
        <section className="panel graph-panel"><div className="panel-header"><div><div className="eyebrow">{t('graph.space')}</div><h2>{t(`graph.presets.${kind}`)} <span className="subtle">/ {t('graph.vertices', { count: kind==='custom'?custom.vertices.length:size })}</span></h2></div><span className="pill">{graph ? t('graph.edges', { count: graph.edges.length }) : t('graph.unknownEdges')}</span></div>
          {graph ? <GraphView graph={graph} probabilities={frame?.vertex_probabilities??[]} selected={selected} onSelect={(vertex) => { if (!busy) setSelected(vertex); }} editor={kind==='custom'?{
            vertices:custom.vertices,mode:editMode,edgeStart,selectedEdge,disabled:locked,
            onCanvas:position=>{if(editMode==='addVertex')createVertex(position);},onNode:selectNode,
            onEdge:edge=>{setSelectedEdge(edge);if(editMode==='delete')deleteConnection(edge);},onMove:(id,position)=>edit(moveVertex(custom,id,position),false),
          }:undefined} /> : <div className="graph-placeholder">{graphLoading ? <><span className="loading-orbit" />{t('graph.preparing')}</> : <>{t('graph.startBackend')}</>}</div>}
          {kind==='custom'&&<p className="graph-editor-caption">{selectedEdge?t('components:editor.endpoints',{a:vertexLabel(selectedEdge[0]),b:vertexLabel(selectedEdge[1])}):t('components:editor.undirected')}</p>}
          <div className="graph-legend"><span><i className="legend-selected" /> {t('graph.selectedVertex')}</span><span><i className="legend-gradient" /> P(x) = 0 → 1</span><span className="legend-note">{t(mode === 'vertex' ? 'research:born.vertex' : 'graph.incomingMarginal')}</span></div>
        </section>

        <section className="panel inspector-panel"><div className="panel-header"><div><div className="eyebrow">{t('inspector.operator')}</div><h2>{t('inspector.matrix')} <span className="math">S(x)</span></h2></div></div>
          <div className="node-select"><label htmlFor="selected-node">{t('inspector.vertex')}</label><select id="selected-node" value={selected} disabled={locked || !graph?.vertices.length} onChange={(event) => {setSelected(Number(event.target.value));setSelectedEdge(null);}}>{graph?.vertices.map((vertex) => <option key={vertex} value={vertex}>{vertexLabel(vertex)}</option>)}</select><span>{t('inspector.degree', { degree: currentNeighbors.length })}</span></div>
          {kind==='custom'&&custom.vertices.some(v=>v.id===selected)&&<><VertexName id={selected} label={custom.vertices.find(v=>v.id===selected)!.label} busy={locked} onRename={label=>attempt(()=>edit(renameVertex(custom,selected,label),false))} />
            {matrixProblem(custom,selected)&&<p className="support-notice">{t('components:editor.matrixReview',{ports:currentNeighbors.join(', ')})}</p>}
            {custom.matrices[selected]&&matrixProblem(custom,selected)==='changedPorts'&&<details><summary>{t('components:editor.retainedMatrix',{ports:custom.matrices[selected].ports.join(', ')})}</summary><pre className="record-line">{JSON.stringify(custom.matrices[selected].matrix,null,2)}</pre></details>}</>}
          {graph&&graph.vertices.includes(selected) ? <MatrixEditor vertex={selected} neighbors={currentNeighbors} matrix={kind==='custom'&&matrixProblem(custom,selected)==='changedPorts'?emptyMatrix:graph.scattering[String(selected)]??emptyMatrix} busy={locked} onApply={applyMatrix} onPreset={(value) => void nodePreset(value)} draftValue={kind==='custom'?custom.matrixDrafts[selected]:presetDrafts[selected]} onDraftChange={matrixDraft} /> : <p className="muted">{t('inspector.empty')}</p>}
          {graph&&currentNeighbors.length>0&&<div className="matrix-extra"><button className="text-button" disabled={locked} onClick={()=>void nodePreset('identity')}>{t('components:editor.identity')}</button>
            <label>{t('components:editor.copyFrom')}<select value="" disabled={locked} onChange={e=>void copyMatrix(Number(e.target.value),[selected])}><option value="">{t('components:editor.choose')}</option>{graph.vertices.filter(x=>x!==selected&&graph.neighbors[x].length===currentNeighbors.length&&(kind==='custom'?!matrixProblem(custom,x):presetDrafts[x]===undefined)).map(x=><option key={x} value={x}>{vertexLabel(x)}</option>)}</select></label>
            <button className="text-button" disabled={locked||(kind==='custom'?!!matrixProblem(custom,selected):presetDrafts[selected]!==undefined)} onClick={()=>void copyMatrix(selected,graph.vertices.filter(x=>x!==selected&&graph.neighbors[x].length===currentNeighbors.length))}>{t('components:editor.applySameDegree')}</button><p className="muted small">{t('components:editor.seedHelp',{seed})}</p></div>}
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

      <section className="playback-bar" aria-label={t('simulation.controls')}><div className="playback-buttons"><button title={t('simulation.previous')} aria-label={t('simulation.previous')} disabled={locked || cursor === 0} onClick={() => { setPlaying(false); setCursor(cursor - 1); }}>←</button><button disabled={!canSimulate || graphLoading || (!playing && cursor >= steps)} onClick={() => setPlaying(!playing)} aria-pressed={playing}>{t(playing ? 'research:playback.pause' : 'research:playback.play')}</button><button className="step-button" disabled={locked || !canSimulate || cursor >= 200} onClick={singleStep}>{t('simulation.step')} <span>→</span></button></div><div className="scrubber"><label htmlFor="time-slider">{t('simulation.timeline')} <strong>t = {frame?.step ?? 0}</strong></label><input id="time-slider" type="range" min="0" max={Math.max(1, maxStep)} value={cursor} disabled={locked || maxStep === 0} onChange={(event) => { setPlaying(false); setCursor(Number(event.target.value)); }} /></div><span className="playback-end">{t('simulation.stepCount', { count: maxStep })}</span></section>

      {(mode === 'trajectory' || (mode === 'vertex' && vertexDynamics === 'trajectory')) && <section className="panel trajectory-panel"><div className="panel-header"><div><div className="eyebrow">{t('trajectory.log')}</div><h2>{t('trajectory.title')}</h2></div><span className="pill">{t('simulation.seed')} {seed}</span></div><p className="muted small">{t(mode === 'vertex' ? 'research:vertex.timing' : 'trajectory.timing')}</p>
        {simulation && cursor > 0 ? <><div className="outcome-list">{simulation.frames.slice(1, cursor + 1).map((item) => <button key={item.step} className={item.step === cursor ? 'outcome active' : 'outcome'} onClick={() => setCursor(item.step)} title={t('trajectory.conditionalProbability', { probability: item.measurement_probability === null ? '—' : number(item.measurement_probability, 6) })}><small>n = {item.step}</small><strong>x = {item.measurement}</strong><span>p = {item.measurement_probability === null ? '—' : number(item.measurement_probability, 3)}</span></button>)}</div><p className="small muted">{t('trajectory.probabilities')} {frame?.measurement_probabilities?.map((p, i) => `x=${graph?.vertices[i]}: ${number(p)}`).join(' · ')}</p></> : <p className="muted">{t('trajectory.empty')}</p>}
      </section>}
      {mode === 'vertex' && graph && <VertexControls key={`${kind}/${size}/${importRevision}`} graph={graph} previousPorts={kind==='custom'?custom.omegaPorts:graph.neighbors} draft={vertexDrafts[vertexDraftKey]} onDraft={draft=>{setVertexDrafts(d=>({...d,[vertexDraftKey]:draft}));reset();}} parameters={effectiveParameters} busy={locked||!topologyReady||!matricesReady} onApply={applyParameters} />}
      {(mode === 'trajectory' || mode === 'vertex' || mode === 'open') && graph && frame && canSimulate && <ResearchPanels
        graph={graph} experiment={payload(steps)} cursor={cursor} frame={frame} />}
      {mode !== 'unitary' && graph && canSimulate && <><nav className="research-navigation" aria-label={t('statistics:navigation')}><a href="#trajectory-statistics">{t('statistics:title')} ↓</a></nav><StationaryPanel experiment={payload(steps)} /><StatisticsPanel experiment={payload(steps)} graph={graph} /></>}
      <footer className="workspace-footer"><span>|xy⟩ ≡ y → x <span>·</span> {t('footer.graphClass')}</span><span>{t('footer.distinction')}</span></footer>
    </main>
  </div>;
}

function superscript(value: number) { return String(value).split('').map((digit) => '⁰¹²³⁴⁵⁶⁷⁸⁹'[Number(digit)]).join(''); }
