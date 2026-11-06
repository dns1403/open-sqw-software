import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { driver } from 'driver.js';
import type { DriveStep } from 'driver.js';
import { setLanguage } from './i18n';
import type { Destination, Navigate } from './Workspace';
import 'driver.js/dist/driver.css';

export type TourKind = 'intro' | 'walk' | 'trajectory' | 'longtime';
type Stop = { destination: Destination; target: string; key: string };
export const tourStops: Record<TourKind, Stop[]> = {
  intro: [
    { destination: 'overview', target: 'welcome', key: 'welcome' },
    { destination: 'overview', target: 'workflow', key: 'workflow' },
    { destination: 'graph', target: 'graph', key: 'graph' },
    { destination: 'matrices', target: 'matrix', key: 'matrix' },
    { destination: 'simulation', target: 'run', key: 'run' },
    { destination: 'analysis', target: 'analysis', key: 'analysis' },
    { destination: 'learn', target: 'help', key: 'help' },
  ],
  walk: [
    { destination: 'graph', target: 'graph-settings', key: 'preset' },
    { destination: 'matrices', target: 'matrix', key: 'matrix' },
    { destination: 'initial', target: 'initial', key: 'initial' },
    { destination: 'simulation', target: 'run', key: 'run' },
    { destination: 'results', target: 'playback', key: 'playback' },
    { destination: 'results', target: 'results', key: 'results' },
  ],
  trajectory: [
    { destination: 'simulation', target: 'mode', key: 'trajectoryMode' },
    { destination: 'simulation', target: 'run', key: 'trajectoryRun' },
    { destination: 'trajectories', target: 'record', key: 'record' },
    { destination: 'trajectories', target: 'conditional', key: 'conditional' },
    { destination: 'ensemble', target: 'ensemble', key: 'ensemble' },
    { destination: 'inspector', target: 'inspector', key: 'atoms' },
  ],
  longtime: [
    { destination: 'simulation', target: 'mode', key: 'analysisMode' },
    { destination: 'stationary', target: 'stationary-run', key: 'stationaryRun' },
    { destination: 'stationary', target: 'classes', key: 'classes' },
    { destination: 'stationary', target: 'cesaro', key: 'cesaro' },
    { destination: 'statistics', target: 'statistics', key: 'statistics' },
  ],
};
export const TOUR_STORAGE_KEY = 'sqw-onboarding-v1';

