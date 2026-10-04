'use client';

import { useEffect, useId, useRef } from 'react';

export function InventoryDialog({ title, busy, onClose, children }: {
  title: string; busy: boolean; onClose: () => void; children: React.ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  useEffect(() => {
    const element = dialog.current;
    const previous = document.activeElement as HTMLElement | null;
    element?.showModal();
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      element?.close(); document.body.style.overflow = overflow;
      if (previous?.isConnected) previous.focus();
      else (document.querySelector<HTMLButtonElement>('[data-inventory-add]:not(:disabled)')
        ?? document.querySelector<HTMLButtonElement>('[data-inventory-retry]'))?.focus();
    };
  }, []);
  return <dialog ref={dialog} className="inventory-dialog" aria-modal="true" aria-labelledby={titleId}
    onKeyDown={event => {
      if (event.key !== 'Tab') return;
      const items = Array.from(dialog.current!.querySelectorAll<HTMLElement>('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href]'))
        .filter(element => element.getClientRects().length > 0);
      const first = items[0], last = items.at(-1);
      if (!first) { event.preventDefault(); dialog.current?.focus(); }
      else if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    }}
    onCancel={event => { event.preventDefault(); if (!busy) onClose(); }}
    onClick={event => { const box = dialog.current!.getBoundingClientRect();
      if (!busy && event.target === dialog.current && (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom)) onClose(); }}>
    <div className="inventory-dialog-heading"><h2 id={titleId} className="text-xl font-semibold">{title}</h2>
      <button type="button" className="hpp-button" aria-label={`Tutup ${title}`} disabled={busy} onClick={onClose}>Tutup</button></div>
    <div className="p-4 sm:p-6">{children}</div>
  </dialog>;
}
