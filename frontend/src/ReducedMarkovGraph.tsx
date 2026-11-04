import { useEffect, useRef } from 'react';
import cytoscape, { type Core } from 'cytoscape';
import { useTranslation } from 'react-i18next';
import { formatNumber } from './i18n/format';
import type { StationaryResult } from './types';

export const classColor = (id: number) => `hsl(${(id * 137.508 + 170) % 360}, 52%, 39%)`;
export const atomLabel = (label: number | [number, number]) => Array.isArray(label) ? `(${label[0]}, ${label[1]})` : String(label);

export default function ReducedMarkovGraph({ result, weights, selected, onSelect }: {
  result: StationaryResult; weights: number[]; selected: number; onSelect: (id: number) => void;
}) {
  const { t, i18n } = useTranslation('stationary');
  const element = useRef<HTMLDivElement>(null);
  const instance = useRef<Core | null>(null);
  const select = useRef(onSelect); select.current = onSelect;
  const retained = result.transitions.filter((edge) => edge.analysis_probability > 0);
  const visible = result.atom_labels.length <= 80 ? result.atom_labels.map((_, i) => i)
    : [...new Set([selected, ...retained.filter((e) => e.source === selected).map((e) => e.target)])].sort((a,b) => a-b);
  const visibleKey = visible.join(',');
  useEffect(() => {
    if (!element.current) return;
    const ids = new Set(visible);
    const edges = retained.filter((e) => ids.has(e.source) && ids.has(e.target));
    const cy = cytoscape({ container: element.current,
      elements: [
        ...visible.map((id) => ({ data: { id: `m${id}`, index: id, label: atomLabel(result.atom_labels[id]),
          color: classColor(result.membership[id]), transient: Number(!result.classes[result.membership[id]].closed) } })),
        ...edges.map((e) => ({ data: { id: `t${e.source}-${e.target}`, source: `m${e.source}`, target: `m${e.target}`,
          probability: e.probability, showLabel: edges.length <= 30, label: '' } })),
      ],
      layout: { name: 'circle', padding: 65 }, selectionType: 'single', minZoom: .15, maxZoom: 4,
      style: [
        { selector: 'node', style: { label: 'data(label)', 'background-color': 'data(color)', color: '#fff',
          'font-size': 11, 'font-weight': 600, 'text-valign': 'center', 'border-width': 2, 'border-color': '#fff', width: 36, height: 36 } },
        { selector: 'node[transient = 1]', style: { 'border-style': 'dashed', 'border-color': '#173441', 'border-width': 3 } },
        { selector: 'node:selected', style: { 'border-color': '#111c24', 'border-width': 5 } },
        { selector: 'edge', style: { 'curve-style': 'bezier', 'target-arrow-shape': 'triangle',
          'target-arrow-color': '#a9bcc5', 'line-color': '#a9bcc5', width: 1.4,
          label: 'data(label)', 'font-size': 9, color: '#33535f', 'text-background-color': '#fff', 'text-background-opacity': .8 } },
      ],
    });
    instance.current = cy;
    cy.on('tap', 'node', (event) => select.current(Number(event.target.data('index'))));
    const observer = new ResizeObserver(() => { cy.resize(); cy.fit(undefined, 55); });
    observer.observe(element.current);
    return () => { observer.disconnect(); cy.destroy(); instance.current = null; };
    // Stable scientific data/visible IDs preserve the graph through language changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result, visibleKey]);
  useEffect(() => {
    const cy = instance.current;
    if (!cy) return;
    cy.batch(() => {
      cy.nodes().forEach((node) => {
        const id = Number(node.data('index'));
        const size = 34 + 32 * Math.sqrt(weights[id] ?? 0);
        node.style({ width: size, height: size });
        if (id === selected) node.select(); else node.unselect();
      });
      cy.edges().forEach((edge) => {
        const outgoing = edge.data('source') === `m${selected}`;
        edge.style({ 'line-color': outgoing ? '#122f3d' : '#a9bcc5', 'target-arrow-color': outgoing ? '#122f3d' : '#a9bcc5', width: outgoing ? 3 : 1.4 });
        edge.data('label', edge.data('showLabel') || outgoing ? formatNumber(edge.data('probability'), i18n.resolvedLanguage ?? 'en', 3) : '');
      });
    });
  }, [result, weights, selected, visibleKey, i18n.resolvedLanguage]);
  return <><div className="markov-graph-stage"><div ref={element} className="markov-cytoscape" role="img" aria-label={t('graphDescription')} />
    <button className="fit-button" onClick={() => instance.current?.fit(undefined, 55)}>{t('center')}</button></div>
    {result.atom_labels.length > 80 && <p className="muted small">{t('localGraph')}</p>}</>;
}
