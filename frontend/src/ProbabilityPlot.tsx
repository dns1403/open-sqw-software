import { useEffect, useRef } from 'react';
import Plotly from 'plotly.js-basic-dist-min';
import { useTranslation } from 'react-i18next';
import type { Data, Layout } from 'plotly.js';
import { formatNumber } from './i18n/format';

interface Props { labels: string[]; probabilities: number[]; selected?: number; history?: { step: number; probabilities: number[] }[]; }

export default function ProbabilityPlot({ labels, probabilities, selected, history }: Props) {
  const { t, i18n } = useTranslation('components');
  const language = i18n.resolvedLanguage ?? 'en';
  const element = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = element.current;
    if (!node) return;
    const traces: Data[] = history
      ? labels.map((label, index) => ({ type: 'scatter', mode: 'lines', name: label,
        x: history.map((frame) => frame.step), y: history.map((frame) => frame.probabilities[index]),
        line: { width: 2.2 },
        hovertext: history.map((frame) => `${label}<br>${t('plot.timeStep')} = ${frame.step}<br>${t('plot.probability')} = ${formatNumber(frame.probabilities[index], language, 5)}`),
        hovertemplate: '%{hovertext}<extra></extra>' }))
      : [{ type: 'bar', x: labels, y: probabilities,
        marker: { color: probabilities.map((_, i) => i === selected ? '#143c4b' : '#15968e'), line: { width: 0 } },
        width: labels.length > 12 ? 0.72 : 0.52,
        hovertext: probabilities.map((p, index) => `${labels[index]}<br>${t('plot.probability')} = ${formatNumber(p, language, 6)}`),
        hovertemplate: '%{hovertext}<extra></extra>' }];
    const percentages = new Intl.NumberFormat(language, { style: 'percent', maximumFractionDigits: 0 });
    const parts = new Intl.NumberFormat(language).formatToParts(1234.5);
    const layout: Partial<Layout> = {
      autosize: true, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent',
      separators: `${parts.find((part) => part.type === 'decimal')?.value ?? '.'}${parts.find((part) => part.type === 'group')?.value ?? ','}`,
      font: { family: 'Inter, Segoe UI, sans-serif', color: '#70838b', size: 11 },
      margin: { l: 44, r: 16, t: 15, b: history ? 40 + Math.ceil(labels.length / 4) * 18 : labels.length > 12 ? 65 : 40 },
      xaxis: { showgrid: false, zeroline: false,
        tickangle: !history && labels.length > 12 ? -45 : 0, automargin: true, ...(history ? { dtick: history.length < 15 ? 1 : undefined } : { type: 'category' }) },
      yaxis: { range: [0, 1.05], gridcolor: '#e9eef0', zeroline: false,
        tickmode: 'array', tickvals: [0, 0.25, 0.5, 0.75, 1],
        ticktext: [0, 0.25, 0.5, 0.75, 1].map((value) => percentages.format(value)) },
      showlegend: Boolean(history), legend: { orientation: 'h', y: -0.23, yanchor: 'top', x: 0, font: { size: 10 } },
      colorway: ['#15968e', '#163e50', '#d3a349', '#7c80b6', '#a26377', '#6594bb'],
      hovermode: history ? 'x unified' : 'closest', bargap: 0.25,
    };
    let disposed = false;
    let observer: ResizeObserver | undefined;
    const isDisplayed = () => node.isConnected && node.clientWidth > 0 && node.clientHeight > 0 && node.getClientRects().length > 0;
    const resize = () => {
      if (disposed || !isDisplayed()) return;
      void Promise.resolve().then(() => {
        if (!disposed && isDisplayed()) return Plotly.Plots.resize(node);
      }).catch((error: unknown) => {
        // Plotly schedules resize work internally; unmount can happen before it runs.
        if (!disposed && isDisplayed()) console.error('Plotly resize failed:', error);
      });
    };
    void Plotly.react(node, traces, layout, {
      responsive: true, displayModeBar: false, scrollZoom: false,
      locale: language,
      // Plotly emits its own interaction tips outside our React labels.
      // Keep their dictionary alongside all other presentation translations.
      locales: { [language]: { dictionary: {
        'Double-click to zoom back out': t('plot.zoomTip'),
        'Double-click on legend to isolate one trace': t('plot.legendTip'),
      } } },
    })
      .then(() => {
        if (disposed || !node.isConnected) return;
        observer = new ResizeObserver(resize);
        observer.observe(node);
        resize();
      })
      .catch((error: unknown) => { if (!disposed) console.error('Plotly rendering failed:', error); });
    return () => { disposed = true; observer?.disconnect(); };
  }, [labels.join('|'), probabilities, selected, history, language, t]);
  useEffect(() => { const node = element.current; return () => { if (node) Plotly.purge(node); }; }, []);
  return <>
    {history && <p style={{ color: '#8b9da5', fontSize: 9, textAlign: 'right', margin: '12px 20px 0' }}>{t('plot.timeAxisCaption')}</p>}
    <div ref={element} className={`probability-plot ${history ? 'history-plot' : ''}`} style={history ? { height: 190 + Math.ceil(labels.length / 4) * 18 } : undefined} role="img" aria-label={t(history ? 'plot.historyAccessibleDescription' : 'plot.distributionAccessibleDescription')} />
  </>;
}
