import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { Matrix, Preset } from './types';
import { matrixCheck } from './matrixValidation';

export const presets: { value: Preset; labelKey: string }[] = [
  { value: 'dft', labelKey: 'presets.dft' }, { value: 'grover', labelKey: 'presets.grover' },
  { value: 'identity', labelKey: 'presets.identity' }, { value: 'hadamard', labelKey: 'presets.hadamard' },
  { value: 'random', labelKey: 'presets.random' },
  { value: 'permutation', labelKey: 'presets.permutation' },
];
const number = (n: number) => Math.abs(n) < 1e-10 ? '0' : Number(n.toFixed(4)).toString();
function formatted([real, imaginary]: [number, number]) {
  if (Math.abs(imaginary) < 1e-10) return number(real);
  if (Math.abs(real) < 1e-10) return `${number(imaginary)}i`;
  return `${number(real)} ${imaginary < 0 ? '−' : '+'} ${number(Math.abs(imaginary))}i`;
}
interface Props { vertex: number; neighbors: number[]; matrix: Matrix; busy: boolean; onApply: (matrix: Matrix) => Promise<boolean>; onPreset: (preset: Preset) => void;
  draftValue?:string;onDraftChange?:(value:string|undefined)=>void; }

export default function MatrixEditor({ vertex, neighbors, matrix, busy, onApply, onPreset, draftValue, onDraftChange }: Props) {
  const { t,i18n } = useTranslation('components');
  const [editing, setEditing] = useState(false);
  const [localDraft, setLocalDraft] = useState('');
  const draft=draftValue??localDraft;
  const setDraft=(text:string)=>{setLocalDraft(text);onDraftChange?.(text);};
  const [error, setError] = useState<string | null>(null);
  // Language changes deliberately do not reset the editor or its draft.
  useEffect(() => { setLocalDraft(JSON.stringify(matrix.length?matrix:Array.from({length:neighbors.length},()=>Array.from({length:neighbors.length},()=>[0,0])), null, 2)); setError(null); setEditing(draftValue!==undefined); }, [matrix, vertex,neighbors.join(',')]);
  const check=matrixCheck(editing?draft:JSON.stringify(matrix),neighbors.length);
  async function apply() {
    const parsed=matrixCheck(draft,neighbors.length);
    if(parsed.error||!parsed.matrix){setError(parsed.error??'shape');return;}
    try {
      setError(null);
      if (await onApply(parsed.matrix)) {setEditing(false);onDraftChange?.(undefined);}
    } catch { setError('apply'); }
  }
  return <>
    <div className="matrix-actions"><label className="sr-only" htmlFor="node-preset">{t('matrix.presetLabel')}</label>
      <select id="node-preset" value="" disabled={busy||neighbors.length===0} onChange={(event) => onPreset(event.target.value as Preset)}>
        <option value="" disabled>{t('matrix.presetPlaceholder')}</option>
        {presets.map((preset) => <option key={preset.value} value={preset.value} disabled={preset.value === 'hadamard' && neighbors.length !== 2}>{t(preset.labelKey)}</option>)}
      </select>
      <button className="text-button" disabled={busy||neighbors.length===0} onClick={() => { if(editing){onDraftChange?.(undefined);setLocalDraft(JSON.stringify(matrix.length?matrix:Array.from({length:neighbors.length},()=>Array.from({length:neighbors.length},()=>[0,0])),null,2));}setEditing(!editing); setError(null); }}>{t(editing ? 'matrix.cancel' : 'matrix.edit')}</button>
    </div>
    {editing ? <div className="matrix-edit">
      {neighbors.length<=8 && <div className="matrix-scroll"><table className="matrix-table"><thead><tr><th>z \ y</th>{neighbors.map(n=><th key={n}>{n}</th>)}</tr></thead><tbody>{neighbors.map((z,i)=><tr key={z}><th>{z}</th>{neighbors.map((y,j)=>{
        let cells:unknown[][]=[];try{const parsed=JSON.parse(draft);if(Array.isArray(parsed))cells=parsed;}catch{/* Keep raw malformed JSON editable. */}
        const cell=cells[i]?.[j];const value=Array.isArray(cell)?`${cell[0]}${Number(cell[1])<0?'':'+'}${cell[1]}i`:String(cell??'');
        return <td key={y}><input className="complex-cell" aria-label={t('matrix.cell',{z,y})} value={value} disabled={busy} onChange={event=>{
          const next=neighbors.map((_,r)=>neighbors.map((__,c)=>cells[r]?.[c]??[0,0]));next[i][j]=event.target.value;setDraft(JSON.stringify(next,null,2));setError(null);
        }} /></td>;
      })}</tr>)}</tbody></table></div>}
      <p className="muted small">{t('matrix.inputHelp')}</p>
      <label htmlFor="matrix-json">{t('matrix.complexEntries')}</label>
      <textarea id="matrix-json" value={draft} onChange={(event) => setDraft(event.target.value)} spellCheck={false} disabled={busy} />
      {error && <p className="field-error" role="alert">{t(`matrix.errors.${error}`, { degree: neighbors.length })}</p>}
      <button className="secondary-button" disabled={busy} onClick={() => void apply()}>{t('matrix.apply')}</button>
    </div> : <div className="matrix-scroll"><table className="matrix-table" aria-label={t('matrix.accessibleDescription', { vertex })}>
      <thead><tr><th scope="col">z \ y</th>{neighbors.map((n) => <th scope="col" key={n}>{n}</th>)}</tr></thead>
      <tbody>{matrix.map((row, i) => <tr key={i}><th scope="row">{neighbors[i]}</th>{row.map((value, j) => <td title={`${value[0]} + (${value[1]})i`} key={j}>{formatted(value)}</td>)}</tr>)}</tbody>
    </table></div>}
    {check.residual!==undefined && <p className={check.error?'field-error':'matrix-valid'}>{t(check.error?'matrix.notUnitary':'matrix.valid')} · max |S†S − I| = {new Intl.NumberFormat(i18n.resolvedLanguage??'en',{notation:'scientific',maximumFractionDigits:3}).format(check.residual)} · ε = 1e-10</p>}
    <div className="matrix-note"><span className="tiny-dot" /> S({vertex}) ∈ U({neighbors.length})<span>{t('matrix.neighbors', { neighbors: neighbors.join(', ') })}</span></div>
    <p className="muted small">{t('matrix.orderingHelp')}</p>
  </>;
}
