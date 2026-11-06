import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import Plotly from 'plotly.js-basic-dist-min';
import { stationaryFixture as result } from './workspaceFixtures';
import StationaryPanel from '../StationaryPanel';
import { setLanguage } from '../i18n';
import type { SimulationRequest } from '../types';

vi.mock('plotly.js-basic-dist-min', () => ({ default: { react: vi.fn(async () => {}), purge: vi.fn(), Plots: { resize: vi.fn(async () => {}) } } }));
vi.mock('../ReducedMarkovGraph', () => ({ default: () => <div data-testid="markov-graph" />,
  atomLabel: (value: number | number[]) => Array.isArray(value) ? `(${value.join(', ')})` : String(value), classColor: () => '#15968e' }));

const experiment: SimulationRequest = { graph: { kind: 'path', size: 3 }, preset: 'identity', scattering: {},
  mode: 'vertex', initial: { kind: 'basis', vertex: 2, edge: [0,1] }, steps: 20, seed: 42 };
// Generic reducible chain: 0 <-> 1, absorbing 2, transient 3 with a 3:1 split.
const calls: { body: Record<string, unknown>; signal?: AbortSignal | null }[] = [];
beforeEach(async () => {
  await setLanguage('en'); calls.length = 0; vi.mocked(Plotly.react).mockClear();
  vi.stubGlobal('fetch', vi.fn(async (_url: string, options: RequestInit) => {
    const body = JSON.parse(String(options.body)); calls.push({body, signal: options.signal});
    return { ok: true, json: async () => ({ ...result, quantum: body.include_density ? {
      class_index: body.stationary_class, density: [[[1,0]]], trace: 1, purity: 1, channel_residual: 0, weights: [0,0,1,0] } : null }) };
  }));
});
async function analyze() {
  await userEvent.click(screen.getByRole('button', { name: 'Analyze long-time dynamics' }));
  await screen.findByText('Family of stationary laws');
}

it('uses actual classes, transient absorption and physical time instead of assumptions about the graph preset', async () => {
  render(<StationaryPanel experiment={experiment} />); await analyze();
  expect(screen.getByText(/periods: 2, 1/)).toBeInTheDocument();
  expect(screen.getByText(/their entire initial mass/)).toBeInTheDocument();
  expect(screen.getByText(/numerical, not certified/)).toBeInTheDocument();
  expect(screen.getByLabelText(/Analysis time/)).toHaveValue('2');
  expect(screen.getByText(/Analysis time/)).toHaveTextContent('t = 3');
  const traces = vi.mocked(Plotly.react).mock.calls[0][1];
  expect(traces[0]).toMatchObject({ x: [1,2,3], y: [0,.75,0] });
  expect(traces[1]).toMatchObject({ y: [0,.375,.25] });
  expect(traces[2]).toMatchObject({ y: [.375,.375,.375] });
});

it('keeps data, class, state and cursor across language changes without any new request', async () => {
  render(<StationaryPanel experiment={experiment} />); await analyze();
  await userEvent.selectOptions(screen.getByLabelText('Stationary distribution to inspect'), '1');
  await userEvent.selectOptions(screen.getByLabelText('State for transitions and probability chart'), '1');
  fireEvent.change(screen.getByLabelText(/Analysis time/), { target: { value: '1' } });
  await act(() => setLanguage('de'));
  expect(screen.getByRole('heading', { name: 'Langzeitdynamik' })).toBeInTheDocument();
  const selects = screen.getAllByRole('combobox');
  expect(selects[0]).toHaveValue('1'); expect(selects[1]).toHaveValue('1');
  expect(screen.getByRole('slider')).toHaveValue('1');
  expect(screen.getAllByText('0,375000', {selector:'strong'})).toHaveLength(2);
  expect(calls).toHaveLength(1);
  const lastProbabilityPlot = vi.mocked(Plotly.react).mock.calls.filter((c) => c[1].length === 3).at(-1)!;
  expect(lastProbabilityPlot[1][0]).toMatchObject({ x: [1,2,3], y: [0,0,.75] });
});

it('reconstructs only the selected class and retains the displayed cursor', async () => {
  render(<StationaryPanel experiment={experiment} />); await analyze();
  fireEvent.change(screen.getByRole('slider'), { target: { value: '1' } });
  await userEvent.selectOptions(screen.getByLabelText('Stationary distribution to inspect'), '1');
  await userEvent.click(screen.getByRole('button', {name:'Reconstruct selected stationary state'}));
  await screen.findByText('Stationary mean density matrix in the physical quantum basis');
  expect(calls[1].body).toMatchObject({ stationary_class: 1, include_density: true });
  expect(screen.getByRole('slider')).toHaveValue('1');
  await userEvent.selectOptions(screen.getByLabelText('Stationary distribution to inspect'), '-1');
  expect(screen.queryByText('Stationary mean density matrix in the physical quantum basis')).not.toBeInTheDocument();
});

it('invalidates old results when the horizon changes and validates support cutoffs locally', async () => {
  render(<StationaryPanel experiment={experiment} />); await analyze();
  fireEvent.change(screen.getByLabelText('Reduced transitions'), {target:{value:'400'}});
  expect(screen.queryByTestId('markov-graph')).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Support cutoff (probability)'), {target:{value:'0.1'}});
  expect(screen.getByRole('button', {name:'Analyze long-time dynamics'})).toBeDisabled();
  expect(screen.getByRole('alert')).toHaveTextContent('between 0 and 1e-6');
  expect(calls).toHaveLength(1);
});

it('aborts stale analysis when the physical experiment changes', async () => {
  let signal: AbortSignal | undefined;
  vi.stubGlobal('fetch', vi.fn((_url: string, options: RequestInit) => { signal = options.signal ?? undefined; return new Promise(() => {}); }));
  const {rerender} = render(<StationaryPanel experiment={experiment} />);
  await userEvent.click(screen.getByRole('button', {name:'Analyze long-time dynamics'}));
  expect(signal?.aborted).toBe(false);
  rerender(<StationaryPanel experiment={{...experiment, preset:'dft'}} />);
  expect(signal?.aborted).toBe(true);
  expect(screen.getByRole('button', {name:'Analyze long-time dynamics'})).toBeEnabled();
});

it('retranslates stationary API errors without repeating the request', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok:false, status:422, json:async () => ({code:'stationary_budget'}) })));
  render(<StationaryPanel experiment={experiment} />);
  await userEvent.click(screen.getByRole('button', {name:'Analyze long-time dynamics'}));
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('state-time entries'));
  await act(() => setLanguage('de'));
  expect(screen.getByRole('alert')).toHaveTextContent('Zustands-Zeit-Einträge');
  expect(fetch).toHaveBeenCalledTimes(1);
});
