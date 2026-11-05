import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
import MatrixEditor from '../MatrixEditor';
import ExperimentFiles from '../ExperimentFiles';
import { setLanguage } from '../i18n';
import { customCopy, toDocument } from '../customGraph';
import type { GraphData, Matrix, SimulationRequest } from '../types';

const canvas=vi.hoisted(()=>({current:null as any,draw:vi.fn()}));
vi.mock('plotly.js-basic-dist-min',()=>({default:{react:vi.fn(()=>Promise.resolve()),purge:vi.fn(),Plots:{resize:vi.fn()}}}));
vi.mock('cytoscape',()=>({default:(options:any)=>{
  const node={style:vi.fn(),select:vi.fn(),unselect:vi.fn(),data:vi.fn(),position:vi.fn(),toggleClass:vi.fn()};
  const handlers:Record<string,(event:any)=>void>={};
  const cy={on:(event:string,selector:any,callback:any)=>{handlers[`${event}/${typeof selector==='string'?selector:''}`]=callback??selector;},batch:(f:()=>void)=>f(),getElementById:()=>node,edges:()=>node,autoungrabify:vi.fn(),resize:vi.fn(),fit:vi.fn(),destroy:vi.fn()};
  canvas.current={cy,handlers,options};canvas.draw(options);return cy;
}}));
const requests:{route:string;body:any}[]=[];
const identity=(d:number):Matrix=>Array.from({length:d},(_,i)=>Array.from({length:d},(_,j)=>[Number(i===j),0]));
function graph(spec:any,scattering?:Record<string,Matrix>):GraphData {
  const vertices:number[]=spec.vertices??Array.from({length:spec.size},(_,i)=>i);
  const edges:[number,number][]=spec.edges??vertices.slice(1).map((x,i)=>[i,x]);
  if(!spec.edges&&spec.kind==='cycle')edges.push([0,vertices.length-1]);
  const neighbors=spec.neighbors??Object.fromEntries(vertices.map(x=>[x,edges.filter(e=>e.includes(x)).map(e=>e.find(y=>y!==x)!).sort((a,b)=>a-b)]));
  const directed_edges=vertices.flatMap(x=>(neighbors[x] as number[]).map(y=>[x,y] as [number,number]));
  return {vertices,edges,neighbors,directed_edges,dimension:directed_edges.length,scattering:scattering??Object.fromEntries(vertices.map(x=>[x,identity(neighbors[x].length)]))};
}
const field=(id:string)=>document.getElementById(id) as HTMLInputElement;
const change=(id:string,value:string)=>fireEvent.change(field(id),{target:{value}});
const click=(name:string)=>fireEvent.click(screen.getByRole('button',{name}));
const run=()=>document.querySelector('.run-button') as HTMLButtonElement;
async function ready(){await waitFor(()=>expect(run()).toBeEnabled());}
async function launch(){render(<App/>);await ready();}
async function choosePreset(id:number,preset:string){change('selected-node',String(id));change('node-preset',preset);await waitFor(()=>expect(field('node-preset')).toBeEnabled());}
function connect(a:number,b:number){fireEvent.change(screen.getByLabelText('First endpoint'),{target:{value:String(a)}});fireEvent.change(screen.getByLabelText('Second endpoint'),{target:{value:String(b)}});click('Connect vertices');}
function upload(file:File){fireEvent.change(screen.getByLabelText('Experiment JSON file'),{target:{files:[file]}});}
function fileFor(value:unknown){const file=new File(['payload'],'experiment.json',{type:'application/json'});Object.defineProperty(file,'text',{value:async()=>JSON.stringify(value)});return file;}

