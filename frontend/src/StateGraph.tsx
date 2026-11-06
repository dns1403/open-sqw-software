import { useTranslation } from 'react-i18next';
import type { GraphData } from './types';
import type { EditorVertex } from './customGraph';
import { formatNumber } from './i18n/format';

/** A read-only probability view; editor layout and all scientific values live in App. */
export default function StateGraph({ graph, probabilities, vertices, selected, onSelect }: {
  graph: GraphData; probabilities: number[]; vertices?: EditorVertex[]; selected: number; onSelect: (id: number) => void;
}) {
  const { t, i18n } = useTranslation('app');
  const raw = graph.vertices.map((id, i) => vertices?.find(v => v.id === id)?.position ?? [Math.cos(i * 2 * Math.PI / graph.vertices.length - Math.PI / 2), Math.sin(i * 2 * Math.PI / graph.vertices.length - Math.PI / 2)]);
  const xs = raw.map(p => p[0]), ys = raw.map(p => p[1]);
  const minX = Math.min(...xs), minY = Math.min(...ys), width = Math.max(...xs) - minX, height = Math.max(...ys) - minY;
  const scale = Math.min(310 / (width || 1), 220 / (height || 1));
  const positions = raw.map(([x, y]) => [200 + (x - minX - width / 2) * scale, 150 + (y - minY - height / 2) * scale]);
  return <section className="panel state-graph"><div className="panel-header"><h2>{t('workspace.graphPreview')}</h2><span className="pill">P(x)</span></div>
    <svg viewBox="0 0 400 300" role="group" aria-label={t('workspace.graphPreview')}>
      {graph.edges.map(([a, b]) => { const [x1, y1] = positions[graph.vertices.indexOf(a)], [x2, y2] = positions[graph.vertices.indexOf(b)]; return <line key={`${a}-${b}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#bfd2d9" strokeWidth="2" />; })}
      {graph.vertices.map((id, i) => { const [x, y] = positions[i], p = probabilities[i] ?? 0, label = vertices?.find(v => v.id === id)?.label ?? String(id); return <g key={id} role="button" tabIndex={0} aria-pressed={selected === id} aria-label={t('workspace.selectVertex', { vertex: label, probability: formatNumber(p, i18n.resolvedLanguage ?? 'en', 5) })} onClick={() => onSelect(id)} onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect(id); } }}>
        <circle cx={x} cy={y} r={17 + 9 * Math.sqrt(Math.max(0, Math.min(1, p)))} fill={p > .01 ? '#238f84' : '#e1ebee'} stroke={id === selected ? '#163e4c' : '#fff'} strokeWidth={id === selected ? 3 : 2} />
        <text x={x} y={y} dy=".35em" textAnchor="middle" fill={p > .01 ? '#fff' : '#173f4c'} fontSize="12">{label.length > 8 ? label.slice(0, 7) + '…' : label}</text>
      </g>; })}
    </svg><p>{t('workspace.graphPreviewHint')}</p>
  </section>;
}
