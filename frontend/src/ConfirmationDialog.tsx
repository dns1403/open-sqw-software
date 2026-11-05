import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';

interface Confirmation {
  key: string;
  params: Record<string, string | number>;
  resolve: (accepted: boolean) => void;
}

/** App-owned dialogs keep confirmations accessible without blocking the browser. */
export function useConfirmation() {
  const [confirmation, setConfirmation] = useState<Confirmation | null>(null);
  const confirm = (key: string, params: Confirmation['params'] = {}) =>
    new Promise<boolean>(resolve => setConfirmation({ key, params, resolve }));
  function finish(accepted: boolean) {
    confirmation?.resolve(accepted);
    setConfirmation(null);
  }
  return { confirm, confirmation, finish };
}

export default function ConfirmationDialog({ confirmation, finish }: {
  confirmation: Confirmation | null;
  finish: (accepted: boolean) => void;
}) {
  const { t } = useTranslation('components');
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (confirmation) dialog.current?.showModal();
    else dialog.current?.close();
  }, [confirmation]);
  return <dialog ref={dialog} className="confirmation-dialog" aria-labelledby="confirmation-title"
    onCancel={event => { event.preventDefault(); finish(false); }}>
    <h2 id="confirmation-title">{t('editor.confirmTitle')}</h2>
    <p>{confirmation ? t(`editor.${confirmation.key}`, confirmation.params) : ''}</p>
    <div className="confirmation-actions">
      <button autoFocus className="text-button" onClick={() => finish(false)}>{t('editor.cancelChange')}</button>
      <button className="secondary-button" onClick={() => finish(true)}>{t('editor.confirmChange')}</button>
    </div>
  </dialog>;
}
