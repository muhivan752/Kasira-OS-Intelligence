import { AccountSettings } from '@/components/auth/account-settings';
import { AccountDeletion } from '@/components/auth/account-deletion';
import '../keuangan/finance.css';
export default function AccountPage() { return <div className="finance-workspace"><h1>Akun saya</h1><AccountSettings /><AccountDeletion /></div>; }
