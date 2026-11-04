import { useTranslation } from 'react-i18next';
import { setLanguage, supportedLanguages } from './i18n';

export default function LanguageSwitcher() {
  const { t, i18n } = useTranslation('app');
  return <div className="language-switcher" role="group" aria-label={t('language.label')}>
    {supportedLanguages.map(({ code, label }, index) => <span key={code}>
      {index > 0 && <span className="language-divider" aria-hidden="true">|</span>}
      <button type="button" lang={code} aria-label={t('language.switchTo', { language: label })}
        title={label} aria-pressed={i18n.resolvedLanguage === code}
        onClick={() => void setLanguage(code)}>{code.toUpperCase()}</button>
    </span>)}
  </div>;
}
