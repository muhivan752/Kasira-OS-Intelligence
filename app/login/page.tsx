import { Suspense } from 'react';
import { PasswordFlow } from '@/components/auth/password-flow';

export default function LoginPage() {
  return <Suspense fallback={<p className="auth-loading" role="status">Memuat halaman masuk…</p>}><PasswordFlow mode="login" /></Suspense>;
}
