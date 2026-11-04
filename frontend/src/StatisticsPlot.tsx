import { useEffect, useRef } from 'react';
import Plotly from 'plotly.js-basic-dist-min';
import type { Data, Layout } from 'plotly.js';
import { useTranslation } from 'react-i18next';
import { formatNumber } from './i18n/format';
import type { StatisticsResult } from './statisticsTypes';

export default function StatisticsPlot({ result, selected }: { result: StatisticsResult; selected: number }) {
  const { t, i18n } = useTranslation('statistics');
  const language = i18n.resolvedLanguage ?? 'en';
  const element = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const node = element.current;
    if (!node) return;
    const path = result.trajectory, points = path.points, theory = result.analysis.classes[selected].poisson;
    const eligible = selected === path.entered_class && !path.support_escape && !path.support_sensitive && !theory.degenerate && !theory.stability_warning;
    const x = points.map(p => p.samples);
    const line = (key: string, y: (number | null)[], color: string, dash = false): Data => ({
      type: 'scatter', mode: 'lines', name: t(key), x, y, connectgaps: false,
      line: { color, width: 2, dash: dash ? 'dash' : 'solid' },
      hovertext: y.map((value,i) => value === null ? '' : `${t(key)}<br>N = ${x[i]} · t = ${points[i].step}<br>${formatNumber(value,language,6)}`),
      hovertemplate: '%{hovertext}<extra></extra>',
    });
    const traces: Data[] = [];
    if (eligible && points.some(p => p.half_width !== null)) {
      traces.push({ ...line('lower',points.map(p => p.half_width===null ? null : theory.mean-p.half_width),'#91c8bc'), showlegend:false });
      traces.push({ ...line('band',points.map(p => p.half_width===null ? null : theory.mean+p.half_width),'#91c8bc'), fill:'tonexty', fillcolor:'rgba(21,150,142,.12)' });
    }
    traces.push(line('reference',points.map(() => theory.mean),'#b77727',true));
    traces.push(line('empirical',points.map(p => p.mean),'#163e50'));
    const layout: Partial<Layout> = { autosize:true, paper_bgcolor:'transparent', plot_bgcolor:'transparent',
      margin:{l:65,r:20,t:15,b:110}, font:{family:'Inter, Segoe UI, sans-serif',size:11,color:'#526b78'},
      xaxis:{title:{text:t('samplesAxis')},gridcolor:'#edf1f3',dtick:path.samples<15?1:undefined},
      yaxis:{title:{text:t('meanAxis')},gridcolor:'#edf1f3'}, separators:language==='de'?',.':'.,',
      legend:{orientation:'h',y:-.3},hovermode:'x unified' };
    let disposed = false;
    let observer: ResizeObserver | undefined;
    const visible = () => node.isConnected && node.clientWidth>0 && node.clientHeight>0;
    const resize = () => { if (!disposed && visible()) void Promise.resolve(Plotly.Plots.resize(node)).catch(error => { if (!disposed && visible()) console.error('Statistics plot resize failed:',error); }); };
    void Plotly.react(node,traces,layout,{responsive:true,displayModeBar:false,locale:language,
      locales:{[language]:{dictionary:{'Double-click to zoom back out':t('stationary:zoomTip'),'Double-click on legend to isolate one trace':t('stationary:legendTip')}}}})
      .then(() => { if (!disposed && node.isConnected) { observer = new ResizeObserver(resize); observer.observe(node); resize(); } })
      .catch(error => { if (!disposed) console.error('Statistics plot failed:',error); });
    return () => { disposed=true; observer?.disconnect(); };
  },[result,selected,language,t]);
  useEffect(() => { const node=element.current; return () => { if (node) Plotly.purge(node); }; },[]);
  return <div ref={element} className="statistics-plot" role="img" aria-label={t('chart')} />;
}
