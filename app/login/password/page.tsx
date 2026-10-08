import { Suspense } from 'react';
import { PasswordFlow } from '@/components/auth/password-flow';

// Masuk pakai username toko + password: karyawan, dan pemilik yang sudah membuat password.
export default function PasswordLoginPage() {
  return <Suspense fallback={<p className="auth-loading" role="status">Memuat halaman masuk…</p>}><PasswordFlow mode="login" /></Suspense>;
}
