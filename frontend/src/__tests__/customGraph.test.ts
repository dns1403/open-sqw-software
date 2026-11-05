import { describe,expect,it } from 'vitest';
import { addEdge,addVertex,basisKey,customCopy,draftGraph,emptyCustomGraph,fromDocument,graphProblems,initialReady,
  matrixProblem,moveVertex,parameterProblems,removeEdge,removeVertex,renameVertex,setMatrix,toDocument } from '../customGraph';
import { matrixCheck,parseComplex,parseMatrix,unitaryResidual } from '../matrixValidation';
import type { Matrix,SimulationRequest } from '../types';
const identity=(d:number):Matrix=>Array.from({length:d},(_,i)=>Array.from({length:d},(_,j)=>[Number(i===j),0]));
function path() {let d=emptyCustomGraph();for(let i=0;i<3;i++)d=addVertex(d,[100*i,50]);return addEdge(addEdge(d,0,1),1,2);}
function prepared() {let d=path();for(const x of draftGraph(d).vertices)d=setMatrix(d,x,identity(draftGraph(d).neighbors[x].length),'identity');return d;}

describe('graph draft operations and scientific bindings',()=>{
  it('keeps incomplete states editable, validates connectivity and constructs both orientations',()=>{
    expect(graphProblems(draftGraph(emptyCustomGraph()))).toEqual(['minimum']);
    let d=path();expect(graphProblems(draftGraph(d))).toEqual([]);
    expect(draftGraph(d).directed_edges).toEqual([[0,1],[1,0],[1,2],[2,1]]);
    d=removeEdge(d,1,2);expect(graphProblems(draftGraph(d))).toEqual(['disconnected']);
  });
  it('rejects self-loops, reversed duplicates and unknown endpoints',()=>{
    const d=path();expect(()=>addEdge(d,1,1)).toThrow('loop');expect(()=>addEdge(d,1,0)).toThrow('duplicate');expect(()=>addEdge(d,2,8)).toThrow('endpoint');
  });
  it('renames and moves without changing IDs, matrices, ports or physical basis',()=>{
    const d=prepared(),before=draftGraph(d);
    const edited=moveVertex(renameVertex(d,1,'Center B'),1,[20,-30]);
    expect(edited.vertices[1]).toEqual({id:1,label:'Center B',position:[20,-30]});
    expect(draftGraph(edited)).toEqual(before);expect(edited.matrices).toBe(d.matrices);
  });
  it('preserves old data on degree changes and marks only affected matrices',()=>{
    const d=prepared(),edited=addEdge(d,0,2);
    expect(edited.matrices).toBe(d.matrices);
    expect(matrixProblem(edited,0)).toBe('changedPorts');expect(matrixProblem(edited,2)).toBe('changedPorts');expect(matrixProblem(edited,1)).toBeUndefined();
    const fixed=setMatrix(edited,0,identity(2));expect(matrixProblem(fixed,0)).toBeUndefined();
    expect(()=>setMatrix(edited,2,identity(1))).toThrow('unitary');
  });
  it('detects same-degree neighbor replacement and does not silently relabel matrix ports',()=>{
    const d=prepared(),edited=addEdge(removeEdge(d,0,1),0,2);
    expect(draftGraph(edited).neighbors[0]).toEqual([2]);expect(edited.matrices[0].ports).toEqual([1]);
    expect(matrixProblem(edited,0)).toBe('changedPorts');
  });
  it('deletes vertex/incident edges explicitly, preserving surviving scientific records and monotone IDs',()=>{
    const d=prepared(),edited=removeVertex(d,1);
    expect(edited.edges).toEqual([]);expect(edited.matrices[0]).toBe(d.matrices[0]);expect(edited.matrices[1]).toBeUndefined();
    expect(addVertex(edited,[0,0]).vertices.at(-1)?.id).toBe(3);
  });
  it('binds manual omega to physical ports and retains unaffected values after edits',()=>{
    const d=prepared();d.parameters={omega:{0:[[1,0]],1:[[1,0],[0,0]],2:[[0,1]]},beta:{0:0,1:.5,2:1}};d.omegaPorts=draftGraph(d).neighbors;
    const edited=addEdge(d,0,2);expect(parameterProblems(edited)).toEqual([0,2]);expect(edited.parameters).toBe(d.parameters);
  });
  it('invalidates explicit initial vectors on basis changes, but retains surviving basis labels',()=>{
    const graph=draftGraph(prepared()),changed=draftGraph(addEdge(prepared(),0,2));
    const bound={state:{kind:'pure' as const,vector:[[1,0],[0,0],[0,0],[0,0]] as [number,number][]},basis:basisKey(graph,false)};
    expect(initialReady(bound,graph,false)).toBe(true);expect(initialReady(bound,changed,false)).toBe(false);
    expect(initialReady({state:{kind:'basis',edge:[0,1]},basis:bound.basis},changed,false)).toBe(true);
    expect(initialReady({state:{kind:'basis',edge:[0,2]},basis:bound.basis},graph,false)).toBe(false);
  });
  it('keeps preset copies independent and records unsubmitted drafts as requiring attention',()=>{
    const graph=draftGraph(prepared()),copy=customCopy(graph,'identity');
    copy.matrices[1].matrix[0][0][0]=2;expect(graph.scattering[1][0][0][0]).toBe(1);
    const d=prepared();d.matrixDrafts[0]='[[[0,1]]]';expect(matrixProblem(d,0)).toBe('unappliedMatrix');
    expect(matrixProblem(setMatrix(d,0,[[[0,1]]]),0)).toBeUndefined();
  });
  it('round-trips complex values, labels, positions, ports and bound initial state without precision loss',()=>{
    let d=setMatrix(prepared(),0,[[[Math.cos(.3),Math.sin(.3)]]]);d=renameVertex(d,1,'B');
    const graph=draftGraph(d);d.initials.edge={state:{kind:'basis',edge:[1,0]},basis:basisKey(graph,false)};
    const exp:SimulationRequest={graph:{kind:'path',size:3},preset:'identity',scattering:{},mode:'trajectory',steps:12,seed:42,initial:d.initials.edge.state};
    const document=JSON.parse(JSON.stringify(toDocument(d,exp)));
    const restored=fromDocument(document,graph);
    expect(restored.vertices).toEqual(d.vertices);expect(restored.matrices).toEqual(d.matrices);expect(restored.initials.edge).toEqual(d.initials.edge);
    expect(toDocument(restored,document.experiment)).toEqual(document);
  });
});
describe('safe complex matrix inputs',()=>{
  it.each([['0.5',[.5,0]],['-0.5',[-.5,0]],['0.5+0.5i',[.5,.5]],['-0.70710678i',[0,-.70710678]],['1',[1,0]],['-i',[0,-1]],['1e-3-2e-4i',[.001,-.0002]]])('parses %s without expression evaluation',(text,expected)=>expect(parseComplex(text)).toEqual(expected));
  it.each(['NaN','Infinity','Math.sin(1)','1/2','alert(1)','1++2i'])('rejects invalid input %s',value=>expect(()=>parseComplex(value)).toThrow());
  it('validates complex U(1), Hadamard, dimensions and nonunitarity at the core tolerance',()=>{
    expect(unitaryResidual(parseMatrix('[["i"]]',1))).toBe(0);
    const h=[[[Math.SQRT1_2,0],[Math.SQRT1_2,0]],[[Math.SQRT1_2,0],[-Math.SQRT1_2,0]]];
    expect(matrixCheck(JSON.stringify(h),2).error).toBeUndefined();
    expect(matrixCheck('[[2]]',1).error).toBe('unitary');expect(matrixCheck('[[1]]',2).error).toBe('shape');
    expect(matrixCheck('{invalid',1).error).toBe('json');
  });
});
