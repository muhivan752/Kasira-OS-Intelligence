export type HppChatMode = 'manual' | 'estimate';
export type HppChatLine = {
  name: string; ingredient_id: string | null; action: 'create' | 'reuse' | 'update_price';
  quantity: string | null; unit: string; input_quantity: string | null; input_unit: string;
  basis: 'portion' | 'batch'; buy_price: string | null; buy_qty: string | null;
  unit_cost: string | null; old_unit_cost: string | null; line_cost: string | null;
  purchase_description?: string;
  quantity_source: string; price_source: string; quantity_evidence: string;
  price_evidence: string; affected_products: string[]; is_estimated: boolean;
  is_optional: boolean; notes: string;
};
export type HppChatPreview = {
  product_name: string; product_id: string | null; new_product: boolean;
  replaces_recipe: boolean; servings: string | null; servings_source: string;
  servings_evidence: string; lines: HppChatLine[]; is_estimated: boolean;
  ready: boolean; missing: string[]; total_cost: string | null; fingerprint: string;
  notes: string;
};
export type HppChatSession = {
  id: string; outlet_id: string; mode: HppChatMode; status: 'draft' | 'applied';
  revision: number; preview: HppChatPreview | null; pending: boolean;
  retry_allowed: boolean; error: string | null;
  result: { product_id: string; recipe_id: string; new_product: boolean;
    total_cost: string; is_estimated: boolean } | null;
  turns: { id: string; mode: HppChatMode; message: string; reply: string | null }[];
};
export type HppChatListItem = { id: string; name: string; status: string; updated_at: string };
export type HppChatResult<T> = { success: true; data: T } | { success: false; message: string };
