import { Suspense } from 'react';
import { AuthFlow } from '@/components/auth/auth-flow';

export default function RegisterPage() {
  return <Suspense fallback={<p className="auth-loading" role="status">Memuat pendaftaran…</p>}><AuthFlow mode="register" /></Suspense>;
}