beforeEach(async()=>{
  await setLanguage('en');requests.length=0;canvas.draw.mockClear();
  vi.stubGlobal('fetch',vi.fn(async(url:string,options:RequestInit)=>{
    const body=JSON.parse(String(options.body));requests.push({route:url,body:structuredClone(body)});
    let result:any;
    if(url==='/api/graph')result=graph(body);
    else if(url==='/api/scattering')result={matrix:body.preset==='hadamard'?[[[Math.SQRT1_2,0],[Math.SQRT1_2,0]],[[Math.SQRT1_2,0],[-Math.SQRT1_2,0]]]:identity(body.degree)};
    else if(url==='/api/scattering/validate')result={matrix:body.matrix,residual:0};
    else if(url==='/api/experiments/validate'){
      if(body.version!==1)return {ok:false,status:422,json:async()=>({code:'experiment_document'})};
      result={document:body,graph:graph(body.experiment.graph,body.experiment.scattering)};
    }else if(url==='/api/simulate'){
      const g=graph(body.graph,body.scattering);
      result={graph:g,mode:body.mode,frames:Array.from({length:body.steps+1},(_,step)=>({step,edge_probabilities:g.directed_edges.map((_,i)=>Number(i===0)),vertex_probabilities:g.vertices.map((_,i)=>Number(i===0)),purity:1,trace:1,measurement:null,measurement_probability:null,measurement_probabilities:null})),outcomes:[]};
    }else throw new Error(`Unexpected endpoint ${url}`);
    return {ok:true,status:200,json:async()=>result};
  }));
});

