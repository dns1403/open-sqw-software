import type { GraphData, InitialStateSpec, Matrix, Preset, SimulationRequest, VertexParameters } from './types';
import { matrixCheck } from './matrixValidation';

export interface EditorVertex { id:number; label:string; position:[number,number]; }
export interface BoundInitial { state:InitialStateSpec; basis:string; }
export interface CustomGraphDraft {
  vertices:EditorVertex[]; edges:[number,number][]; nextId:number;
  matrices:Record<string,{matrix:Matrix;ports:number[];preset:Preset|null}>;
  matrixDrafts:Record<string,string>;
  parameters:VertexParameters; omegaPorts:Record<string,number[]>;
  initials:{edge:BoundInitial;vertex:BoundInitial};
}
export interface ExperimentDocument {
  format:'sqw-experiment';version:1;experiment:SimulationRequest;
  vertices:EditorVertex[];matrix_presets:Record<string,Preset|null>;
}
export type EditMode='select'|'addVertex'|'addEdge'|'delete';
export const samePorts=(a:number[]|undefined,b:number[])=>JSON.stringify(a)===JSON.stringify(b);
export function emptyCustomGraph():CustomGraphDraft {
  return {vertices:[],edges:[],nextId:0,matrices:{},matrixDrafts:{},parameters:{},omegaPorts:{},
    initials:{edge:{state:{kind:'basis'},basis:''},vertex:{state:{kind:'basis'},basis:''}}};
}
export function draftGraph(draft:CustomGraphDraft):GraphData {
  const vertices=draft.vertices.map(v=>v.id).sort((a,b)=>a-b);
  const edges=draft.edges.map(([a,b])=>[Math.min(a,b),Math.max(a,b)] as [number,number]).sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
  const neighbors=Object.fromEntries(vertices.map(x=>[x,edges.filter(e=>e.includes(x)).map(([a,b])=>a===x?b:a).sort((a,b)=>a-b)]));
  const directed_edges=vertices.flatMap(x=>neighbors[x].map(y=>[x,y] as [number,number]));
  return {vertices,edges,neighbors,directed_edges,dimension:directed_edges.length,
    scattering:Object.fromEntries(vertices.filter(x=>draft.matrices[x]).map(x=>[x,draft.matrices[x].matrix]))};
}
export function customSpec(graph:GraphData):SimulationRequest['graph'] {
  return {kind:'custom',size:graph.vertices.length,vertices:graph.vertices,edges:graph.edges,neighbors:graph.neighbors};
}
export function basisKey(graph:GraphData,vertex:boolean) { return JSON.stringify(vertex?graph.vertices:graph.directed_edges); }
export function graphProblems(graph:GraphData):string[] {
  if(graph.vertices.length<2) return ['minimum'];
  if(graph.vertices.length>32 || graph.edges.length>128) return ['limit'];
  const reached=new Set<number>(),todo=[graph.vertices[0]];
  while(todo.length) {const x=todo.pop()!;if(reached.has(x))continue;reached.add(x);todo.push(...graph.neighbors[x].filter(y=>!reached.has(y)));}
  return reached.size<graph.vertices.length?['disconnected']:[];
}
export function addVertex(draft:CustomGraphDraft,position:[number,number]):CustomGraphDraft {
  if(draft.vertices.length>=32 || draft.nextId>2**31-1) throw new Error('limit');
  if(!position.every(Number.isFinite)) throw new Error('position');
  const id=draft.nextId;
  return {...draft,nextId:id+1,vertices:[...draft.vertices,{id,label:id<26?String.fromCharCode(65+id):String(id),position}]};
}
export function addEdge(draft:CustomGraphDraft,a:number,b:number):CustomGraphDraft {
  if(a===b)throw new Error('loop');
  if(![a,b].every(x=>draft.vertices.some(v=>v.id===x)))throw new Error('endpoint');
  if(draft.edges.some(e=>e.includes(a)&&e.includes(b)))throw new Error('duplicate');
  if(draft.edges.length>=128)throw new Error('limit');
  return {...draft,edges:[...draft.edges,[Math.min(a,b),Math.max(a,b)]]};
}
export function removeEdge(draft:CustomGraphDraft,a:number,b:number):CustomGraphDraft {
  return {...draft,edges:draft.edges.filter(e=>!(e.includes(a)&&e.includes(b)))};
}
export function removeVertex(draft:CustomGraphDraft,id:number):CustomGraphDraft {
  // Explicit deletion removes this vertex's data; every surviving record stays intact.
  const omit=<T,>(data:Record<string,T>)=>Object.fromEntries(Object.entries(data).filter(([k])=>k!==String(id)));
  return {...draft,vertices:draft.vertices.filter(v=>v.id!==id),edges:draft.edges.filter(e=>!e.includes(id)),
    matrices:omit(draft.matrices),matrixDrafts:omit(draft.matrixDrafts),omegaPorts:omit(draft.omegaPorts),
    parameters:{...(draft.parameters.omega?{omega:omit(draft.parameters.omega)}:{}),...(draft.parameters.beta?{beta:omit(draft.parameters.beta)}:{})}};
}
export function moveVertex(draft:CustomGraphDraft,id:number,position:[number,number]):CustomGraphDraft {
  if(!position.every(Number.isFinite))throw new Error('position');
  return {...draft,vertices:draft.vertices.map(v=>v.id===id?{...v,position}:v)};
}
export function renameVertex(draft:CustomGraphDraft,id:number,label:string):CustomGraphDraft {
  if(!label.trim()||label.length>64)throw new Error('label');
  return {...draft,vertices:draft.vertices.map(v=>v.id===id?{...v,label}:v)};
}
export function matrixProblem(draft:CustomGraphDraft,x:number,graph=draftGraph(draft)):string|undefined {
  const record=draft.matrices[x],ports=graph.neighbors[x];
  if(!record)return 'missingMatrix';
  if(!samePorts(record.ports,ports))return 'changedPorts';
  const error=matrixCheck(draft.matrixDrafts[x]??JSON.stringify(record.matrix),ports.length).error;
  return error ?? (draft.matrixDrafts[x]!==undefined?'unappliedMatrix':undefined);
}
export function setMatrix(draft:CustomGraphDraft,id:number,matrix:Matrix,preset:Preset|null=null):CustomGraphDraft {
  const ports=draftGraph(draft).neighbors[id];
  if(!ports||matrixCheck(JSON.stringify(matrix),ports.length).error)throw new Error('unitary');
  const drafts={...draft.matrixDrafts};delete drafts[id];
  return {...draft,matrixDrafts:drafts,matrices:{...draft.matrices,[id]:{matrix:structuredClone(matrix),ports:[...ports],preset}}};
}
export function parameterProblems(draft:CustomGraphDraft,graph=draftGraph(draft)):number[] {
  return graph.vertices.filter(x=>{
    const w=draft.parameters.omega?.[x];
    return (draft.parameters.omega!=null && (!w || !samePorts(draft.omegaPorts[x],graph.neighbors[x]) || w.length!==graph.neighbors[x].length))
      || (draft.parameters.beta!=null && !Number.isFinite(draft.parameters.beta[x]));
  });
}
export function initialReady(bound:BoundInitial,graph:GraphData,vertex:boolean):boolean {
  if(!bound.basis)return false;
  if(bound.state.kind==='basis')return vertex?graph.vertices.includes(bound.state.vertex??-1):graph.directed_edges.some(e=>JSON.stringify(e)===JSON.stringify(bound.state.edge));
  return bound.basis===basisKey(graph,vertex);
}
export function customCopy(graph:GraphData,preset:Preset,parameters:VertexParameters={},initial?:InitialStateSpec,vertex=false):CustomGraphDraft {
  const draft=emptyCustomGraph();
  draft.vertices=graph.vertices.map((id,i)=>({id,label:String(id),position:[250+150*Math.cos(2*Math.PI*i/graph.vertices.length),200+150*Math.sin(2*Math.PI*i/graph.vertices.length)]}));
  draft.edges=structuredClone(graph.edges);draft.nextId=Math.max(...graph.vertices)+1;
  draft.matrices=Object.fromEntries(graph.vertices.map(x=>[x,{matrix:structuredClone(graph.scattering[x]),ports:[...graph.neighbors[x]],preset}]));
  draft.parameters=structuredClone({...(parameters.omega?{omega:parameters.omega}:{}),...(parameters.beta?{beta:parameters.beta}:{})});draft.omegaPorts=structuredClone(graph.neighbors);
  if(initial)draft.initials[vertex?'vertex':'edge']={state:structuredClone(initial),basis:basisKey(graph,vertex)};
  return draft;
}
export function toDocument(draft:CustomGraphDraft,experiment:SimulationRequest):ExperimentDocument {
  const graph=draftGraph(draft);
  if(graphProblems(graph).length || graph.vertices.some(x=>matrixProblem(draft,x,graph)) || parameterProblems(draft,graph).length)throw new Error('notReady');
  if(!initialReady(draft.initials[experiment.mode==='vertex'?'vertex':'edge'],graph,experiment.mode==='vertex'))throw new Error('initialReview');
  return {format:'sqw-experiment',version:1,experiment:{...experiment,graph:customSpec(graph),scattering:graph.scattering,
    initial:draft.initials[experiment.mode==='vertex'?'vertex':'edge'].state,vertex_parameters:draft.parameters},
    vertices:structuredClone(draft.vertices),matrix_presets:Object.fromEntries(graph.vertices.map(x=>[x,draft.matrices[x].preset]))};
}
/** Call only with the server-validated document/graph. Invalid imports never get here. */
export function fromDocument(document:ExperimentDocument,graph:GraphData):CustomGraphDraft {
  const exp=document.experiment;
  const draft=customCopy(graph,exp.preset,exp.vertex_parameters,exp.initial,exp.mode==='vertex');
  draft.vertices=structuredClone(document.vertices);
  for(const x of graph.vertices)draft.matrices[x].preset=document.matrix_presets[x];
  return draft;
}
