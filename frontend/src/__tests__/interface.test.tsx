import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
import MatrixEditor from '../MatrixEditor';
import ProbabilityPlot from '../ProbabilityPlot';
import i18n, { setLanguage } from '../i18n';
import type { Frame, GraphData, GraphKind, Matrix, SimulationRequest } from '../types';

const canvas = vi.hoisted(() => ({
  plot: vi.fn(() => Promise.resolve()),
  graph: vi.fn(),
}));

vi.mock('plotly.js-basic-dist-min', () => ({ default: {
  react: canvas.plot, purge: vi.fn(), Plots: { resize: vi.fn(() => Promise.resolve()) },
} }));

vi.mock('cytoscape', () => ({ default: (...args: unknown[]) => {
  canvas.graph(...args);
  const node = { style: vi.fn(), select: vi.fn(), unselect: vi.fn() };
  return {
    on: vi.fn(), batch: (fn: () => void) => fn(), getElementById: () => node,
    resize: vi.fn(), fit: vi.fn(), destroy: vi.fn(),
  };
} }));

// These deterministic API fixtures test the presentation contract. Numerical
// correctness belongs to the independent Python suite; no simulator is
// reimplemented or translated here.
function graphFixture(kind: GraphKind, size: number): GraphData {
  const vertices = Array.from({ length: size }, (_, i) => i);
  const edges: [number, number][] = [];
  for (let x = 0; x < size; x++) {
    for (let y = x + 1; y < size; y++) {
      if (kind === 'complete' || (kind === 'star' ? x === 0 : y === x + 1 || (kind === 'cycle' && x === 0 && y === size - 1))) edges.push([x, y]);
    }
  }
  const neighbors = Object.fromEntries(vertices.map((x) => [String(x), edges
    .filter(([a, b]) => a === x || b === x).map(([a, b]) => a === x ? b : a).sort((a, b) => a - b)]));
  const directed_edges = vertices.flatMap((x) => neighbors[String(x)].map((y): [number, number] => [x, y]));
  const scattering: Record<string, Matrix> = Object.fromEntries(vertices.map((x) => [String(x), neighbors[String(x)]
    .map((_, i) => neighbors[String(x)].map((__, j): [number, number] => [Number(i === j), 0]))]));
  return { vertices, edges, directed_edges, neighbors, scattering, dimension: directed_edges.length };
}

function framesFixture(graph: GraphData, steps: number): Frame[] {
  return Array.from({ length: steps + 1 }, (_, step) => ({
    step,
    edge_probabilities: graph.directed_edges.map((_, i) => Number(i === step % graph.dimension)),
    vertex_probabilities: graph.vertices.map((_, i) => Number(i === step % graph.vertices.length)),
    purity: step ? 0.75 : 1, trace: 1,
    measurement: step ? graph.vertices[(step - 1) % graph.vertices.length] : null,
    measurement_probability: step ? 0.5 : null,
    measurement_probabilities: step ? graph.vertices.map(() => 1 / graph.vertices.length) : null,
  }));
}

function field<T extends HTMLElement>(id: string): T {
  const node = document.getElementById(id);
  if (!node) throw new Error(`Missing control #${id}`);
  return node as T;
}

function button(selector: string): HTMLButtonElement {
  const node = document.querySelector<HTMLButtonElement>(selector);
  if (!node) throw new Error(`Missing button ${selector}`);
  return node;
}

async function switchTo(language: 'en' | 'de') {
  await userEvent.click(button(`button[lang="${language}"]`));
  await waitFor(() => expect(document.documentElement.lang).toBe(language));
}

const requests: { route: string; body: Record<string, unknown> }[] = [];
let rejectSimulation = false;

