import { Suspense } from 'react';
import { AuthFlow } from '@/components/auth/auth-flow';

// Pintu utama pemilik: Google atau kode Sefrekuensi (cadangan WhatsApp).
export default function LoginPage() {
  return <Suspense fallback={<p className="auth-loading" role="status">Memuat halaman masuk…</p>}><AuthFlow mode="login" /></Suspense>;
}
