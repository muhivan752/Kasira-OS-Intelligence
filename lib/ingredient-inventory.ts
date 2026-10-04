import type { HppIngredient } from './hpp';

export type InventoryIngredient = HppIngredient & {
  brand_id?: string; current_stock?: number | null; min_stock?: number | null;
  overhead_cost_per_day?: number | string | null;
  used_in?: { product_name: string; qty_per_serving: number; unit: string }[] | null;
};

export function hasRecordedStock(ingredient: InventoryIngredient): boolean {
  return ingredient.current_stock != null && Number.isFinite(Number(ingredient.current_stock));
}

export function hasLowStock(ingredient: InventoryIngredient): boolean {
  if (!hasRecordedStock(ingredient)) return false;
  const minimum = ingredient.min_stock == null ? 0 : Number(ingredient.min_stock);
  return Number(ingredient.current_stock) <= minimum;
}