/** Navigation and explanatory text only: no access to scientific setters or API. */
export function useOnboarding(navigate: Navigate) {
  const { t, i18n } = useTranslation('app');
  const [active, setActive] = useState<{ kind: TourKind; index: number } | null>(null);
  const [seen, setSeen] = useState(() => { try { return localStorage.getItem(TOUR_STORAGE_KEY) === 'seen'; } catch { return false; } });
  const returnFocus = useRef<HTMLElement | null>(null);
  const go = (kind: TourKind, index: number) => { navigate(tourStops[kind][index].destination); setActive({ kind, index }); };
  const start = (kind: TourKind) => { returnFocus.current = document.activeElement as HTMLElement; go(kind, 0); };
  useEffect(() => {
    if (!active) return;
    let cleaning = false;
    const { kind, index } = active;
    const stop = tourStops[kind][index];
    // React has mounted the destination. Reveal any native advanced disclosure.
    const target = document.querySelector<HTMLElement>(`[data-tour="${stop.target}"]`);
    let parent = target?.parentElement;
    while (parent) { if (parent instanceof HTMLDetailsElement) parent.open = true; parent = parent.parentElement; }
    const available = target && !target.closest('[hidden]') && getComputedStyle(target).display !== 'none';
    const finish = () => {
      if (cleaning) return;
      setActive(null);
      if (kind === 'intro') { setSeen(true); try { localStorage.setItem(TOUR_STORAGE_KEY, 'seen'); } catch { /* Private mode: tours still work. */ } }
      requestAnimationFrame(() => {
        const origin = returnFocus.current;
        (origin?.isConnected && !origin.closest('[hidden]') ? origin : document.getElementById('workspace-title'))?.focus();
      });
    };
    const steps: DriveStep[] = tourStops[kind].map((item, position) => ({
      element: position === index ? (available ? target : undefined) : `[data-tour="${item.target}"]`,
      popover: {
        title: t(`workspace.tourSteps.${item.key}.title`),
        description: `${position === index && !available ? t('workspace.tourUnavailable') + ' ' : ''}${t(`workspace.tourSteps.${item.key}.body`)}`,
        side: 'bottom', align: 'start',
      },
    }));
    const tour = driver({ steps, animate: false, smoothScroll: false, showProgress: true,
      progressText: t('workspace.tourProgress', { current: index + 1, total: steps.length }),
      nextBtnText: t('workspace.next'), prevBtnText: t('workspace.previous'), doneBtnText: t('workspace.finish'),
      closeBtnLabel: t('workspace.skipTour'), allowClose: true, overlayClickBehavior: 'none',
      popoverClass: 'sqw-tour', stagePadding: 6,
      onNextClick: () => index + 1 < steps.length ? go(kind, index + 1) : finish(),
      onPrevClick: () => { if (index > 0) go(kind, index - 1); },
      onDoneClick: finish, onDestroyed: finish,
      onPopoverRender: popover => {
        popover.wrapper.setAttribute('role', 'dialog');
        popover.wrapper.setAttribute('aria-modal', 'false');
        popover.wrapper.setAttribute('aria-label', t(`workspace.tours.${kind}.title`));
        const controls = document.createElement('div'); controls.className = 'tour-extra';
        const skip = document.createElement('button'); skip.textContent = t('workspace.skipTour'); skip.onclick = () => tour.destroy(); controls.append(skip);
        for (const language of ['en', 'de'] as const) {
          const button = document.createElement('button'); button.textContent = language.toUpperCase();
          button.className = 'tour-language';
          button.setAttribute('aria-label', t(`workspace.tourLanguage.${language}`));
          button.setAttribute('aria-pressed', String(i18n.resolvedLanguage === language));
          button.onclick = () => { void setLanguage(language); }; controls.append(button);
        }
        popover.footer.append(controls);
      },
    });
    tour.drive(index);
    // Driver's built-in focus list omits number/range inputs and disclosure controls.
    // Keep the real highlighted controls keyboard-accessible alongside the popover.
    const trapTab = (event: KeyboardEvent) => {
      if (event.key !== 'Tab') return;
      const popover = document.querySelector<HTMLElement>('.sqw-tour');
      if (!popover) return;
      const selector = 'button:not(:disabled),a[href],input:not(:disabled):not([type="hidden"]),select:not(:disabled),textarea:not(:disabled),summary,[tabindex="0"]';
      const roots = available ? [target, popover] : [popover];
      const candidates = roots.flatMap(root => [...(root.matches(selector) ? [root] : []), ...root.querySelectorAll<HTMLElement>(selector)])
        .filter(element => !element.closest('[hidden]') && element.getClientRects().length > 0);
      if (!candidates.length) return;
      const current = candidates.indexOf(document.activeElement as HTMLElement);
      const next = current < 0 ? (event.shiftKey ? candidates.length - 1 : 0) : (current + (event.shiftKey ? -1 : 1) + candidates.length) % candidates.length;
      event.preventDefault(); event.stopImmediatePropagation(); candidates[next].focus();
    };
    const preserveInputKeys = (event: KeyboardEvent) => {
      if (event.target instanceof Element && event.target.matches('input,textarea,select') && ['ArrowLeft','ArrowRight'].includes(event.key)) event.stopImmediatePropagation();
    };
    document.addEventListener('keydown', trapTab, true);
    document.addEventListener('keyup', preserveInputKeys, true);
    const refresh = () => tour.refresh();
    const observer = new ResizeObserver(refresh);
    if (available) observer.observe(target);
    window.addEventListener('resize', refresh);
    return () => { cleaning = true; observer.disconnect(); window.removeEventListener('resize', refresh); document.removeEventListener('keydown', trapTab, true); document.removeEventListener('keyup', preserveInputKeys, true); tour.destroy(); };
    // A language change rebuilds this same step; it never navigates or changes experiment data.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, i18n.resolvedLanguage, t]);
  return { start, seen, active };
}