beforeEach(async () => {
  await setLanguage('en');
  localStorage.clear();
  requests.length = 0;
  rejectSimulation = false;
  vi.stubGlobal('fetch', vi.fn(async (url: string, options: RequestInit) => {
    const body = JSON.parse(String(options.body));
    requests.push({ route: url, body: structuredClone(body) });
    if (url === '/api/graph') return { ok: true, status: 200, json: async () => graphFixture(body.kind, body.size) };
    if (url === '/api/scattering/validate') return { ok: true, status: 200, json: async () => ({matrix:body.matrix,residual:0}) };
    if (url === '/api/simulate') {
      if (rejectSimulation) return { ok: false, status: 422, json: async () => ({ detail: 'Backend diagnostic', code: 'matrix_not_unitary', params: { vertex: 1 } }) };
      const request = body as SimulationRequest;
      const graph = { ...graphFixture(request.graph.kind, request.graph.size), scattering: request.scattering };
      return { ok: true, status: 200, json: async () => ({ graph, mode: request.mode, frames: framesFixture(graph, request.steps), outcomes: [] }) };
    }
    throw new Error(`Unexpected test API request: ${url}`);
  }));
});

describe('live experiment language switching', () => {
  it('preserves graph, selected matrix, initial state, seed and simulation progress without a new request', async () => {
    render(<App />);
    await waitFor(() => expect(field<HTMLSelectElement>('initial-edge').options).toHaveLength(12));
    await userEvent.selectOptions(field('graph-kind'), 'path');
    await waitFor(() => expect(field<HTMLSelectElement>('initial-edge').options).toHaveLength(10));
    await userEvent.selectOptions(field('graph-size'), '3');
    await waitFor(() => expect(field<HTMLSelectElement>('initial-edge').options).toHaveLength(4));
    await userEvent.selectOptions(field('selected-node'), '1');
    await userEvent.selectOptions(field('initial-kind'), 'uniform');
    fireEvent.change(field('seed'), { target: { value: '17' } });
    fireEvent.blur(field('seed'));
    await waitFor(() => expect(requests.at(-1)?.body.seed).toBe(17));
    await waitFor(() => expect(button('.run-button')).toBeEnabled());
    // A seed update recreates the graph by design. Select and edit afterward.
    await userEvent.selectOptions(field('selected-node'), '1');
    await userEvent.click(screen.getByRole('button', { name: /^Φ\s*Open$/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Edit' }));
    const custom = '[[[1,0],[0,0]],[[0,0],[0,1]]]';
    fireEvent.change(field('matrix-json'), { target: { value: custom } });
    await userEvent.click(screen.getByRole('button', { name: 'Validate & apply matrix' }));
    await waitFor(() => expect(document.getElementById('matrix-json')).toBeNull());
    fireEvent.change(field('steps'), { target: { value: '4' } });
    await userEvent.click(button('.run-button'));
    await waitFor(() => expect(field<HTMLInputElement>('time-slider').value).toBe('4'));
    fireEvent.change(field('time-slider'), { target: { value: '2' } });

    const completedRequest = structuredClone(requests.at(-1));
    const requestCount = requests.length;
    const graphCount = canvas.graph.mock.calls.length;
    const values = ['graph-kind', 'graph-size', 'selected-node', 'initial-kind', 'seed', 'steps', 'time-slider']
      .map((id) => field<HTMLInputElement>(id).value);
    await switchTo('de');
    expect(screen.getByText('Wahrscheinlichkeitsverteilung', { selector: 'h2' })).toBeInTheDocument();
    expect(screen.getByText('0,7500')).toBeInTheDocument();
    expect(requests).toHaveLength(requestCount);
    expect(canvas.graph).toHaveBeenCalledTimes(graphCount);
    expect(['graph-kind', 'graph-size', 'selected-node', 'initial-kind', 'seed', 'steps', 'time-slider']
      .map((id) => field<HTMLInputElement>(id).value)).toEqual(values);
    expect(screen.getByTitle('0 + (1)i')).toBeInTheDocument();

    await switchTo('en');
    expect(screen.getByText('Probability distribution', { selector: 'h2' })).toBeInTheDocument();
    expect(screen.getByText('0.7500')).toBeInTheDocument();
    expect(requests).toHaveLength(requestCount);
    await userEvent.click(button('.run-button'));
    await waitFor(() => expect(requests).toHaveLength(requestCount + 1));
    expect(requests.at(-1)).toEqual(completedRequest);
    expect((requests.at(-1)?.body as unknown as SimulationRequest).scattering['1']).toEqual(JSON.parse(custom));
    expect(requests.at(-1)?.body.mode).toBe('open');
  });

  it('retains an unsubmitted complex matrix draft while changing labels', async () => {
    render(<App />);
    await waitFor(() => expect(button('.run-button')).toBeEnabled());
    await userEvent.click(screen.getByRole('button', { name: 'Edit' }));
    const draft = '[[[0.123456789,-0.5],[1,0]],[[0,1],[0.25,0]]]';
    fireEvent.change(field('matrix-json'), { target: { value: draft } });
    const count = requests.length;
    await switchTo('de');
    expect(field<HTMLTextAreaElement>('matrix-json').value).toBe(draft);
    expect(screen.getByRole('button', { name: 'Matrix prüfen & übernehmen' })).toBeInTheDocument();
    expect(requests).toHaveLength(count);
    await switchTo('en');
    expect(field<HTMLTextAreaElement>('matrix-json').value).toBe(draft);
  });

  it('preserves an uncommitted seed draft without regenerating the experiment on switch', async () => {
    render(<App />);
    await waitFor(() => expect(button('.run-button')).toBeEnabled());
    await userEvent.click(button('.run-button'));
    await waitFor(() => expect(field<HTMLInputElement>('time-slider').value).toBe('12'));
    await userEvent.click(field('seed'));
    fireEvent.change(field('seed'), { target: { value: '12345' } });
    const count = requests.length;
    const graphCount = canvas.graph.mock.calls.length;
    await switchTo('de');
    expect(field<HTMLInputElement>('seed').value).toBe('12345');
    expect(field<HTMLInputElement>('time-slider').value).toBe('12');
    expect(requests).toHaveLength(count);
    expect(canvas.graph).toHaveBeenCalledTimes(graphCount);
    await switchTo('en');
    expect(field<HTMLInputElement>('seed').value).toBe('12345');
    expect(requests).toHaveLength(count);
    // A later ordinary blur still commits the draft through the original path.
    await userEvent.click(field('seed'));
    await userEvent.click(field('steps'));
    await waitFor(() => expect(requests.at(-1)?.body.seed).toBe(12345));
  });

  it('retranslates an existing server error without repeating the failed request', async () => {
    render(<App />);
    await waitFor(() => expect(button('.run-button')).toBeEnabled());
    rejectSimulation = true;
    await userEvent.click(button('.run-button'));
    const alert = await screen.findByRole('alert');
    const english = alert.textContent;
    const count = requests.length;
    await switchTo('de');
    expect(alert.textContent).not.toBe(english);
    expect(alert.textContent).not.toContain('Backend diagnostic');
    expect(requests).toHaveLength(count);
    await switchTo('en');
    expect(alert.textContent).toBe(english);
  });

  it('keeps an in-flight simulation alive and renders its result in the selected language', async () => {
    render(<App />);
    await waitFor(() => expect(button('.run-button')).toBeEnabled());
    const graph = graphFixture('cycle', 6);
    let resolveReply!: (response: Response) => void;
    const pending = new Promise<Response>((resolve) => { resolveReply = resolve; });
    let requestSignal: AbortSignal | null | undefined;
    const heldFetch = vi.fn((_url: string, options: RequestInit) => {
      requestSignal = options.signal;
      return pending;
    });
    vi.stubGlobal('fetch', heldFetch);
    await userEvent.click(button('.run-button'));
    expect(button('.run-button')).toBeDisabled();
    await switchTo('de');
    expect(heldFetch).toHaveBeenCalledTimes(1);
    expect(requestSignal?.aborted).toBe(false);
    await act(async () => {
      resolveReply({ ok: true, json: async () => ({ graph, mode: 'unitary', frames: framesFixture(graph, 12), outcomes: [] }) } as Response);
    });
    await waitFor(() => expect(field<HTMLInputElement>('time-slider').value).toBe('12'));
    expect(button('.run-button')).toBeEnabled();
    expect(screen.getByText('Wahrscheinlichkeitsverteilung', { selector: 'h2' })).toBeInTheDocument();
  });

  it('renders each mode and both languages without missing translation keys', async () => {
    const missingKey = vi.fn();
    const previousSetting = i18n.options.saveMissing;
    i18n.options.saveMissing = true;
    i18n.on('missingKey', missingKey);
    try {
      render(<App />);
      await waitFor(() => expect(button('.run-button')).toBeEnabled());
      for (const language of ['de', 'en'] as const) {
        // Native buttons support keyboard activation, not just pointer clicks.
        button(`button[lang="${language}"]`).focus();
        await userEvent.keyboard('{Enter}');
        await waitFor(() => expect(document.documentElement.lang).toBe(language));
        for (let mode = 0; mode < 3; mode++) {
          await userEvent.click(document.querySelectorAll<HTMLButtonElement>('.mode-bar button')[mode]);
          await userEvent.click(button('.run-button'));
          await waitFor(() => expect(field<HTMLInputElement>('time-slider').value).toBe('12'));
        }
        expect(document.body.textContent).not.toMatch(/\b(?:app|components|errors):[\w.]+/);
      }
      expect(missingKey).not.toHaveBeenCalled();
    } finally {
      i18n.options.saveMissing = previousSetting;
      i18n.off('missingKey', missingKey);
    }
  });
});

describe('component translation and numerical invariance', () => {
  it('retranslates local validation and preserves the malformed draft', async () => {
    render(<MatrixEditor vertex={1} neighbors={[0, 2]} matrix={[[[1, 0], [0, 0]], [[0, 0], [1, 0]]]} busy={false} onApply={vi.fn()} onPreset={vi.fn()} />);
    await userEvent.click(screen.getByRole('button', { name: 'Edit' }));
    fireEvent.change(field('matrix-json'), { target: { value: '{invalid' } });
    await userEvent.click(screen.getByRole('button', { name: 'Validate & apply matrix' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Enter valid JSON');
    await act(() => setLanguage('de'));
    expect(screen.getByRole('alert')).toHaveTextContent('Gültiges JSON');
    expect(field<HTMLTextAreaElement>('matrix-json').value).toBe('{invalid');
  });

  it('localizes chart tooltips and number strings but keeps numeric plotted data unchanged', async () => {
    const history = [{ step: 0, probabilities: [0.125, 0.875] }, { step: 1, probabilities: [0.5, 0.5] }];
    render(<ProbabilityPlot labels={['x = 0', 'x = 1']} probabilities={[0.5, 0.5]} history={history} />);
    await waitFor(() => expect(canvas.plot).toHaveBeenCalled());
    const english = structuredClone(canvas.plot.mock.calls.at(-1)?.slice(1));
    expect(JSON.stringify(english)).toContain('Probability P');
    expect(JSON.stringify(english)).toContain('0.12500');
    expect(canvas.plot.mock.calls.at(-1)).toEqual(expect.arrayContaining([expect.objectContaining({
      locale: 'en',
      locales: { en: { dictionary: {
        'Double-click to zoom back out': 'Double-click to zoom back out',
        'Double-click on legend to isolate one trace': 'Double-click on legend to isolate one trace',
      } } },
    })]));
    await act(() => setLanguage('de'));
    await waitFor(() => expect(JSON.stringify(canvas.plot.mock.calls.at(-1)?.slice(1))).toContain('Wahrscheinlichkeit P'));
    const german = canvas.plot.mock.calls.at(-1) as unknown as [HTMLElement, { x: number[]; y: number[] }[], unknown];
    expect(JSON.stringify(german.slice(1))).toContain('0,12500');
    expect(canvas.plot.mock.calls.at(-1)).toEqual(expect.arrayContaining([expect.objectContaining({
      locale: 'de',
      locales: { de: { dictionary: {
        'Double-click to zoom back out': 'Doppelklicken, um wieder herauszuzoomen',
        'Double-click on legend to isolate one trace': 'In der Legende doppelklicken, um eine einzelne Kurve anzuzeigen',
      } } },
    })]));
    expect(german[1].map(({ x, y }) => ({ x, y }))).toEqual([
      { x: [0, 1], y: [0.125, 0.5] }, { x: [0, 1], y: [0.875, 0.5] },
    ]);
    expect(history[0].probabilities).toEqual([0.125, 0.875]);
    expect(screen.getByText('Horizontale Achse: Zeitschritt t')).toBeInTheDocument();
    expect(i18n.resolvedLanguage).toBe('de');
  });
});
