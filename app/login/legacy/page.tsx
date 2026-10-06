import { Suspense } from 'react';
import { AuthFlow } from '@/components/auth/auth-flow';
export default function LegacyLogin() {
  return <Suspense fallback={<p role="status">Memuat akun lama…</p>}><AuthFlow mode="login" /></Suspense>;
}
