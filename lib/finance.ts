export interface FinanceCategory { key: string; label: string }
export type FinanceResult<T> = { success: true; data: T; message?: string } | { success: false; message: string; uncertain?: boolean };
export interface FinanceSetup {
  outlets: { id: string; name: string }[]; categories: FinanceCategory[]; accounts: FinanceAccount[];
  suppliers: { id: string; name: string; is_active: boolean }[]; selectedOutletId?: string;
  canManage?: boolean; managed?: boolean; includeGlobal?: boolean;
}
export interface FinanceAccount { id: string; name: string; kind: string; default_for: string[]; is_active: boolean }
export interface FinanceExpense {
  id: string; category: string; category_label: string; amount: string; paid_at: string; payment_method: string;
  cash_account_id?: string | null; cash_account_name?: string | null; supplier_id?: string | null; supplier_name?: string | null;
  purchase_id?: string | null; note?: string | null; recurring: string; row_version: number;
}
export interface FinanceSummary {
  month: string; outlet_id: string; revenue: string; refunds: string; net_revenue: string; delivery_fees?: string;
  cogs: string; cogs_coverage: number; gross_profit: string; gross_margin_pct: number;
  expenses_total: string; petty_cash_out: string; net_profit: string; net_margin_pct: number; orders_count: number;
  expenses_by_category: { key: string; label: string; amount: string; count: number }[];
  cash_in: string; cash_out: string; cash_net: string;
  accounts: { id: string | null; name: string; kind: string; inflow: string; outflow: string; net: string }[];
  purchases_paid: string; payables_outstanding: string; payables_overdue?: string;
  trend: { month: string; label: string; revenue: string; cogs: string; expenses: string; net: string }[];
  recurring_pending: number; generated_at?: string; report_timezone?: string; cash_history_estimated?: boolean;
}

export const money = (value: number | string | null | undefined) => value == null ? 'Tidak diizinkan' : new Intl.NumberFormat('id-ID', {
  style: 'currency', currency: 'IDR', minimumFractionDigits: 2, maximumFractionDigits: 2,
}).format(Number(value));

export function jakartaDate(value = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Jakarta', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(value);
  const part = (name: string) => parts.find(p => p.type === name)!.value;
  return `${part('year')}-${part('month')}-${part('day')}`;
}

export const monthName = (month: string) => new Intl.DateTimeFormat('id-ID', {
  timeZone: 'UTC', month: 'long', year: 'numeric',
}).format(new Date(`${month}-01T00:00:00Z`));

export function moveMonth(month: string, delta: number): string {
  const [year, num] = month.split('-').map(Number);
  return new Date(Date.UTC(year, num - 1 + delta, 1)).toISOString().slice(0, 7);
}

export function reportCsv(summary: FinanceSummary, expenses: FinanceExpense[], outletName: string): string {
  const rows: (string | number)[][] = [
    ['Laporan operasional keuangan'], ['Outlet', outletName], ['Periode', summary.month], ['Zona waktu', summary.report_timezone || 'Asia/Jakarta'],
    ['Dibuat pada', summary.generated_at || 'Tidak tersedia'],
    ['Dasar laba', 'HPP terkini dan biaya yang sudah dicatat; bukan saldo kas'],
    ['Kelengkapan HPP (%)', summary.cogs_coverage * 100],
    ['Riwayat kas perkiraan', summary.cash_history_estimated ? 'Ya' : 'Tidak'], [],
    ['Ringkasan', 'Nominal (IDR)'],
    ...([
      ['Penjualan sebelum refund', summary.revenue], ['Refund', summary.refunds], ['Ongkir', summary.delivery_fees || '0'],
      ['HPP terjual', summary.cogs], ['Laba kotor perkiraan', summary.gross_profit],
      ['Pengeluaran', summary.expenses_total], ['Kas kecil', summary.petty_cash_out], ['Laba setelah biaya tercatat (perkiraan)', summary.net_profit],
      ['Kas masuk', summary.cash_in], ['Kas keluar', summary.cash_out], ['Perubahan kas', summary.cash_net],
      ['Pembayaran nota', summary.purchases_paid], ['Utang supplier saat ini', summary.payables_outstanding],
      ['Utang lewat jatuh tempo saat ini', summary.payables_overdue || '0'],
    ] as string[][]).map(([label, value]) => [label, Number(value)]), [],
    ['Akun', 'Masuk (IDR)', 'Keluar (IDR)', 'Perubahan (IDR)'],
    ...summary.accounts.map(a => [a.name, Number(a.inflow), Number(a.outflow), Number(a.net)]), [],
    ['Pengeluaran', 'Tanggal (WIB)', 'Kategori', 'Catatan', 'Nominal (IDR)', 'Metode', 'Akun', 'Supplier', 'Nota terkait'],
    ...expenses.map(e => [e.id, jakartaDate(new Date(e.paid_at)), e.category_label, e.note || '', Number(e.amount), e.payment_method,
      e.cash_account_name || '', e.supplier_name || '', e.purchase_id || '']),
  ];
  const cell = (value: string | number) => {
    const text = typeof value === 'number' ? value.toFixed(2) : (/^[\s]*[=+\-@\t\r]/.test(value) ? `'${value}` : value);
    return `"${text.replaceAll('"', '""')}"`;
  };
  return '\uFEFF' + rows.map(row => row.map(cell).join(',')).join('\r\n');
}
