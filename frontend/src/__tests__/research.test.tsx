import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import App from '../App';
import ResearchPanels, { VertexControls } from '../ResearchPanels';
import { setLanguage } from '../i18n';
import type { Analysis, Ensemble, Frame, GraphData, SimulationRequest } from '../types';

vi.mock('plotly.js-basic-dist-min', () => ({ default: { react: vi.fn(async () => {}), purge: vi.fn(), Plots: { resize: vi.fn(async () => {}) } } }));
vi.mock('cytoscape', () => ({ default: () => ({ on: vi.fn(), batch: (fn: () => void) => fn(),
  getElementById: () => ({ style: vi.fn(), select: vi.fn(), unselect: vi.fn() }), resize: vi.fn(), fit: vi.fn(), destroy: vi.fn() }) }));

const graph: GraphData = { vertices: [0, 1, 2], edges: [[0, 1], [1, 2], [0, 2]],
  directed_edges: [[0, 1], [0, 2], [1, 0], [1, 2], [2, 0], [2, 1]], neighbors: { 0: [1, 2], 1: [0, 2], 2: [0, 1] },
  scattering: Object.fromEntries([0, 1, 2].map((x) => [x, [[[1, 0], [0, 0]], [[0, 0], [1, 0]]]])), dimension: 6 };
const frame: Frame = { step: 2, edge_probabilities: [.5, 0, 0, 0, .5, 0], vertex_probabilities: [.5, 0, .5],
  purity: 1, trace: 1, measurement: 1, measurement_probability: .5, measurement_probabilities: [.5, .5, 0], stage: 'edge_atom', atom_id: 2, atom_edge: [1, 0] };
const experiment: SimulationRequest = { graph: { kind: 'cycle', size: 3 }, preset: 'dft', scattering: graph.scattering,
  mode: 'trajectory', initial: { kind: 'uniform', edge: [0, 1] }, strategy: 'optimized', steps: 2, seed: 42 };
const ensemble: Ensemble = { model: 'edge', strategy: 'optimized', trajectories: 1000, seed: 42,
  frames: [0, 1, 2].map((step) => ({ step, state_counts: step < 2 ? null : [200, 100, 300, 100, 200, 100], outcome_counts: step ? [300, 400, 300] : null,
    empirical_born_vertices: [.3, .4, .3], empirical_born_edges: [0, .3, .4, 0, .3, 0], exact_state_weights: step < 2 ? null : [1/6, 1/6, 1/6, 1/6, 1/6, 1/6],
    exact_born_vertices: [1/3, 1/3, 1/3], exact_born_edges: [1/6, 1/6, 1/6, 1/6, 1/6, 1/6], state_total_variation: step < 2 ? null : .2, born_vertex_total_variation: 1/15 })),
  selected_outcomes: [[0, 1]], selected_state_ids: [[null, null, 2]] };
const analysis: Analysis = { model: 'edge', orientation: 'column', state_step: 2, stage: 'edge_atom',
  current_density: [[[1, 0]]], after_measurement_density: [[[1, 0]]], atom_id: 0,
  atom_labels: graph.directed_edges, atom_ket: [[.5, .5], [.5, -.5], [0, 0], [0, 0], [0, 0], [0, 0]],
  transition_matrix: Array.from({ length: 6 }, (_, i) => Array.from({ length: 6 }, (__, j) => Number(i === j))),
  next_atom_probabilities: [1, 0, 0, 0, 0, 0], eligible: true, assumptions: 'SIMPLE_STATIC' };
const calls: { url: string; body: SimulationRequest }[] = [];

