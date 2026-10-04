export type HppIngredient = {
  id: string; name: string; base_unit: string; unit_type: string;
  buy_price: number | string; buy_qty: number; cost_per_base_unit: number | string;
  ingredient_type: string; row_version: number; needs_review?: boolean;
};

export type HppProduct = { id: string; name: string; base_price: number | string; is_active: boolean; stock_enabled?: boolean };
export type HppRecipe = {
  id: string; product_id: string; notes?: string | null; total_cost: number; is_estimated?: boolean;
  ingredients: { ingredient_id: string; ingredient_name: string; quantity: number;
    quantity_unit: string; is_optional: boolean; notes?: string | null }[];
};

const units: Record<string, [string, number]> = {
  kg: ['gram', 1000], kilo: ['gram', 1000], kilogram: ['gram', 1000],
  g: ['gram', 1], gr: ['gram', 1], gram: ['gram', 1], ons: ['gram', 100], kwintal: ['gram', 100000],
  l: ['ml', 1000], liter: ['ml', 1000], ml: ['ml', 1], mililiter: ['ml', 1], cc: ['ml', 1], galon: ['ml', 19000],
  pcs: ['pcs', 1], butir: ['pcs', 1], buah: ['pcs', 1], biji: ['pcs', 1],
  tray: ['pcs', 30], dus: ['pcs', 12], lusin: ['pcs', 12], papan: ['pcs', 30],
  ekor: ['pcs', 1], ikat: ['pcs', 1], botol: ['pcs', 1], kaleng: ['pcs', 1],
  lembar: ['pcs', 1], sisir: ['pcs', 1], porsi: ['pcs', 1],
  bungkus: ['bungkus', 1], bks: ['bungkus', 1], pack: ['bungkus', 1],
  sachet: ['bungkus', 1], pak: ['bungkus', 1], renceng: ['bungkus', 1],
};

export function convertHppQuantity(quantity: number, from: string, to: string): number | null {
  if (!Number.isFinite(quantity) || quantity <= 0) return null;
  const a = from.toLowerCase().trim();
  const b = to.toLowerCase().trim();
  if (a === b) return quantity;
  if (!units[a] || !units[b] || units[a][0] !== units[b][0]) return null;
  return quantity * units[a][1] / units[b][1];
}

// Existing recipes use the backend's HPP rules. Stock still deducts raw quantity;
// new or explicitly reviewed rows must be saved in the ingredient's base unit.
export function existingHppQuantity(quantity: number, unit: string, base: string): number | null {
  if (!Number.isFinite(quantity) || quantity <= 0) return null;
  const a = unit.toLowerCase().trim();
  const b = base.toLowerCase().trim();
  if (!a || a === b) return quantity;
  return units[a]?.[0] === b ? quantity * units[a][1] : null;
}

export function hppUnits(base: string): string[] {
  const family = units[base.toLowerCase().trim()]?.[0];
  const choices = family === 'gram' ? ['gram', 'kg'] : family === 'ml' ? ['ml', 'liter'] : [base];
  return [...new Set([...choices, base])];
}

export const hppMoney = (value: number) => new Intl.NumberFormat('id-ID', {
  style: 'currency', currency: 'IDR', maximumFractionDigits: 2,
}).format(value);
export const hppNumber = (value: number) => new Intl.NumberFormat('id-ID', { maximumFractionDigits: 6 }).format(value);
