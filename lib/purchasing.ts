export type PurchaseResult<T> = { success: true; data: T; message?: string } | { success: false; message: string; uncertain?: boolean };
export interface Supplier {
  id: string; name: string; phone?: string | null; email?: string | null; address?: string | null; notes?: string | null;
  payment_terms_days: number; is_active: boolean; row_version: number;
  purchase_count: number; purchase_total: string; outstanding_total: string;
}
export interface PurchaseLine {
  id: string; ingredient_id?: string | null; product_id?: string | null; is_other: boolean; name: string;
  quantity: number; unit?: string | null; base_unit?: string | null; qty_base?: number | null; unit_price: string; total_price: string;
  cost_before?: string | null; cost_after?: string | null;
}
export interface Purchase {
  id: string; outlet_id: string; po_number: string; status: string; supplier_id?: string | null; supplier_name?: string | null;
  invoice_no?: string | null; photo_url?: string | null; notes?: string | null; received_at?: string | null;
  total_amount: string; paid_amount: string; outstanding_amount: string; due_at?: string | null;
  row_version: number; items: PurchaseLine[]; payments?: { id: string; kind: string; amount: string; paid_at: string }[];
  payment_history_incomplete?: boolean;
}
export interface PurchaseSummary {
  month: string; month_total: string; month_count: number; outstanding_total: string; outstanding_count: number;
  overdue_total: string; overdue_count: number; generated_at?: string;
  next_due_at?: string | null; next_due_supplier?: string | null; next_due_amount?: string | null;
}
export interface PurchaseSetup {
  outlets: { id: string; name: string; brand_id: string }[]; selectedOutletId?: string; isPro: boolean;
  canManage?: boolean; canRecord?: boolean; canReceive?: boolean; canCreateIngredient?: boolean; canScan?: boolean; managed?: boolean;
}
export interface PurchaseTarget { key: string; id: string; kind: 'ingredient' | 'product'; name: string; unit: string; stockEnabled?: boolean }
export interface PurchaseFilters { month?: string; unpaidOnly?: boolean; search?: string; skip?: number }
export interface PurchaseData { summary: PurchaseSummary; purchases: Purchase[]; suppliers: Supplier[]; hasNext: boolean }
export const purchaseDate = (iso?: string | null) => iso ? new Date(iso).toLocaleDateString('id-ID', {
  timeZone: 'Asia/Jakarta', day: 'numeric', month: 'short', year: 'numeric',
}) : 'Belum ditentukan';
export const quantityLabel = (value: number) => value.toLocaleString('id-ID', { maximumFractionDigits: 8 });
export const unitCost = (value: string) => new Intl.NumberFormat('id-ID', {
  style: 'currency', currency: 'IDR', minimumFractionDigits: 2, maximumFractionDigits: 8,
}).format(Number(value));
