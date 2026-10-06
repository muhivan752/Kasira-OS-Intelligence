import { Suspense } from 'react';
import { PasswordFlow } from '@/components/auth/password-flow';

export default function RegisterPage() {
  return <Suspense fallback={<p className="auth-loading" role="status">Memuat pendaftaran…</p>}><PasswordFlow mode="register" /></Suspense>;
}
