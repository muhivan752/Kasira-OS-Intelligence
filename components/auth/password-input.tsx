'use client';

import { useId, useState, type InputHTMLAttributes } from 'react';

export function PasswordInput({ label, ...props }: Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'id'> & { label: string }) {
  const id = useId();
  const [visible, setVisible] = useState(false);
  return <div className="account-password-control">
    <label htmlFor={id}>{label}</label>
    <div className="account-password-field">
      <input {...props} id={id} type={visible ? 'text' : 'password'} autoCapitalize="none" autoCorrect="off" spellCheck={false} />
      <button type="button" className="account-password-toggle" aria-label={`${visible ? 'Sembunyikan' : 'Tampilkan'} ${label.toLowerCase()}`} aria-controls={id} aria-pressed={visible} disabled={props.disabled} onClick={() => setVisible(value => !value)}>{visible ? 'Sembunyikan' : 'Tampilkan'}</button>
    </div>
  </div>;
}
