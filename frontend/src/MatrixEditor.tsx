import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { Matrix, Preset } from './types';

export const presets: { value: Preset; labelKey: string }[] = [
  { value: 'dft', labelKey: 'presets.dft' }, { value: 'grover', labelKey: 'presets.grover' },
  { value: 'identity', labelKey: 'presets.identity' }, { value: 'hadamard', labelKey: 'presets.hadamard' },
  { value: 'random', labelKey: 'presets.random' },
];
const number = (n: number) => Math.abs(n) < 1e-10 ? '0' : Number(n.toFixed(4)).toString();
function formatted([real, imaginary]: [number, number]) {
  if (Math.abs(imaginary) < 1e-10) return number(real);
  if (Math.abs(real) < 1e-10) return `${number(imaginary)}i`;
  return `${number(real)} ${imaginary < 0 ? '−' : '+'} ${number(Math.abs(imaginary))}i`;
}
interface Props { vertex: number; neighbors: number[]; matrix: Matrix; busy: boolean; onApply: (matrix: Matrix) => Promise<boolean>; onPreset: (preset: Preset) => void; }

export default function MatrixEditor({ vertex, neighbors, matrix, busy, onApply, onPreset }: Props) {
  const { t } = useTranslation('components');
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  const [error, setError] = useState<'json' | 'shape' | 'apply' | null>(null);
  // Language changes deliberately do not reset the editor or its draft.
  useEffect(() => { setDraft(JSON.stringify(matrix, null, 2)); setError(null); setEditing(false); }, [matrix, vertex]);
  async function apply() {
    let parsed: unknown;
    try {
      parsed = JSON.parse(draft);
    } catch {
      setError('json');
      return;
    }
    if (!Array.isArray(parsed) || parsed.length !== neighbors.length || parsed.some((row) => !Array.isArray(row) || row.length !== neighbors.length || row.some((value: unknown) => !Array.isArray(value) || value.length !== 2 || value.some((v: unknown) => typeof v !== 'number' || !Number.isFinite(v))))) {
      setError('shape');
      return;
    }
    try {
      setError(null);
      if (await onApply(parsed as Matrix)) setEditing(false);
    } catch { setError('apply'); }
  }
  return <>
    <div className="matrix-actions"><label className="sr-only" htmlFor="node-preset">{t('matrix.presetLabel')}</label>
      <select id="node-preset" value="" disabled={busy} onChange={(event) => onPreset(event.target.value as Preset)}>
        <option value="" disabled>{t('matrix.presetPlaceholder')}</option>
        {presets.map((preset) => <option key={preset.value} value={preset.value} disabled={preset.value === 'hadamard' && neighbors.length !== 2}>{t(preset.labelKey)}</option>)}
      </select>
      <button className="text-button" disabled={busy} onClick={() => { setEditing(!editing); setError(null); }}>{t(editing ? 'matrix.cancel' : 'matrix.edit')}</button>
    </div>
    {editing ? <div className="matrix-edit">
      <label htmlFor="matrix-json">{t('matrix.complexEntries')}</label>
      <textarea id="matrix-json" value={draft} onChange={(event) => setDraft(event.target.value)} spellCheck={false} disabled={busy} />
      {error && <p className="field-error" role="alert">{t(`matrix.errors.${error}`, { degree: neighbors.length })}</p>}
      <button className="secondary-button" disabled={busy} onClick={() => void apply()}>{t('matrix.apply')}</button>
    </div> : <div className="matrix-scroll"><table className="matrix-table" aria-label={t('matrix.accessibleDescription', { vertex })}>
      <thead><tr><th scope="col">z \ y</th>{neighbors.map((n) => <th scope="col" key={n}>{n}</th>)}</tr></thead>
      <tbody>{matrix.map((row, i) => <tr key={i}><th scope="row">{neighbors[i]}</th>{row.map((value, j) => <td title={`${value[0]} + (${value[1]})i`} key={j}>{formatted(value)}</td>)}</tr>)}</tbody>
    </table></div>}
    <div className="matrix-note"><span className="tiny-dot" /> S({vertex}) ∈ U({neighbors.length})<span>{t('matrix.neighbors', { neighbors: neighbors.join(', ') })}</span></div>
    <p className="muted small">{t('matrix.orderingHelp')}</p>
  </>;
}
