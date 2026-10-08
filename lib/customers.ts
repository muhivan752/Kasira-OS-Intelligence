import type { FinanceResult } from './finance';

export type CustomerResult<T> = FinanceResult<T>;
export interface Customer {
  id: string; name: string; phone: string | null; email: string | null; notes: string | null;
  birthday: string | null; wa_marketing_consent: boolean; consent_given_at: string | null; row_version: number;
  total_visits: number; total_spent: string; avg_spent: string; first_visit_at: string | null; last_visit_at: string | null;
}
export interface CustomerList {
  items: Customer[]; total: number; skip: number; limit: number;
  summary: { total: number; repeat: number; spent: string; consented: number };
  generated_at: string; scope: string; timezone: string; basis: string; history_note: string; workspace_key: string;
  can_manage?: boolean; can_export?: boolean;
}
export interface CustomerDetail extends Customer {
  can_manage?: boolean; scope?: string;
  orders: { id: string; order_number: string; created_at: string; total_amount: string; items: { name: string; qty: number }[] }[];
  history_skip: number; history_limit: number; favourites: { id: string; name: string; qty: number }[];
  timeline: { id: string; kind: string; body: string; created_at: string }[]; timeline_limit: number;
}
export interface CustomerFilters { search: string; segment: string; sort: string; skip: number }
export interface CustomerSave {
  client_request_id: string; row_version?: number; name: string; phone: string | null; email: string | null;
  notes: string | null; birthday: string | null; wa_marketing_consent: boolean;
}
export interface CustomerNote { client_request_id: string; body: string; kind: 'note' | 'complaint' }
export const customerDate = (value: string | null) => value ? new Intl.DateTimeFormat('id-ID', {
  timeZone: 'Asia/Jakarta', day: 'numeric', month: 'short', year: 'numeric',
}).format(new Date(value.length === 10 ? `${value}T00:00:00+07:00` : value)) : 'Belum tercatat';

export function customerCsv(data: CustomerList): string {
  const rows: (string | number)[][] = [
    ['Data pelanggan', 'Halaman yang sedang ditampilkan'], ['Cakupan', data.scope === 'allowed_outlets' ? 'Outlet yang diizinkan' : 'Semua outlet dalam bisnis'],
    ['Dibuat pada', data.generated_at], ['Dasar belanja', data.history_note],
    ['Hasil filter', data.total], ['Baris awal', data.skip + 1], [],
    ['Nama', 'HP', 'Email', 'Transaksi lunas', 'Total nota (IDR)', 'Terakhir belanja (WIB)', 'Tanggal lahir', 'Preferensi / catatan'],
    ...data.items.map(c => [c.name, c.phone || '', c.email || '', c.total_visits, c.total_spent,
      customerDate(c.last_visit_at), c.birthday || '', c.notes || '']),
  ];
  return '\uFEFF' + rows.map(row => row.map(value => {
    const text = String(value);
    return `"${(/^[\s]*[=+\-@\t\r]/.test(text) ? `'${text}` : text).replaceAll('"', '""')}"`;
  }).join(',')).join('\r\n');
}