beforeEach(async () => {
  await setLanguage('en'); calls.length = 0;
  vi.stubGlobal('fetch', vi.fn(async (url: string, options: RequestInit) => {
    const body = JSON.parse(String(options.body)); calls.push({ url, body });
    const data = url.endsWith('/graph') ? graph : url.endsWith('/ensemble') ? ensemble : url.endsWith('/analysis') ? analysis
      : { graph, mode: body.mode, frames: Array.from({ length: body.steps + 1 }, (_, step) => ({ ...frame, step, stage: step ? 'vertex_atom' : 'initial' })), outcomes: [] };
    return { ok: true, json: async () => data };
  }));
});

it('preserves ensemble counts, selected time and inspector outputs across languages without another request', async () => {
  render(<ResearchPanels graph={graph} experiment={experiment} cursor={2} frame={frame} />);
  await userEvent.click(screen.getByRole('button', { name: 'Run ensemble' }));
  await screen.findByText('Vertex Born TV deviation:');
  fireEvent.change(screen.getByLabelText(/Ensemble time step/), { target: { value: '1' } });
  await userEvent.click(screen.getByRole('button', { name: 'Inspect state at t = 2' }));
  await screen.findByText('Reconstructed atom ket');
  await act(() => setLanguage('de'));
  expect(screen.getByText('Rekonstruierter Atom-Ket')).toBeInTheDocument();
  expect(screen.getByLabelText(/Ensemble-Zeitschritt/)).toHaveValue('1');
  expect(screen.getByText('0,066667', { selector: 'strong' })).toBeInTheDocument();
  expect(calls.map((c) => c.url)).toEqual(['/api/ensemble', '/api/analysis']);
  expect(calls[0].body.strategy).toBe('optimized');
});

