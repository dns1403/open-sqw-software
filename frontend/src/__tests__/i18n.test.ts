import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n, {
  getInitialLanguage, LANGUAGE_STORAGE_KEY, resources, setLanguage,
} from '../i18n';
import { formatNumber } from '../i18n/format';

function leaves(value: unknown, prefix = ''): Record<string, string> {
  if (typeof value === 'string') return { [prefix]: value };
  return Object.fromEntries(Object.entries(value as Record<string, unknown>)
    .flatMap(([key, child]) => Object.entries(leaves(child, prefix ? `${prefix}.${key}` : key))));
}

function placeholders(text: string): string[] {
  return [...text.matchAll(/\{\{\s*-?\s*([^},\s]+)(?:[^}]*)\}\}/g)]
    .map((match) => match[1]).sort();
}

beforeEach(async () => {
  await setLanguage('en');
  localStorage.clear();
});

describe('language selection and fallback', () => {
  it('defaults to English even when the browser prefers German', () => {
    vi.spyOn(navigator, 'language', 'get').mockReturnValue('de-DE');
    expect(getInitialLanguage()).toBe('en');
  });

  it('honours only a supported, explicitly stored choice', () => {
    for (const saved of ['de', 'en']) {
      localStorage.setItem(LANGUAGE_STORAGE_KEY, saved);
      expect(getInitialLanguage()).toBe(saved);
    }
    for (const saved of ['fr', 'de-DE', 'DE', '', 'null']) {
      localStorage.setItem(LANGUAGE_STORAGE_KEY, saved);
      expect(getInitialLanguage()).toBe('en');
    }
  });

  it('survives unavailable storage without changing the default', () => {
    expect(getInitialLanguage({ getItem: () => { throw new Error('Storage denied'); } })).toBe('en');
  });

  it('persists explicit changes and updates the document language immediately', async () => {
    await setLanguage('de');
    expect(i18n.resolvedLanguage).toBe('de');
    expect(document.documentElement.lang).toBe('de');
    expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe('de');
    // The startup reader is the same path used on the next page load.
    expect(getInitialLanguage()).toBe('de');
    await setLanguage('en');
    expect(document.documentElement.lang).toBe('en');
    expect(localStorage.getItem(LANGUAGE_STORAGE_KEY)).toBe('en');
  });

  it('still switches languages when writing the preference is blocked', async () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('Quota exceeded'); });
    await expect(setLanguage('de')).resolves.toBeUndefined();
    expect(i18n.resolvedLanguage).toBe('de');
    expect(document.documentElement.lang).toBe('de');
  });

  it('falls back to English for a key absent from the selected language', async () => {
    i18n.addResource('en', 'app', '__fallback_probe__', 'English fallback');
    try {
      await setLanguage('de');
      expect(i18n.t('__fallback_probe__', { ns: 'app' })).toBe('English fallback');
    } finally {
      delete i18n.getResourceBundle('en', 'app').__fallback_probe__;
    }
  });
});

describe('translation catalogue contract', () => {
  it('has identical complete key structures and interpolation arguments in every language', () => {
    const canonical = leaves(resources.en);
    for (const [language, catalogue] of Object.entries(resources)) {
      const translated = leaves(catalogue);
      expect(Object.keys(translated).sort(), language).toEqual(Object.keys(canonical).sort());
      for (const [key, text] of Object.entries(translated)) {
        expect(text.trim(), `${language}:${key}`).not.toBe('');
        expect(placeholders(text), `${language}:${key}`).toEqual(placeholders(canonical[key]));
      }
    }
  });

  it('resolves every translated key instead of exposing identifiers to the interface', () => {
    for (const [language, namespaces] of Object.entries(resources)) {
      for (const [namespace, catalogue] of Object.entries(namespaces)) {
        for (const key of Object.keys(leaves(catalogue))) {
          const text = i18n.t(key, { lng: language, ns: namespace });
          expect(text, `${language}:${namespace}:${key}`).not.toBe(key);
        }
      }
    }
  });

  it('formats observable numbers by locale without changing their numeric values', () => {
    const probability = 0.125;
    expect(formatNumber(probability, 'en', 4)).toBe('0.1250');
    expect(formatNumber(probability, 'de', 4)).toBe('0,1250');
    expect(probability).toBe(0.125);
  });
});
