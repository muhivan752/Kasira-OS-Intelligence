import { Suspense } from 'react';
import { AuthFlow } from '@/components/auth/auth-flow';

export default function LoginPage() {
  return <Suspense fallback={<p className="auth-loading" role="status">Memuat halaman masuk…</p>}><AuthFlow mode="login" /></Suspense>;
}