it('retranslates a new API error without rerunning the experiment', async () => {
  vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 422, json: async () => ({ code: 'ensemble_budget' }) })));
  render(<ResearchPanels graph={graph} experiment={experiment} cursor={0} frame={frame} />);
  await userEvent.click(screen.getByRole('button', { name: 'Run ensemble' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('interactive work budget');
  await act(() => setLanguage('de'));
  expect(screen.getByRole('alert')).toHaveTextContent('interaktive Rechenbudget');
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('clears old ensemble statistics when the trajectory count changes', async () => {
  render(<ResearchPanels graph={graph} experiment={experiment} cursor={2} frame={frame} />);
  await userEvent.click(screen.getByRole('button', { name: 'Run ensemble' }));
  await screen.findByText('Vertex Born TV deviation:');
  fireEvent.change(screen.getByLabelText('Number of trajectories'), { target: { value: '2000' } });
  expect(screen.queryByText('Vertex Born TV deviation:')).not.toBeInTheDocument();
  expect(calls).toHaveLength(1);
});

it('restores applied vertex parameters when returning from another mode', async () => {
  render(<App />);
  await waitFor(() => expect(document.querySelector('.run-button')).toBeEnabled());
  await userEvent.click(screen.getByRole('button', { name: /Vertex Walk/ }));
  await userEvent.click(screen.getByText('Vertex boundary vectors and phases'));
  const omega = Object.fromEntries(graph.vertices.map((x) => [x, [[.6, 0], [0, .8]]]));
  const beta = { 0: .3, 1: -.7, 2: 1.1 };
  fireEvent.change(screen.getByLabelText('Boundary vectors ω (JSON)'), { target: { value: JSON.stringify(omega) } });
  fireEvent.change(screen.getByLabelText('Phases β (JSON)'), { target: { value: JSON.stringify(beta) } });
  await userEvent.click(screen.getByRole('button', { name: 'Apply parameters' }));
  await userEvent.click(screen.getByRole('button', { name: /Unitary/ }));
  await userEvent.click(screen.getByRole('button', { name: /Vertex Walk/ }));
  await userEvent.click(screen.getByText('Vertex boundary vectors and phases'));
  expect(screen.getByLabelText('Boundary vectors ω (JSON)')).toHaveValue(JSON.stringify(omega, null, 2));
  expect(screen.getByLabelText('Phases β (JSON)')).toHaveValue(JSON.stringify(beta, null, 2));
  await userEvent.click(screen.getByRole('button', { name: /Run simulation/ }));
  await waitFor(() => expect(calls.find((c) => c.url === '/api/simulate')).toBeDefined());
  expect(calls.find((c) => c.url === '/api/simulate')!.body.vertex_parameters).toEqual({ omega, beta });
});

it('aborts stale ensemble work when mathematical inputs change', async () => {
  let signal: AbortSignal | undefined;
  vi.stubGlobal('fetch', vi.fn((_url: string, options: RequestInit) => {
    signal = options.signal ?? undefined;
    return new Promise(() => {});
  }));
  const { rerender } = render(<ResearchPanels graph={graph} experiment={experiment} cursor={0} frame={frame} />);
  await userEvent.click(screen.getByRole('button', { name: 'Run ensemble' }));
  expect(signal?.aborted).toBe(false);
  rerender(<ResearchPanels graph={graph} experiment={{ ...experiment, seed: 17 }} cursor={0} frame={frame} />);
  expect(signal?.aborted).toBe(true);
  expect(screen.getByRole('button', { name: 'Run ensemble' })).toBeEnabled();
});

it('preserves complex boundary drafts and localized validation', async () => {
  const apply = vi.fn(); render(<VertexControls graph={graph} busy={false} onApply={apply} />);
  await userEvent.click(screen.getByText('Vertex boundary vectors and phases'));
  fireEvent.change(screen.getByLabelText('Boundary vectors ω (JSON)'), { target: { value: '{invalid' } });
  await userEvent.click(screen.getByRole('button', { name: 'Apply parameters' }));
  await act(() => setLanguage('de'));
  expect(screen.getByLabelText('Randvektoren ω (JSON)')).toHaveValue('{invalid');
  expect(screen.getByRole('alert')).toHaveTextContent('Gültige JSON-Objekte');
  expect(apply).not.toHaveBeenCalled();
});

it('enables the separate vertex model and sends its explicit strategy and initial state', async () => {
  render(<App />);
  await waitFor(() => expect(document.querySelector('.run-button')).toBeEnabled());
  await userEvent.click(screen.getByRole('button', { name: /Vertex Walk/ }));
  await userEvent.selectOptions(screen.getByLabelText('Preparation'), 'maximally_mixed');
  await userEvent.selectOptions(screen.getByLabelText('Execution strategy'), 'reference');
  await userEvent.click(screen.getByRole('button', { name: /Run simulation/ }));
  await waitFor(() => expect(calls.filter((c) => c.url === '/api/simulate')).toHaveLength(1));
  const sent = calls.find((c) => c.url === '/api/simulate')!.body;
  expect(sent.mode).toBe('vertex'); expect(sent.strategy).toBe('reference');
  expect(sent.initial.kind).toBe('maximally_mixed');
  expect(screen.getByRole('button', { name: 'Edges' })).toBeDisabled();
});

it('plays one requested step at a time, preserves playback on language change, and pauses without future draws', async () => {
  render(<App />);
  await waitFor(() => expect(document.querySelector('.run-button')).toBeEnabled());
  await userEvent.click(screen.getByRole('button', { name: /Trajectory/ }));
  vi.useFakeTimers();
  try {
    fireEvent.click(screen.getByRole('button', { name: 'Play' }));
    await act(() => setLanguage('de'));
    expect(calls.filter((c) => c.url === '/api/simulate')).toHaveLength(0);
    await act(() => vi.advanceTimersByTimeAsync(600));
    expect(calls.filter((c) => c.url === '/api/simulate').map((c) => c.body.steps)).toEqual([1]);
    fireEvent.click(screen.getByRole('button', { name: 'Pausieren' }));
    await act(() => vi.advanceTimersByTimeAsync(1800));
    expect(calls.filter((c) => c.url === '/api/simulate')).toHaveLength(1);
  } finally { vi.useRealTimers(); }
});
