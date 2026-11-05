import { useEffect, useRef } from 'react';
import cytoscape, { type Core } from 'cytoscape';
import { useTranslation } from 'react-i18next';
import type { GraphData } from './types';
import type { EditorVertex, EditMode } from './customGraph';

export interface GraphEditing {
  vertices:EditorVertex[];mode:EditMode;edgeStart:number|null;selectedEdge:[number,number]|null;disabled:boolean;
  onCanvas:(position:[number,number])=>void;onNode:(id:number)=>void;
  onEdge:(edge:[number,number])=>void;onMove:(id:number,position:[number,number])=>void;
}
interface Props { graph: GraphData; probabilities: number[]; selected: number; onSelect: (vertex: number) => void; editor?:GraphEditing; }

export default function GraphView({ graph, probabilities, selected, onSelect, editor }: Props) {
  const { t } = useTranslation('components');
  const element = useRef<HTMLDivElement>(null);
  const instance = useRef<Core | null>(null);
  const select = useRef(onSelect);
  select.current = onSelect;
  const editing=useRef(editor);editing.current=editor;
  useEffect(() => {
    if (!element.current) return;
    const cy = cytoscape({
      container: element.current,
      elements: [
        ...graph.vertices.map((vertex) => {const v=editing.current?.vertices.find(v=>v.id===vertex);return { data: { id: String(vertex), label: v?.label??String(vertex), probability: 0 },...(v?{position:{x:v.position[0],y:v.position[1]}}:{}) };}),
        ...graph.edges.map(([source, target]) => ({ data: { id: `e-${source}-${target}`, source: String(source), target: String(target) } })),
      ],
      layout: editing.current ? {name:'preset',fit:false} : { name: 'circle', padding: 70, startAngle: -Math.PI / 2 },
      style: [
        { selector: 'node', style: {
          label: 'data(label)', 'background-color': '#dce7ea', color: '#173441',
          'text-valign': 'center', 'text-halign': 'center', 'font-size': 16, 'font-weight': 600,
          width: 42, height: 42, 'border-width': 2, 'border-color': '#ffffff',
          'overlay-opacity': 0,
        } },
        { selector: 'edge', style: { width: 2, 'line-color': '#c5d5dc', 'curve-style': 'bezier', 'overlay-opacity': 0 } },
        { selector: 'node:selected', style: { 'border-color': '#173441', 'border-width': 4, 'border-opacity': 1 } },
        { selector: 'node.connecting', style: { 'border-color':'#d68d2c','border-width':6 } },
        { selector: 'edge:selected', style: { 'line-color':'#15968e','width':5 } },
      ],
      minZoom: 0.3, maxZoom: 3, selectionType: 'single',
    });
    instance.current = cy;
    cy.on('tap', 'node', (event) => {const e=editing.current;if(e){if(!e.disabled)e.onNode(Number(event.target.id()));}else select.current(Number(event.target.id()));});
    cy.on('tap','edge',event=>{const e=editing.current;if(e&&!e.disabled)e.onEdge([Number(event.target.data('source')),Number(event.target.data('target'))]);});
    cy.on('tap',event=>{const e=editing.current;if(e&&!e.disabled&&event.target===cy)e.onCanvas([event.position.x,event.position.y]);});
    cy.on('dragfree','node',event=>{const e=editing.current;if(e&&!e.disabled){const p=event.target.position();e.onMove(Number(event.target.id()),[p.x,p.y]);}});
    const observer = new ResizeObserver(() => { cy.resize(); if(!editing.current)cy.fit(undefined, 65); });
    observer.observe(element.current);
    return () => { observer.disconnect(); cy.destroy(); instance.current = null; };
  }, [graph.vertices.join(','), graph.edges.map((e) => e.join(',')).join(';'), !!editor]);

  useEffect(()=>{
    const cy=instance.current;if(!cy||!editor)return;
    cy.autoungrabify(editor.disabled||editor.mode!=='select');
    cy.batch(()=>{
      for(const v of editor.vertices){const node=cy.getElementById(String(v.id));node.data('label',v.label);node.position({x:v.position[0],y:v.position[1]});node.toggleClass('connecting',editor.edgeStart===v.id);}
      cy.edges().unselect();if(editor.selectedEdge)cy.getElementById(`e-${editor.selectedEdge[0]}-${editor.selectedEdge[1]}`).select();
    });
  },[editor,graph]);

  useEffect(() => {
    const cy = instance.current;
    if (!cy) return;
    cy.batch(() => graph.vertices.forEach((vertex, index) => {
      const p = Math.max(0, Math.min(1, probabilities[index] ?? 0));
      const blend = (start: number, end: number) => Math.round(start + (end - start) * Math.sqrt(p));
      const node = cy.getElementById(String(vertex));
      node.style({
        'background-color': `rgb(${blend(220, 18)},${blend(231, 151)},${blend(234, 145)})`,
        color: p > 0.3 ? '#ffffff' : '#173441', width: 42 + 23 * Math.sqrt(p), height: 42 + 23 * Math.sqrt(p),
      });
      if (vertex === selected) node.select(); else node.unselect();
    }));
  }, [graph, probabilities, selected]);

  return <div className="graph-stage">
    <div ref={element} className="cytoscape" role="img" aria-label={t('graph.accessibleDescription')} />
    <button className="fit-button" title={t('graph.centerTooltip')} onClick={() => instance.current?.fit(undefined, 65)}>⤢ {t('graph.center')}</button>
    <div className="graph-help">{editor?t(`components:editor.modes.${editor.mode}Help`):t('graph.interactionHelp')}</div>
  </div>;
}
