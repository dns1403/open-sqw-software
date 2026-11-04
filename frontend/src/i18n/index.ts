import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import enApp from './locales/en/app.json';
import deApp from './locales/de/app.json';
import enComponents from './locales/en/components.json';
import deComponents from './locales/de/components.json';
import enErrors from './locales/en/errors.json';
import deErrors from './locales/de/errors.json';
import enResearch from './locales/en/research.json';
import deResearch from './locales/de/research.json';
import enStationary from './locales/en/stationary.json';
import deStationary from './locales/de/stationary.json';

export const LANGUAGE_STORAGE_KEY = 'sqw.language';
export const supportedLanguages = [
  { code: 'en', label: 'English' },
  { code: 'de', label: 'Deutsch' },
] as const;
export type SupportedLanguage = typeof supportedLanguages[number]['code'];
export const resources = {
  en: { app: enApp, components: enComponents, errors: enErrors, research: enResearch, stationary: enStationary },
  de: { app: deApp, components: deComponents, errors: deErrors, research: deResearch, stationary: deStationary },
};

/** Language selection is explicit: browser/system preferences are never used. */
export function getInitialLanguage(storage?: Pick<Storage, 'getItem'>): SupportedLanguage {
  try {
    const stored = (storage ?? window.localStorage).getItem(LANGUAGE_STORAGE_KEY);
    return supportedLanguages.find(({ code }) => code === stored)?.code ?? 'en';
  } catch {
    return 'en'; // Storage may be unavailable in private/restricted contexts.
  }
}

function updateDocumentLanguage(language: string) {
  if (typeof document === 'undefined') return;
  document.documentElement.lang = language;
  document.title = i18n.t('app:brand.documentTitle');
  document.querySelector('meta[name="description"]')?.setAttribute('content', i18n.t('app:brand.description'));
}

// Bundled resources initialize synchronously; no network detector or Suspense
// boundary is needed and changing language never remounts the experiment.
void i18n.use(initReactI18next).init({
  resources,
  lng: getInitialLanguage(),
  fallbackLng: 'en',
  supportedLngs: supportedLanguages.map(({ code }) => code),
  ns: ['app', 'components', 'errors', 'research', 'stationary'],
  defaultNS: 'app',
  initAsync: false,
  interpolation: { escapeValue: false },
  returnEmptyString: false,
  react: { useSuspense: false },
});
updateDocumentLanguage(i18n.resolvedLanguage ?? 'en');
i18n.on('languageChanged', updateDocumentLanguage);

export async function setLanguage(language: SupportedLanguage): Promise<void> {
  if (!supportedLanguages.some(({ code }) => code === language)) return;
  try { window.localStorage.setItem(LANGUAGE_STORAGE_KEY, language); } catch { /* Keep in-memory switching usable. */ }
  await i18n.changeLanguage(language);
}

export default i18n;
