import { visit, reveal } from './workspaceActions';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import App from '../App';
import { featureGroups, sectionFor } from '../Workspace';
import { TOUR_STORAGE_KEY } from '../onboarding';
import { stationaryFixture, statisticsFixture } from './workspaceFixtures';
import i18n from '../i18n';
import ResearchPanels, { VertexControls } from '../ResearchPanels';
import { setLanguage } from '../i18n';
import type { Analysis, Ensemble, Frame, GraphData, SimulationRequest } from '../types';

vi.mock('plotly.js-basic-dist-min', () => ({ default: { react: vi.fn(async () => {}), purge: vi.fn(), Plots: { resize: vi.fn(async () => {}) } } }));
vi.mock('../ReducedMarkovGraph', () => ({ default: () => <div data-testid="markov-graph" />,
  atomLabel: (value: number | number[]) => Array.isArray(value) ? `(${value.join(', ')})` : String(value), classColor: () => '#15968e' }));
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
  localStorage.removeItem(TOUR_STORAGE_KEY);
  HTMLElement.prototype.scrollIntoView = vi.fn();
  vi.stubGlobal('fetch', vi.fn(async (url: string, options: RequestInit) => {
    const body = JSON.parse(String(options.body)); calls.push({ url, body });
    const data = url.endsWith('/graph') ? graph : url.endsWith('/ensemble') ? ensemble : url.endsWith('/analysis') ? analysis : url.endsWith('/stationary') ? stationaryFixture : url.endsWith('/statistics') ? statisticsFixture
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
  render(<App />);visit('simulation');
  await waitFor(() => expect(document.querySelector('.run-button')).toBeEnabled());
  await userEvent.click(screen.getByRole('button', { name: /Vertex Walk/ }));
  if(document.getElementById('workspace-navigation'))reveal(screen.getByText('Vertex boundary vectors and phases'));await userEvent.click(screen.getByText('Vertex boundary vectors and phases'));
  const omega = Object.fromEntries(graph.vertices.map((x) => [x, [[.6, 0], [0, .8]]]));
  const beta = { 0: .3, 1: -.7, 2: 1.1 };
  fireEvent.change(screen.getByLabelText('Boundary vectors ω (JSON)'), { target: { value: JSON.stringify(omega) } });
  fireEvent.change(screen.getByLabelText('Phases β (JSON)'), { target: { value: JSON.stringify(beta) } });
  await userEvent.click(screen.getByRole('button', { name: 'Apply parameters' }));
  visit('simulation');await userEvent.click(screen.getByRole('button', { name: /Unitary/ }));
  await userEvent.click(screen.getByRole('button', { name: /Vertex Walk/ }));
  if(document.getElementById('workspace-navigation'))reveal(screen.getByText('Vertex boundary vectors and phases'));await userEvent.click(screen.getByText('Vertex boundary vectors and phases'));
  expect(screen.getByLabelText('Boundary vectors ω (JSON)')).toHaveValue(JSON.stringify(omega, null, 2));
  expect(screen.getByLabelText('Phases β (JSON)')).toHaveValue(JSON.stringify(beta, null, 2));
  visit('simulation');await userEvent.click(screen.getByRole('button', { name: /Run simulation/ }));
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
  if(document.getElementById('workspace-navigation'))reveal(screen.getByText('Vertex boundary vectors and phases'));await userEvent.click(screen.getByText('Vertex boundary vectors and phases'));
  fireEvent.change(screen.getByLabelText('Boundary vectors ω (JSON)'), { target: { value: '{invalid' } });
  await userEvent.click(screen.getByRole('button', { name: 'Apply parameters' }));
  await act(() => setLanguage('de'));
  expect(screen.getByLabelText('Randvektoren ω (JSON)')).toHaveValue('{invalid');
  expect(screen.getByRole('alert')).toHaveTextContent('Gültige JSON-Objekte');
  expect(apply).not.toHaveBeenCalled();
});

it('enables the separate vertex model and sends its explicit strategy and initial state', async () => {
  render(<App />);visit('simulation');
  await waitFor(() => expect(document.querySelector('.run-button')).toBeEnabled());
  await userEvent.click(screen.getByRole('button', { name: /Vertex Walk/ }));
  await userEvent.selectOptions(screen.getByLabelText('Preparation'), 'maximally_mixed');
  await userEvent.selectOptions(screen.getByLabelText('Execution strategy'), 'reference');
  visit('simulation');await userEvent.click(screen.getByRole('button', { name: /Run simulation/ }));
  await waitFor(() => expect(calls.filter((c) => c.url === '/api/simulate')).toHaveLength(1));
  const sent = calls.find((c) => c.url === '/api/simulate')!.body;
  expect(sent.mode).toBe('vertex'); expect(sent.strategy).toBe('reference');
  expect(sent.initial.kind).toBe('maximally_mixed');
  expect(screen.getByRole('button', { name: 'Edges' })).toBeDisabled();
});

it('plays one requested step at a time, preserves playback on language change, and pauses without future draws', async () => {
  render(<App />);visit('simulation');
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

it('starts on Overview and routes every feature directory destination without scientific requests', async () => {
  render(<App />);
  await waitFor(() => expect(document.querySelector('.run-button')).toBeEnabled());
  expect(screen.getByRole('heading', { level: 1, name: 'Overview' })).toBeVisible();
  expect(screen.queryByRole('button', { name: /^▶\s*Run simulation$/ })).not.toBeInTheDocument();
  const count = calls.length;
  for (const group of featureGroups) {
    const label = i18n.t(`app:workspace.destinations.${group.destination}`);
    await userEvent.click(screen.getByRole('button', { name: label }));
    expect(screen.getByRole('heading', { level: 1, name: i18n.t(`app:workspace.nav.${sectionFor(group.destination)}`) })).toBeVisible();
    const target = document.querySelector(`[data-destination="${group.destination}"]`);
    if (target) expect(target).toBeVisible();
    visit('overview');
  }
  expect(calls).toHaveLength(count);
});

it('preserves ensemble and inspector results, their selections and timeline across workspaces and language', async () => {
  render(<App />); visit('simulation');
  await waitFor(() => expect(document.querySelector('.run-button')).toBeEnabled());
  await userEvent.click(screen.getByRole('button', { name: /^ψ\s*Trajectory$/ }));
  fireEvent.change(screen.getByLabelText('Steps'), { target: { value: '2' } });
  await userEvent.click(screen.getByRole('button', { name: /^▶\s*Run simulation$/ }));
  await waitFor(() => expect(document.getElementById('time-slider')).toHaveValue('2'));
  visit('trajectories');
  await userEvent.click(screen.getByRole('button', { name: 'Run ensemble' }));
  await screen.findByText('Vertex Born TV deviation:');
  fireEvent.change(screen.getByLabelText(/Ensemble time step/), { target: { value: '1' } });
  visit('analysis');
  await userEvent.click(screen.getByRole('button', { name: 'Inspect state at t = 2' }));
  await screen.findByText('Reconstructed atom ket');
  const count = calls.length;
  visit('graph'); visit('overview'); visit('learn'); visit('trajectories');
  expect(screen.getByLabelText(/Ensemble time step/)).toHaveValue('1');
  expect(screen.getByText('Vertex Born TV deviation:')).toBeVisible();
  visit('analysis');
  expect(screen.getByText('Reconstructed atom ket')).toBeVisible();
  await act(() => setLanguage('de'));
  expect(screen.getByText('Rekonstruierter Atom-Ket')).toBeVisible();
  expect(calls).toHaveLength(count);
  expect(document.getElementById('time-slider')).toHaveValue('2');
});

it('retains stationary and statistics results and inputs when switching analysis tabs', async () => {
  render(<App />); visit('simulation');
  await waitFor(() => expect(document.querySelector('.run-button')).toBeEnabled());
  await userEvent.click(screen.getByRole('button', { name: /^Φ\s*Open$/ }));
  visit('analysis');
  await userEvent.click(screen.getByRole('button', { name: 'Long-time dynamics' }));
  await userEvent.click(screen.getByRole('button', { name: 'Analyze long-time dynamics' }));
  await screen.findByLabelText('Stationary distribution to inspect');
  await userEvent.selectOptions(screen.getByLabelText('Stationary distribution to inspect'), '1');
  fireEvent.change(screen.getByLabelText(/Analysis time/), { target: { value: '1' } });
  await userEvent.click(screen.getByRole('button', { name: 'Statistics & uncertainty' }));
  fireEvent.change(screen.getByLabelText('Trajectory seed'), { target: { value: '77' } });
  await userEvent.click(screen.getByRole('button', { name: 'Analyze trajectory statistics' }));
  await screen.findByText('Selected class · asymptotic statistics');
  const count = calls.length;
  visit('graph'); visit('analysis');
  expect(screen.getByText('Selected class · asymptotic statistics')).toBeVisible();
  expect(screen.getByLabelText('Trajectory seed')).toHaveValue(77);
  await userEvent.click(screen.getByRole('button', { name: 'Long-time dynamics' }));
  expect(screen.getByLabelText('Stationary distribution to inspect')).toHaveValue('1');
  expect(screen.getByLabelText(/Analysis time/)).toHaveValue('1');
  await act(() => setLanguage('de'));
  expect(calls).toHaveLength(count);
});

it('keeps an invalid matrix draft and readiness status when navigating without applying it', async () => {
  render(<App />); visit('graph');
  await waitFor(() => expect(document.querySelector('.run-button')).toBeEnabled());
  await userEvent.click(screen.getByRole('button', { name: 'Edit' }));
  fireEvent.change(document.getElementById('matrix-json')!, { target: { value: '{unfinished' } });
  const count = calls.length;
  visit('overview'); visit('simulation');
  expect(screen.getByRole('button', { name: /^▶\s*Run simulation$/ })).toBeDisabled();
  visit('learn'); visit('graph');
  expect(document.getElementById('matrix-json')).toHaveValue('{unfinished');
  expect(screen.getByRole('button', { name: 'Validate & apply matrix' })).toBeVisible();
  expect(calls).toHaveLength(count);
});

it('does not abort in-flight scientific work on navigation', async () => {
  render(<App />); visit('simulation');
  await waitFor(() => expect(document.querySelector('.run-button')).toBeEnabled());
  let resolve!: (reply: unknown) => void;
  let signal: AbortSignal | null | undefined;
  vi.stubGlobal('fetch', vi.fn((_url: string, options: RequestInit) => { signal = options.signal; return new Promise(done => { resolve = done; }); }));
  await userEvent.click(screen.getByRole('button', { name: /^▶\s*Run simulation$/ }));
  visit('graph'); visit('overview');
  expect(signal?.aborted).toBe(false);
  await act(async () => resolve({ ok: true, json: async () => ({ graph, mode: 'unitary', frames: [{ ...frame, step: 0 }, { ...frame, step: 1 }], outcomes: [] }) }));
  visit('simulation');
  expect(document.getElementById('time-slider')).toHaveValue('1');
  expect(fetch).toHaveBeenCalledTimes(1);
});

it('runs the real Driver.js introduction, retains its step across languages, skips and restarts without requests', async () => {
  render(<App />);
  await waitFor(() => expect(document.querySelector('.run-button')).toBeEnabled());
  const count = calls.length;
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  await userEvent.click(screen.getAllByRole('button', { name: 'Start tour' })[0]);
  expect(screen.getByRole('dialog', { name: 'Welcome to your laboratory' })).toBeVisible();
  expect(screen.getByText('Step 1 of 7')).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: 'Next' }));
  await userEvent.click(screen.getByRole('button', { name: 'Tour in German' }));
  expect(screen.getByText('Schritt 2 von 7')).toBeVisible();
  await userEvent.click(screen.getByRole('button', { name: 'Zurück' }));
  expect(screen.getByText('Schritt 1 von 7')).toBeVisible();
  await userEvent.keyboard('{Escape}');
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(localStorage.getItem(TOUR_STORAGE_KEY)).toBe('seen');
  await act(() => setLanguage('en'));
  visit('graph'); visit('overview');
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  await userEvent.click(screen.getByRole('button', { name: 'Restart introduction' }));
  expect(screen.getByText('Step 1 of 7')).toBeVisible();
  for (let index = 1; index < 7; index++) await userEvent.click(screen.getByRole('button', { name: 'Next' }));
  await userEvent.click(screen.getByRole('button', { name: 'Finish' }));
  expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  expect(calls).toHaveLength(count);
});

