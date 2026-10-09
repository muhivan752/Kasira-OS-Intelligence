from fastapi import HTTPException
from sqlalchemy import select

from backend.services.access import denied
from backend.services.pos_access import as_id, require_any


def route_rules():
    from backend.api.routes import finance, purchasing, recipes, ingredients, customer_workspace, reports
    rules = {}

    def add(module, method, names, grants):
        for name in names.split():
            rules[method, getattr(module, name)] = tuple(grants.split())

    add(finance, "GET", "finance_summary list_expenses", "finance.view")
    add(finance, "GET", "categories list_accounts", "finance.view finance.manage")
    add(finance, "PUT", "update_account update_expense", "finance.manage")
    add(finance, "POST", "create_expense copy_recurring", "finance.manage")
    add(finance, "DELETE", "delete_expense", "finance.manage")
    add(purchasing, "GET", "list_suppliers", "purchasing.view purchasing.manage finance.view finance.manage")
    add(purchasing, "GET", "purchase_summary list_purchases get_purchase", "purchasing.view")
    add(purchasing, "POST", "create_supplier create_purchase pay_purchase", "purchasing.manage")
    add(purchasing, "PUT", "update_supplier", "purchasing.manage")
    add(purchasing, "DELETE", "delete_supplier", "purchasing.manage")
    add(customer_workspace, "GET", "listing detail", "customers.view")
    add(customer_workspace, "POST", "create note", "customers.manage")
    add(customer_workspace, "PUT", "update", "customers.manage")
    add(recipes, "GET", "list_recipes get_hpp_report", "hpp.view")
    # Tab Laporan app (modal + margin per produk) = isi yang sama dengan
    # laporan HPP. Dulu tanpa gerbang: kasir legacy bisa membaca modal semua
    # produk, akun managed selalu ditolak walau diberi izin (9 Okt 2026).
    # App menyembunyikan tabnya dengan izin yang sama (SessionCache.canViewMargin).
    add(reports, "GET", "get_margin_report", "hpp.view hpp.manage")
    # Saran: pintu masuk untuk siapa pun yang boleh melihat salah satu jenis saran.
    # Jenis mana yang tampil dan siapa yang boleh menerapkan diputuskan di
    # services/suggestions.py (can_view / can_apply). Batalkan + periksa ulang: pemilik.
    from backend.api.routes import suggestions
    add(suggestions, "GET", "list_suggestions", "hpp.view stock.view")
    add(suggestions, "POST", "apply_suggestion skip_suggestion", "hpp.view stock.view")
    add(recipes, "POST", "create_recipe", "hpp.manage")
    add(recipes, "PUT", "update_recipe", "hpp.manage")
    add(recipes, "DELETE", "delete_recipe", "hpp.manage")
    add(ingredients, "POST", "create_ingredient", "hpp.manage")
    add(ingredients, "PUT", "update_ingredient", "hpp.manage")
    add(ingredients, "DELETE", "delete_ingredient", "hpp.manage")
    return rules


def supported_route(request):
    return (request.method, request.scope.get("endpoint")) in route_rules()


def include_global(context):
    return context is None or context.mode != "managed" or context.scope == "tenant"


def require_global(context):
    if not include_global(context):
        denied("TENANT_SCOPE_REQUIRED", "Perubahan data bersama ini memerlukan akses seluruh bisnis")


