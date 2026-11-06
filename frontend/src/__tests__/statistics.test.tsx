import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, it, vi } from 'vitest';
import Plotly from 'plotly.js-basic-dist-min';
import { statisticsFixture as fixture } from './workspaceFixtures';
import StatisticsPanel from '../StatisticsPanel';
import { setLanguage } from '../i18n';
import type { GraphData, SimulationRequest } from '../types';
import type { StatisticsResult } from '../statisticsTypes';
vi.mock('plotly.js-basic-dist-min',()=>({default:{react:vi.fn(async()=>{}),purge:vi.fn(),Plots:{resize:vi.fn(async()=>{})}}}));
const graph: GraphData = {vertices:[0,1,2],edges:[[0,1],[1,2]],directed_edges:[[0,1],[1,0],[1,2],[2,1]],neighbors:{},scattering:{},dimension:4};
const experiment: SimulationRequest = {graph:{kind:'path',size:3},preset:'identity',scattering:{},mode:'vertex',initial:{kind:'uniform',edge:[0,1]},steps:20,seed:42};
const calls: {body:Record<string,unknown>;signal?:AbortSignal|null}[] = [];
let response: StatisticsResult;
beforeEach(async()=>{
  await setLanguage('en'); calls.length=0; response=structuredClone(fixture); vi.mocked(Plotly.react).mockClear();
  vi.stubGlobal('fetch',vi.fn(async(_url:string,options:RequestInit)=>{calls.push({body:JSON.parse(String(options.body)),signal:options.signal});return {ok:true,json:async()=>response};}));
});
const setup = () => render(<StatisticsPanel graph={graph} experiment={experiment} />);
async function run() { await userEvent.click(screen.getByRole('button',{name:'Analyze trajectory statistics'})); await screen.findByText('Selected class · asymptotic statistics'); }

it('plots a conditional correlated envelope and shows IID comparison and limits',async()=>{
  setup(); await run();
  expect(screen.getByText(/not generally one global Gaussian/)).toBeInTheDocument();
  expect(screen.getByText('IID standard error · comparison only')).toBeInTheDocument();
  expect(screen.getByText(/not simultaneous coverage/)).toBeInTheDocument();
  const traces=vi.mocked(Plotly.react).mock.calls.at(-1)![1];
  expect(traces).toHaveLength(4);
  expect(traces[1]).toMatchObject({fill:'tonexty',x:[1,2],y:[1.88,1.48]});
  expect(traces[2]).toMatchObject({y:[.5,.5]}); expect(traces[3]).toMatchObject({y:[1,.5]});
  expect(calls[0].body).toMatchObject({seed:42,trajectory_seed:42,samples:2000,observable:{kind:'label_indicator'}});
});

it('preserves class, observable, seed, and data across language changes without requests',async()=>{
  setup(); await userEvent.selectOptions(screen.getByLabelText('Observable'),'vertex_probability');
  fireEvent.change(screen.getByLabelText('Trajectory seed'),{target:{value:'77'}});
  await run(); await userEvent.selectOptions(screen.getByLabelText('Class to inspect / prepare on next run'),'1');
  expect(screen.getByText(/has not entered the selected class/)).toBeInTheDocument();
  expect(vi.mocked(Plotly.react).mock.calls.at(-1)![1]).toHaveLength(2);
  await act(()=>setLanguage('de'));
  expect(screen.getByRole('heading',{name:'Trajektorienstatistik & Unsicherheit'})).toBeInTheDocument();
  expect(screen.getByLabelText('Trajektorien-Seed')).toHaveValue(77);
  expect(screen.getByLabelText('Observable')).toHaveValue('vertex_probability');
  expect(screen.getByLabelText('Klasse zur Ansicht / Präparation beim nächsten Lauf')).toHaveValue('1');
  expect(calls).toHaveLength(1);
});

it.each(['degenerate','support','unstable'])('suppresses the empirical Gaussian band for %s',async reason=>{
  if(reason==='degenerate') response.analysis.classes[0].poisson.degenerate=true;
  if(reason==='unstable') response.analysis.classes[0].poisson.stability_warning=true;
  if(reason==='support') response.trajectory.support_sensitive=true;
  response.trajectory.confidence_interval=null;
  setup(); await run(); expect(vi.mocked(Plotly.react).mock.calls.at(-1)![1]).toHaveLength(2);
  expect(screen.queryByText(/Approximate final confidence interval/)).not.toBeInTheDocument();
});

it('invalidates changed sampling inputs and submits explicit class preparation',async()=>{
  setup(); await run(); await userEvent.selectOptions(screen.getByLabelText('Class to inspect / prepare on next run'),'1');
  await userEvent.selectOptions(screen.getByLabelText('Trajectory initialization'),'stationary_class');
  expect(screen.queryByRole('img')).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText('Recorded observations N'),{target:{value:'0'}});
  expect(screen.getByRole('button',{name:'Analyze trajectory statistics'})).toBeDisabled();
  fireEvent.change(screen.getByLabelText('Recorded observations N'),{target:{value:'500'}});
  await run(); expect(calls[1].body).toMatchObject({initialization:'stationary_class',stationary_class:1,samples:500});
});

it('aborts pending requests on experiment changes',async()=>{
  let signal:AbortSignal|null|undefined;
  vi.stubGlobal('fetch',vi.fn((_url:string,options:RequestInit)=>{signal=options.signal;return new Promise(()=>{});}));
  const {rerender}=setup(); await userEvent.click(screen.getByRole('button',{name:'Analyze trajectory statistics'}));
  rerender(<StatisticsPanel graph={graph} experiment={{...experiment,preset:'dft'}} />);
  expect(signal?.aborted).toBe(true); expect(screen.getByRole('button',{name:'Analyze trajectory statistics'})).toBeEnabled();
});

it('translates API errors without another request',async()=>{
  vi.stubGlobal('fetch',vi.fn(async()=>({ok:false,status:422,json:async()=>({code:'statistics_budget'})})));
  setup(); await userEvent.click(screen.getByRole('button',{name:'Analyze trajectory statistics'}));
  await waitFor(()=>expect(screen.getByRole('alert')).toHaveTextContent('statistics work budget'));
  await act(()=>setLanguage('de')); expect(screen.getByRole('alert')).toHaveTextContent('Statistik-Rechenbudget');
  expect(fetch).toHaveBeenCalledTimes(1);
});
