import { useEffect, useRef } from 'react';
import Plotly from 'plotly.js-basic-dist-min';
import type { Data, Layout } from 'plotly.js';
import { useTranslation } from 'react-i18next';
import { formatNumber } from './i18n/format';
import type { StationaryResult } from './types';

export default function StationaryPlot({ result, selected, distance = false }: { result: StationaryResult; selected: number; distance?: boolean }) {
  const { t, i18n } = useTranslation('stationary');
  const language = i18n.resolvedLanguage ?? 'en';
  const element = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = element.current;
    if (!node) return;
    const frames = result.frames;
    const keys = distance ? ['ordinaryDistance', 'cesaroDistance'] : ['ordinaryTrace', 'cesaroTrace', 'stationaryTrace'];
    const values = distance ? [frames.map((f) => f.total_variation), frames.map((f) => f.cesaro_total_variation)]
      : [frames.map((f) => f.probabilities[selected]), frames.map((f) => f.cesaro[selected]), frames.map(() => result.stationary_mixture[selected])];
    const traces: Data[] = keys.map((key, i) => ({ type: 'scatter', mode: 'lines', name: t(key),
      x: frames.map((f) => f.step), y: values[i], line: { color: ['#163e50','#15968e','#b77727'][i], width: 2, dash: i === 2 ? 'dash' : 'solid' },
      hovertext: values[i].map((v, j) => `${t(key)}<br>t = ${frames[j].step}<br>${formatNumber(v, language, 6)}`), hovertemplate: '%{hovertext}<extra></extra>' }));
    const layout: Partial<Layout> = { autosize: true, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
      margin: { l: 52, r: 15, t: 15, b: 90 }, font: { family: 'Inter, Segoe UI, sans-serif', size: 11, color: '#526b78' },
      xaxis: { title: { text: t('timeAxis') }, gridcolor: '#edf1f3', dtick: frames.length < 15 ? 1 : undefined },
      yaxis: { title: { text: t(distance ? 'distanceAxis' : 'probability') }, range: [0,1.05], gridcolor: '#edf1f3',
        tickvals: [0,.25,.5,.75,1], ticktext: [0,.25,.5,.75,1].map((v) => formatNumber(v, language, 2)) },
      legend: { orientation: 'h', y: -.32 }, hovermode: 'x unified' };
    let disposed = false;
    let observer: ResizeObserver | undefined;
    const visible = () => node.isConnected && node.clientWidth > 0 && node.clientHeight > 0;
    const resize = () => { if (!disposed && visible()) void Promise.resolve(Plotly.Plots.resize(node)).catch((error: unknown) => { if (!disposed && visible()) console.error('Stationary plot resize failed:', error); }); };
    void Plotly.react(node, traces, layout, { responsive: true, displayModeBar: false, locale: language,
      locales: { [language]: { dictionary: { 'Double-click to zoom back out': t('zoomTip'), 'Double-click on legend to isolate one trace': t('legendTip') } } } })
      .then(() => { if (!disposed && node.isConnected) { observer = new ResizeObserver(resize); observer.observe(node); resize(); } })
      .catch((error: unknown) => { if (!disposed) console.error('Stationary plot failed:', error); });
    return () => { disposed = true; observer?.disconnect(); };
  }, [result, selected, distance, language, t]);
  useEffect(() => { const node = element.current; return () => { if (node) Plotly.purge(node); }; }, []);
  return <div ref={element} className="stationary-plot" role="img" aria-label={t(distance ? 'distanceChart' : 'probabilityChart')} />;
}