it('offers a safe fallback for unavailable tutorial targets and completes every contextual tutorial', async () => {
  render(<App />); visit('learn');
  await waitFor(() => expect(document.querySelector('.run-button')).toBeEnabled());
  const count = calls.length;
  for (const [title, length] of [['Your first quantum walk', 6], ['Understand a quantum trajectory', 6], ['Explore long-time behavior', 5]] as const) {
    visit('learn');
    const card = screen.getByRole('heading', { name: title }).closest('article')!;
    await userEvent.click(card.querySelector('button')!);
    for (let index = 1; index < length; index++) await userEvent.click(screen.getByRole('button', { name: 'Next' }));
    if (title !== 'Your first quantum walk') expect(screen.getByText(/This control is currently unavailable/)).toBeVisible();
    await userEvent.click(screen.getByRole('button', { name: 'Finish' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  }
  expect(calls).toHaveLength(count);
});

it('opens practice in an independent tab and never persists experiment drafts', async () => {
  render(<App />); visit('learn');
  await waitFor(() => expect(document.querySelector('.run-button')).toBeEnabled());
  const practice = screen.getByRole('link', { name: /Open practice experiment/ });
  expect(practice).toHaveAttribute('target', '_blank');
  expect(practice).toHaveAttribute('rel', 'noopener noreferrer');
  expect(practice).toHaveAttribute('href', '?example=first-walk');
  expect(Object.keys(localStorage).filter(key => key !== TOUR_STORAGE_KEY && !key.includes('language'))).toEqual([]);
});