async def authorize(request, db, context):
    if context.mode != "managed":
        return
    grants = route_rules().get((request.method, request.scope.get("endpoint")))
    if grants is None:
        return
    require_any(context, grants)
    if not context.outlets:
        denied("OUTLET_ACCESS_REQUIRED", "Belum ada outlet aktif yang diizinkan untuk akun ini")
    from backend.models import Brand, Product, Ingredient, Recipe
    from backend.models.finance import Expense, CashAccount
    from backend.models.purchasing import Supplier, PurchaseOrder
    from backend.models.customer import Customer

    try:
        body = await request.json() if request.method in {"POST", "PUT", "PATCH"} and await request.body() else {}
    except ValueError:
        raise HTTPException(422, "Isi permintaan tidak valid") from None
    name = request.scope["endpoint"].__name__
    if not isinstance(body, dict):
        raise HTTPException(422, "Isi permintaan tidak valid")
    sources = (request.path_params, request.query_params, body)

    def values(source, key):
        return source.getlist(key) if hasattr(source, "getlist") else [source[key]] if source.get(key) else []

    outlets = {as_id(v) for s in sources for v in values(s, "outlet_id")}
    if len(outlets) > 1:
        raise HTTPException(404, "Outlet tidak sesuai")
    for oid in outlets:
        context.require_outlet(oid)
    outlet_id = next(iter(outlets), None)
    brands = {o.brand_id for o in context.outlets}
    explicit_brands = {as_id(v) for s in sources for v in values(s, "brand_id")}
    if len(explicit_brands) > 1:
        raise HTTPException(404, "Brand tidak sesuai")
    for bid in explicit_brands:
        if bid not in brands or (outlet_id and not any(o.id == outlet_id and o.brand_id == bid for o in context.outlets)):
            raise HTTPException(404, "Brand tidak tersedia dalam akses akun ini")
        if not await db.scalar(select(Brand.id).where(Brand.id == bid, Brand.tenant_id == context.tenant_id,
                                                      Brand.deleted_at.is_(None), Brand.is_active.is_(True))):
            raise HTTPException(404, "Brand tidak tersedia")

    async def resource(model, value):
        row = await db.scalar(select(model).where(model.id == as_id(value), model.deleted_at.is_(None)))
        if row is None or (hasattr(row, "tenant_id") and row.tenant_id != context.tenant_id):
            raise HTTPException(404, "Data tidak ditemukan")
        if hasattr(row, "outlet_id"):
            if row.outlet_id is None:
                if model is Expense or (model is CashAccount and name == "update_account"):
                    require_global(context)
            else:
                context.require_outlet(row.outlet_id)
                if outlet_id and row.outlet_id != outlet_id:
                    raise HTTPException(404, "Data tidak sesuai outlet")
        if hasattr(row, "brand_id"):
            if row.brand_id not in brands or (explicit_brands and row.brand_id not in explicit_brands):
                raise HTTPException(404, "Data tidak sesuai brand")
            if outlet_id and not any(o.id == outlet_id and o.brand_id == row.brand_id for o in context.outlets):
                raise HTTPException(404, "Data tidak sesuai outlet")
            if not await db.scalar(select(Brand.id).where(Brand.id == row.brand_id,
                Brand.tenant_id == context.tenant_id, Brand.deleted_at.is_(None), Brand.is_active.is_(True))):
                raise HTTPException(404, "Brand tidak tersedia")
        return row

    found = {}
    for key, model in {"expense_id": Expense, "account_id": CashAccount, "cash_account_id": CashAccount,
                       "purchase_id": PurchaseOrder, "supplier_id": Supplier, "customer_id": Customer,
                       "product_id": Product, "ingredient_id": Ingredient, "recipe_id": Recipe}.items():
        for source in sources:
            for value in values(source, key):
                row = await resource(model, value)
                if key in found and row.id != found[key].id:
                    raise HTTPException(404, "Identitas data tidak sesuai")
                found[key] = row
    recipe = found.get("recipe_id")
    product = found.get("product_id")
    if recipe:
        parent = await resource(Product, recipe.product_id)
        if product and product.id != parent.id:
            raise HTTPException(404, "Produk resep tidak sesuai")
        product = parent
    if name in {"create_recipe", "update_recipe", "delete_recipe", "create_ingredient", "update_ingredient", "delete_ingredient"}:
        # These endpoints persist immediately; editing a draft alone is a later AI workflow.
        context.require("hpp.approve")
    if name in {"create_expense", "copy_recurring", "list_expenses", "finance_summary", "create_purchase", "purchase_summary", "list_purchases"} and not outlet_id:
        if name == "create_expense":
            require_global(context)
        else:
            raise HTTPException(422, "Pilih outlet untuk laporan atau pencatatan")
    if name in {"create_purchase", "pay_purchase"}:
        context.require("supplier.price.view")
    if name == "create_purchase":
        lines = body.get("items", [])
        if not isinstance(lines, list):
            raise HTTPException(422, "Baris nota tidak valid")
        for line in lines:
            if not isinstance(line, dict):
                raise HTTPException(422, "Baris nota tidak valid")
            if any(line.get(key) for key in ("product_id", "ingredient_id", "new_product", "new_ingredient")):
                context.require("stock.receive")
            if line.get("new_product"):
                denied("CATALOG_ROUTE_NOT_READY", "Tambahkan produk melalui pemilik sebelum mencatat nota")
            if line.get("new_ingredient"):
                context.require("hpp.manage")
                context.require("hpp.approve")
            for key, model in (("product_id", Product), ("ingredient_id", Ingredient)):
                if line.get(key):
                    await resource(model, line[key])
    if name in {"create_recipe", "update_recipe"}:
        lines = body.get("ingredients", [])
        if not isinstance(lines, list):
            raise HTTPException(422, "Bahan resep tidak valid")
        for line in lines:
            if not isinstance(line, dict) or not line.get("ingredient_id"):
                raise HTTPException(422, "Bahan resep tidak valid")
            ing = await resource(Ingredient, line["ingredient_id"])
            if product is None or ing.brand_id != product.brand_id:
                raise HTTPException(404, "Bahan harus berasal dari brand produk yang sama")
    if request.scope["endpoint"].__module__.endswith("customer_workspace") and request.method == "GET" and request.query_params.get("export") == "true":
        context.require("customers.export")
    db.info["business_access"] = context


PURCHASE_PRICES = frozenset({
    "unit_price", "total_price", "total_amount", "paid_amount", "outstanding_amount", "amount",
    "month_total", "outstanding_total", "overdue_total", "next_due_amount", "purchase_total",
    "photo_url", "notes", "payments",
})


def redact(value, context, module):
    if isinstance(value, list):
        return [redact(v, context, module) for v in value]
    if not isinstance(value, dict):
        return value
    result = {}
    for key, item in value.items():
        if module == "purchasing" and key in PURCHASE_PRICES and not context.allows("supplier.price.view"):
            result[key] = [] if key == "payments" else None
        elif module == "purchasing" and key in {"cost_before", "cost_after"} and not (context.allows("hpp.view") and context.allows("supplier.price.view")):
            result[key] = None
        elif module == "finance" and key == "opening_balance" and not include_global(context):
            result[key] = None
        else:
            result[key] = redact(item, context, module)
    return result
