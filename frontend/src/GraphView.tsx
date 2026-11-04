import { useEffect, useRef } from 'react';
import cytoscape, { type Core } from 'cytoscape';
import { useTranslation } from 'react-i18next';
import type { GraphData } from './types';

interface Props { graph: GraphData; probabilities: number[]; selected: number; onSelect: (vertex: number) => void; }

export default function GraphView({ graph, probabilities, selected, onSelect }: Props) {
  const { t } = useTranslation('components');
  const element = useRef<HTMLDivElement>(null);
  const instance = useRef<Core | null>(null);
  const select = useRef(onSelect);
  select.current = onSelect;
  useEffect(() => {
    if (!element.current) return;
    const cy = cytoscape({
      container: element.current,
      elements: [
        ...graph.vertices.map((vertex) => ({ data: { id: String(vertex), label: String(vertex), probability: 0 } })),
        ...graph.edges.map(([source, target]) => ({ data: { id: `e-${source}-${target}`, source: String(source), target: String(target) } })),
      ],
      layout: { name: 'circle', padding: 70, startAngle: -Math.PI / 2 },
      style: [
        { selector: 'node', style: {
          label: 'data(label)', 'background-color': '#dce7ea', color: '#173441',
          'text-valign': 'center', 'text-halign': 'center', 'font-size': 16, 'font-weight': 600,
          width: 42, height: 42, 'border-width': 2, 'border-color': '#ffffff',
          'overlay-opacity': 0,
        } },
        { selector: 'edge', style: { width: 2, 'line-color': '#c5d5dc', 'curve-style': 'bezier', 'overlay-opacity': 0 } },
        { selector: 'node:selected', style: { 'border-color': '#173441', 'border-width': 4, 'border-opacity': 1 } },
      ],
      minZoom: 0.3, maxZoom: 3, selectionType: 'single',
    });
    instance.current = cy;
    cy.on('tap', 'node', (event) => select.current(Number(event.target.id())));
    const observer = new ResizeObserver(() => { cy.resize(); cy.fit(undefined, 65); });
    observer.observe(element.current);
    return () => { observer.disconnect(); cy.destroy(); instance.current = null; };
  }, [graph.vertices.join(','), graph.edges.map((e) => e.join(',')).join(';')]);

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
    <div className="graph-help">{t('graph.interactionHelp')}</div>
  </div>;
}
