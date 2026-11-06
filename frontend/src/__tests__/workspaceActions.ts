import { fireEvent, screen, within } from '@testing-library/react';
import i18n from '../i18n';
import type { Section } from '../Workspace';

export function visit(section: Section) {
  fireEvent.click(within(screen.getByRole('navigation', { name: i18n.t('app:workspace.navigation') })).getByRole('button', { name: i18n.t(`app:workspace.nav.${section}`) }));
}

/** Reach the control through the same navigation/disclosures a user uses. */
export function reveal(element: Element) {
  const hidden = element.closest('[hidden]');
  const destination = hidden?.getAttribute('data-destination');
  if (destination && ['graph','simulation','trajectories','analysis','learn'].includes(destination)) visit(destination as Section);
  const details: HTMLDetailsElement[] = [];
  let parent = element.parentElement;
  while (parent) { if (parent instanceof HTMLDetailsElement && !parent.open) details.unshift(parent); parent = parent.parentElement; }
  for (const detail of details) fireEvent.click(detail.querySelector('summary')!);
}
