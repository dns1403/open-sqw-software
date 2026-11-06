import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import type { TourKind } from './onboarding';

export const sections = ['overview', 'graph', 'simulation', 'trajectories', 'analysis', 'learn'] as const;
export type Section = typeof sections[number];
export type Destination = Section | 'matrices' | 'parameters' | 'files' | 'initial' | 'results' | 'ensemble' | 'inspector' | 'stationary' | 'statistics';
export const sectionFor = (destination: Destination): Section => {
  if (['matrices', 'parameters', 'files'].includes(destination)) return 'graph';
  if (['initial', 'results'].includes(destination)) return 'simulation';
  if (destination === 'ensemble') return 'trajectories';
  if (['inspector', 'stationary', 'statistics'].includes(destination)) return 'analysis';
  return destination as Section;
};
export type Navigate = (destination: Destination) => void;
const symbols = ['◈', '◇', '▷', 'ψ', '∑', '?'];

export function WorkspaceNavigation({ section, navigate }: { section: Section; navigate: Navigate }) {
  const { t } = useTranslation('app');
  const [open, setOpen] = useState(false);
  return <aside className="navigation-rail" data-tour="navigation">
    <div className="rail-brand"><span aria-hidden="true">◇</span><div>SCATTERING<small>QUANTUM WALK LAB</small></div></div>
    <button className="menu-toggle" aria-expanded={open} aria-controls="workspace-navigation" onClick={() => setOpen(!open)}>{t('workspace.menu')} <span aria-hidden="true">☰</span></button>
    <nav id="workspace-navigation" className={`nav-links ${open ? 'mobile-open' : ''}`} aria-label={t('workspace.navigation')}>
      {sections.map((item, i) => <button key={item} aria-current={section === item ? 'page' : undefined} onClick={() => { navigate(item); setOpen(false); }}><span aria-hidden="true">{symbols[i]}</span>{t(`workspace.nav.${item}`)}</button>)}
    </nav>
    <div className="rail-note"><span className="status-dot" />{t('workspace.local')}<small>{t('workspace.persistence')}</small></div>
  </aside>;
}

export function ContextHelp({ topic }: { topic: string }) {
  const { t } = useTranslation('app');
  return <details className="context-help"><summary>{t(`workspace.help.${topic}.title`)}</summary><p>{t(`workspace.help.${topic}.body`)}</p></details>;
}

export const featureGroups: { destination: Destination; items: string[] }[] = [
  { destination: 'graph', items: ['presets', 'builder', 'layout'] },
  { destination: 'matrices', items: ['coins', 'editing', 'bindings'] },
  { destination: 'parameters', items: ['omega'] },
  { destination: 'files', items: ['files'] },
  { destination: 'initial', items: ['preparation'] },
  { destination: 'simulation', items: ['modes', 'execution'] },
  { destination: 'results', items: ['playback', 'plots'] },
  { destination: 'trajectories', items: ['record', 'conditional'] },
  { destination: 'ensemble', items: ['ensemble', 'histories'] },
  { destination: 'inspector', items: ['atoms', 'densities'] },
  { destination: 'stationary', items: ['classes', 'stationary', 'cesaro'] },
  { destination: 'statistics', items: ['observables', 'poisson', 'uncertainty'] },
];

export function Overview({ navigate, startTour, tourSeen }: { navigate: Navigate; startTour: (kind: TourKind) => void; tourSeen: boolean }) {
  const { t } = useTranslation('app');
  const entries: { key: string; destination?: Destination; tour?: TourKind; symbol: string }[] = [
    { key: 'build', destination: 'graph', symbol: '◇' }, { key: 'walk', destination: 'simulation', symbol: '▷' },
    { key: 'trajectory', destination: 'trajectories', symbol: 'ψ' }, { key: 'longtime', destination: 'stationary', symbol: '∑' },
    { key: 'open', destination: 'files', symbol: '↥' }, { key: 'tour', tour: 'intro', symbol: '?' },
  ];
  return <>
    <section className="overview-hero" data-tour="welcome"><div><p className="eyebrow">{t('workspace.hero.eyebrow')}</p><h2>{t('workspace.hero.title')}</h2><p>{t('workspace.hero.body')}</p><button className="secondary-button" onClick={() => startTour('intro')}>{t(tourSeen ? 'workspace.restartTour' : 'workspace.startTour')}</button></div><div className="hero-formula" aria-hidden="true"><span>y → x → z</span>U<sub>S</sub>|xy⟩ = ∑<sub>z∼x</sub> S<sub>zy</sub>(x)|zx⟩<small>{t('brand.tagline')}</small></div></section>
    <div className="entry-grid">{entries.map(entry => <button key={entry.key} className="entry-card" onClick={() => entry.destination ? navigate(entry.destination) : startTour(entry.tour!)}><span className="entry-symbol" aria-hidden="true">{entry.symbol}</span><strong>{t(`workspace.entry.${entry.key}.title`)}</strong><span>{t(`workspace.entry.${entry.key}.body`)}</span><span className="entry-arrow" aria-hidden="true">↗</span></button>)}</div>
    <section className="feature-directory" data-tour="directory"><h2>{t('workspace.directory')}</h2><p>{t('workspace.directoryHint')}</p><div className="directory-grid">{featureGroups.map(group => <article key={group.destination}><h3><button onClick={() => navigate(group.destination)}>{t(`workspace.destinations.${group.destination}`)} <span aria-hidden="true">→</span></button></h3><ul>{group.items.map(item => <li key={item}><button onClick={() => navigate(group.destination)}>{t(`workspace.features.${item}`)}</button></li>)}</ul></article>)}</div></section>
  </>;
}

export function LearnPanel({ startTour }: { startTour: (kind: TourKind) => void }) {
  const { t } = useTranslation('app');
  return <div data-tour="help"><div className="section-intro"><h2>{t('workspace.learnTitle')}</h2><p>{t('workspace.learnBody')}</p></div>
    <div className="tutorial-grid">{(['intro', 'walk', 'trajectory', 'longtime'] as TourKind[]).map(kind => <article className="panel tutorial-card" key={kind}><h3>{t(`workspace.tours.${kind}.title`)}</h3><p>{t(`workspace.tours.${kind}.body`)}</p><button className="secondary-button" onClick={() => startTour(kind)}>{t('workspace.launchTutorial')}</button></article>)}</div>
    <section className="panel help-library"><h2>{t('workspace.glossary')}</h2>{['basis', 'matrix', 'trajectory', 'conditional', 'stationary', 'cesaro', 'variance'].map(topic => <ContextHelp key={topic} topic={topic} />)}<a href="https://arxiv.org/abs/2409.08428v2" target="_blank" rel="noreferrer">{t('brand.reference')} ↗</a></section>
    <section className="panel help-library"><h2>{t('workspace.exampleTitle')}</h2><p>{t('workspace.exampleBody')}</p><a className="secondary-button example-link" href="?example=first-walk" target="_blank" rel="noopener noreferrer">{t('workspace.openExample')} ↗</a></section>
  </div>;
}
