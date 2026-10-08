import { redirect } from 'next/navigation';

// Link lama "Masuk akun lama dengan kode atau Google" sekarang jadi halaman masuk utama.
export default function LegacyLogin() {
  redirect('/login');
}
