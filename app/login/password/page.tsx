import { redirect } from 'next/navigation';

// Sejak 9 Okt 2026 nomor HP/username + password ada di /login, tanpa username toko.
// Tautan lama (pesan WA karyawan, bookmark) tetap sampai ke layar yang benar.
export default function PasswordLoginPage() {
  redirect('/login');
}