describe('custom graph workflow',()=>{
  it('creates a path on the existing canvas, binds complex ports, and sends every model through the common API',async()=>{
    await launch();change('graph-kind','custom');expect(run()).toBeDisabled();
    click('Add Vertex');
    for(const [x,y] of [[100,80],[200,130],[300,80]])act(()=>canvas.current.handlers['tap/']({target:canvas.current.cy,position:{x,y}}));
    expect((field('selected-node') as unknown as HTMLSelectElement).options).toHaveLength(3);
    click('Add Edge');
    const tap=(id:number)=>act(()=>canvas.current.handlers['tap/node']({target:{id:()=>String(id)}}));
    tap(0);expect(screen.getByText(/Connecting from A/)).toBeInTheDocument();tap(1);tap(1);tap(2);
    connect(0,0);expect(screen.getByRole('alert')).toHaveTextContent('Self-loops');
    connect(1,0);expect(screen.getByRole('alert')).toHaveTextContent('already exists');
    await choosePreset(1,'hadamard');await choosePreset(2,'identity');change('selected-node','0');
    click('Edit');fireEvent.change(screen.getByRole('textbox',{name:'Outgoing 1, incoming 1'}),{target:{value:'i'}});
    click('Validate & apply matrix');await waitFor(()=>expect(field('matrix-json')).toBeNull());
    change('initial-kind','uniform');await ready();
    for(const mode of ['unitary','open','trajectory','vertex']){
      fireEvent.click(document.querySelectorAll('.mode')[['unitary','open','trajectory','vertex'].indexOf(mode)]);
      if(mode==='vertex')change('initial-kind','uniform');
      await ready();fireEvent.click(run());await ready();
      const req=requests.at(-1)!.body as SimulationRequest;
      expect(req.mode).toBe(mode);expect(req.graph.neighbors).toEqual({'0':[1],'1':[0,2],'2':[1]});
      expect(req.scattering['0']).toEqual([[[0,1]]]);expect(req.scattering['1'][1][1][0]).toBe(-Math.SQRT1_2);
    }
    click('Select / Move');const before=requests.length;
    act(()=>canvas.current.handlers['dragfree/node']({target:{id:()=> '0',position:()=>({x:177,y:91})}}));
    fireEvent.change(screen.getByLabelText('Display label · stable ID 0'),{target:{value:'Alpha'}});click('Rename');
    expect(requests).toHaveLength(before);expect(canvas.current.options.elements.find((e:any)=>e.data.id==='0')).toBeDefined();
    click('Edit');const raw='[["0.2+0.7i"]]';change('matrix-json',raw);expect(run()).toBeDisabled();
    await act(()=>setLanguage('de'));expect(field('matrix-json').value).toBe(raw);expect(requests).toHaveLength(before);
    await act(()=>setLanguage('en'));expect(field('matrix-json').value).toBe(raw);
  });

  it('retains incompatible matrices and custom drafts while preserving reusable presets',async()=>{
    await launch();change('graph-size','3');await ready();click('Customize this graph');await ready();
    fireEvent.change(screen.getByLabelText('Selected undirected edge'),{target:{value:'[0,1]'}});click('Delete selected edge');
    expect(run()).toBeDisabled();expect(screen.getByText('Retained matrix · previous ports [1, 2]')).toBeInTheDocument();
    change('selected-node','2');expect(screen.getAllByTitle('1 + (0)i')).toHaveLength(2);
    await choosePreset(0,'identity');await choosePreset(1,'identity');expect(run()).toBeDisabled();
    change('initial-kind','uniform');await ready();
    change('graph-kind','cycle');await ready();expect((field('initial-edge') as unknown as HTMLSelectElement).options).toHaveLength(6);
    change('graph-kind','custom');await ready();expect(Array.from((field('initial-edge') as unknown as HTMLSelectElement).options).filter(o=>o.value!=='-1')).toHaveLength(4);
    click('Delete selected vertex');click('Keep current data');expect((field('selected-node') as unknown as HTMLSelectElement).options).toHaveLength(3);
  });

  it('retains unapplied vertex parameter drafts across model changes and blocks vertex runs until validation',async()=>{
    await launch();click('Customize this graph');fireEvent.click(document.querySelectorAll('.mode')[3]);change('initial-kind','uniform');await ready();
    const omega=document.querySelectorAll('.research-columns textarea')[0] as HTMLTextAreaElement;
    fireEvent.change(omega,{target:{value:'{"unfinished":'}});expect(run()).toBeDisabled();
    fireEvent.click(document.querySelectorAll('.mode')[0]);await ready();fireEvent.click(document.querySelectorAll('.mode')[3]);
    expect((document.querySelectorAll('.research-columns textarea')[0] as HTMLTextAreaElement).value).toBe('{"unfinished":');expect(run()).toBeDisabled();
  });

  it('validates custom pure and mixed states and never reinterprets a changed physical basis',async()=>{
    await launch();change('graph-size','3');await ready();click('Customize this graph');
    for(const kind of ['pure','mixed']){
      change('initial-kind',kind);expect(run()).toBeDisabled();click('Replace draft with valid template');click('Validate & use initial state');await ready();
      const req=requests.at(-1)!.body;expect(req.initial.kind).toBe(kind);expect((kind==='pure'?req.initial.vector:req.initial.density).length).toBe(6);
    }
    fireEvent.change(screen.getByLabelText('Selected undirected edge'),{target:{value:'[0,1]'}});click('Delete selected edge');
    await choosePreset(0,'identity');await choosePreset(1,'identity');expect(run()).toBeDisabled();
    expect(JSON.parse(field('initial-json').value)).toHaveLength(6);expect(screen.getByText(/Dimension 4\./)).toBeInTheDocument();
    click('Replace draft with valid template');click('Validate & use initial state');await ready();expect(requests.at(-1)!.body.initial.density).toHaveLength(4);
  });

  it('keeps the existing draft until import confirmation and accepts server defaults without inventing manual parameters',async()=>{
    await launch();click('Customize this graph');
    const g=graph({kind:'path',size:2});g.scattering['0']=[[[0,1]]];
    const d=customCopy(g,'identity',{}, {kind:'basis',edge:[0,1]});
    const doc=toDocument(d,{graph:{kind:'path',size:2},preset:'identity',scattering:g.scattering,mode:'unitary',initial:{kind:'basis',edge:[0,1]},steps:8,seed:71});
    // Pydantic includes null for absent optional scientific parameters.
    (doc.experiment as any).vertex_parameters={omega:null,beta:null};
    upload(fileFor(doc));await screen.findByRole('dialog',{name:'Confirm change'});
    expect((field('selected-node') as unknown as HTMLSelectElement).options).toHaveLength(6);
    click('Keep current data');await screen.findByText('Import cancelled; existing draft retained.');
    expect((field('selected-node') as unknown as HTMLSelectElement).options).toHaveLength(6);
    upload(fileFor(doc));await screen.findByRole('dialog',{name:'Confirm change'});click('Confirm change');
    await screen.findByText('Experiment imported and validated.');await ready();
    expect((field('selected-node') as unknown as HTMLSelectElement).options).toHaveLength(2);
    expect(screen.getByTitle('0 + (1)i')).toBeInTheDocument();expect(field('seed').value).toBe('71');
  });

  it('rejects malformed imports without replacing the current custom experiment',async()=>{
    await launch();click('Customize this graph');const count=(field('selected-node') as unknown as HTMLSelectElement).options.length;
    upload(fileFor({format:'sqw-experiment',version:99}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid experiment file');
    expect((field('selected-node') as unknown as HTMLSelectElement).options).toHaveLength(count);await ready();
  });
});

describe('matrix input and serialization presentation',()=>{
  it('rejects nonunitary cell input locally, accepts a U(1) phase and restores accepted data on cancellation',async()=>{
    const apply=vi.fn(async()=>true);
    render(<MatrixEditor vertex={2} neighbors={[7]} matrix={[[[0,1]]]} busy={false} onApply={apply} onPreset={()=>{}}/>);
    click('Edit');fireEvent.change(screen.getByRole('textbox',{name:'Outgoing 7, incoming 7'}),{target:{value:'0.5+0.5i'}});click('Validate & apply matrix');
    expect(screen.getByRole('alert')).toHaveTextContent('not unitary');expect(apply).not.toHaveBeenCalled();
    click('Cancel');click('Edit');expect(screen.getByRole('textbox',{name:'Outgoing 7, incoming 7'})).toHaveValue('0+1i');
    fireEvent.change(screen.getByRole('textbox',{name:'Outgoing 7, incoming 7'}),{target:{value:'-i'}});click('Validate & apply matrix');
    await waitFor(()=>expect(apply).toHaveBeenCalledWith([[[0,-1]]]));
  });

  it('downloads the versioned document and applies a validated round-trip with positions and complex entries',async()=>{
    const g=graph({kind:'path',size:2});g.scattering['0']=[[[0,1]]];
    const draft=customCopy(g,'identity',{}, {kind:'basis',edge:[0,1]});draft.vertices[0]={id:0,label:'Alpha',position:[177,91]};
    const doc=toDocument(draft,{graph:{kind:'path',size:2},preset:'identity',scattering:g.scattering,mode:'unitary',initial:{kind:'basis',edge:[0,1]},steps:8,seed:71});
    const imported=vi.fn((_document:unknown)=>true),busy=vi.fn();let blob:Blob|undefined;
    vi.stubGlobal('URL',class extends URL {static createObjectURL(value:Blob){blob=value;return 'blob:experiment';}static revokeObjectURL(){}});
    const download=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{});
    render(<ExperimentFiles exportDocument={()=>doc} onImport={imported} canExport busy={false} onBusy={busy}/>);
    click('Export Experiment');await screen.findByText('Validated experiment downloaded.');
    expect(download).toHaveBeenCalled();expect(blob!.type).toBe('application/json');expect(requests.at(-1)!.body).toEqual(doc);
    upload(fileFor(doc));await screen.findByText('Experiment imported and validated.');
    expect(imported.mock.calls[0][0]).toEqual(doc);expect(busy.mock.calls.map(x=>x[0])).toEqual([true,false,true,false]);
  });
});
