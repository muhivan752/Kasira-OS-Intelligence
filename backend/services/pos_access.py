import json
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException
from fastapi.routing import APIRoute
from sqlalchemy import select

from backend.services.access import denied


from backend.schemas.access import POS_PERMISSIONS

def route_rules():
    from backend.api.routes import categories, products, orders, payments, shifts, outlets, sync, ingredients, tables, tabs, devices, couriers, customers
    rules = {}

    def add(module, method, names, permissions):
        for name in names.split():
            rules[method, getattr(module, name)] = tuple(permissions.split())

    add(outlets, "GET", "read_outlets read_outlet", "pos.sell stock.view pos.kitchen sales.detail.view pos.shift.manage pos.cash.manage pos.refund pos.refund.approve")
    add(outlets, "GET", "get_tax_config", "pos.sell")
    add(categories, "GET", "read_categories read_category", "pos.sell stock.view")
    add(products, "GET", "read_products read_product read_product_variants", "pos.sell stock.view")
    add(products, "GET", "read_low_stock_products", "stock.view")
    add(products, "POST", "restock_product", "stock.receive")
    add(products, "POST", "stock_count_product", "stock.adjust")
    add(ingredients, "GET", "list_ingredients get_ingredient low_stock_ingredients", "stock.view")
    add(ingredients, "POST", "restock_ingredient", "stock.receive")
    add(orders, "POST", "create_order accept_online_order dispatch_delivery_order mark_order_delivered mark_order_delivery_failed", "pos.sell")
    add(orders, "POST", "reject_online_order", "pos.sell")
    add(orders, "PUT", "update_order_status", "pos.sell")
    add(orders, "GET", "read_orders read_order get_order_receipt", "pos.sell sales.detail.view")
    add(orders, "GET", "read_online_orders stream_orders", "pos.sell")
    add(orders, "GET", "read_kitchen_orders", "pos.kitchen")
    add(orders, "POST", "update_kitchen_status", "pos.kitchen")
    add(payments, "POST", "create_payment claim_print_receipt send_receipt_whatsapp", "pos.sell")
    add(payments, "GET", "get_payment_status read_payment read_payments", "pos.sell sales.detail.view")
    add(payments, "GET", "list_refunds", "pos.refund pos.refund.approve")
    add(payments, "POST", "request_refund", "pos.refund")
    add(payments, "POST", "approve_refund reject_refund", "pos.refund.approve")
    add(shifts, "GET", "get_current_shift", "pos.sell pos.shift.manage pos.cash.manage")
    add(shifts, "GET", "list_uncounted_shifts get_shift_review", "pos.shift.manage")
    add(shifts, "POST", "open_shift close_shift pause_shift", "pos.shift.manage")
    add(shifts, "GET", "get_cash_activities", "pos.cash.manage")
    add(shifts, "POST", "add_cash_activity", "pos.cash.manage")
    add(tables, "GET", "get_tables", "pos.sell")
    add(tabs, "GET", "list_tabs get_tab get_tab_by_table get_tab_items get_split_receipt", "pos.sell")
    add(tabs, "POST", "open_tab add_order_to_tab split_equal split_per_item split_custom pay_tab_full pay_split pay_items cancel_tab move_table merge_tab request_bill", "pos.sell")
    add(tabs, "PATCH", "update_guests", "pos.sell")
    add(devices, "POST", "register_device unregister_device", "pos.sell pos.kitchen")
    add(sync, "POST", "sync_data", "pos.sell stock.view sales.detail.view")
    add(couriers, "GET", "list_couriers", "pos.sell")
    add(customers, "GET", "lookup_customer_for_pos", "customers.lookup")
    from backend.schemas.access import BUSINESS_PERMISSIONS
    for endpoint in (outlets.read_outlets, outlets.read_outlet):
        rules["GET", endpoint] += tuple(BUSINESS_PERMISSIONS)
    for endpoint in (products.read_products, products.read_product, categories.read_categories, categories.read_category):
        rules["GET", endpoint] += ("hpp.view", "purchasing.view", "purchasing.manage")
    for endpoint in (ingredients.list_ingredients, ingredients.get_ingredient):
        rules["GET", endpoint] += ("hpp.view", "purchasing.view", "purchasing.manage")
    return rules


def supported_route(request):
    return (request.method, request.scope.get("endpoint")) in route_rules()


def require_any(context, permissions):
    if not any(context.allows(p) for p in permissions):
        denied("PERMISSION_DENIED", "Akses ini belum diberikan oleh pemilik usaha")


def as_id(value):
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(422, "ID tidak valid")


async def authorize(request, db, context):
    if context.mode != "managed":
        return
    permissions = route_rules().get((request.method, request.scope.get("endpoint")))
    if permissions is None:
        return
    require_any(context, permissions)
    from backend.models import Product, Category, Ingredient, Order, Payment, Outlet, Shift, Table, Tab
    from backend.models.payment_refund import PaymentRefund
    body = await request.json() if request.method in {"POST", "PUT", "PATCH"} and await request.body() else {}
    if not isinstance(body, dict):
        raise HTTPException(422, "Isi permintaan tidak valid")
    endpoint = request.scope["endpoint"]
    name = endpoint.__name__
    outlet_ids = set()
    for source in (request.path_params, request.query_params, body):
        if source.get("outlet_id"):
            oid = as_id(source["outlet_id"])
            context.require_outlet(oid)
            outlet_ids.add(oid)
    if len(outlet_ids) > 1:
        raise HTTPException(404, "Outlet tidak sesuai")
    outlet_id = next(iter(outlet_ids), None)
    brands = {o.brand_id for o in context.outlets}
    for source in (request.query_params, body):
        if source.get("brand_id"):
            bid = as_id(source["brand_id"])
            if bid not in brands or (outlet_id and not any(o.id == outlet_id and o.brand_id == bid for o in context.outlets)):
                raise HTTPException(404, "Brand tidak tersedia dalam akses outlet ini")

    async def resource(model, value):
        row = await db.scalar(select(model).where(model.id == as_id(value), model.deleted_at.is_(None)))
        if row is None:
            raise HTTPException(404, "Data tidak ditemukan")
        if hasattr(row, "tenant_id") and row.tenant_id != context.tenant_id:
            raise HTTPException(404, "Data tidak ditemukan")
        if hasattr(row, "outlet_id"):
            context.require_outlet(row.outlet_id)
            if outlet_id and row.outlet_id != outlet_id:
                raise HTTPException(404, "Data tidak sesuai outlet")
        if hasattr(row, "brand_id") and row.brand_id not in brands:
            raise HTTPException(404, "Data tidak tersedia dalam akses akun ini")
        if hasattr(row, "brand_id") and outlet_id and not any(o.id == outlet_id and o.brand_id == row.brand_id for o in context.outlets):
            raise HTTPException(404, "Data tidak sesuai brand outlet")
        return row

    resources = {}
    for key, model in {"product_id": Product, "category_id": Category, "ingredient_id": Ingredient,
                       "order_id": Order, "payment_id": Payment, "shift_id": Shift,
                       "table_id": Table, "tab_id": Tab, "shift_session_id": Shift}.items():
        for source in (request.path_params, request.query_params, body):
            if source.get(key):
                row = await resource(model, source[key])
                if key in resources and resources[key].id != row.id:
                    raise HTTPException(404, "Identitas data tidak sesuai")
                resources[key] = row
    if request.path_params.get("refund_id"):
        refund = await resource(PaymentRefund, request.path_params["refund_id"])
        resources["payment_id"] = await resource(Payment, refund.payment_id)
    payment = resources.get("payment_id")
    if payment:
        if payment.invoice_id or not (payment.order_id or payment.tab_id):
            denied("PERMISSION_DENIED", "Pembayaran di luar pesanan POS belum tersedia untuk akun staf")
        for key, model, parent_id in (("order_id", Order, payment.order_id), ("tab_id", Tab, payment.tab_id)):
            if parent_id:
                parent = await resource(model, parent_id)
                if key in resources and resources[key].id != parent.id:
                    raise HTTPException(404, "Parent pembayaran tidak sesuai")
                resources[key] = parent
    order = resources.get("order_id")
    if order and (request.method == "GET" or name == "create_payment") and not context.allows("sales.detail.view"):
        status = getattr(order.status, "value", order.status)
        if order.user_id != context.user_id and order.accepted_by != context.user_id and status in {"completed", "cancelled"}:
            own_tab = await db.scalar(select(Tab.id).where(Tab.id == order.tab_id,
                (Tab.opened_by == context.user_id) | (Tab.closed_by == context.user_id))) if order.tab_id else None
            if not own_tab:
                context.require("sales.detail.view")
    tab = resources.get("tab_id")
    if tab and (request.method == "GET" or name in {"pay_tab_full", "pay_split", "pay_items"}) and getattr(tab.status, "value", tab.status) in {"paid", "cancelled"} and tab.opened_by != context.user_id and tab.closed_by != context.user_id:
        context.require("sales.detail.view")
    for key in ("target_tab_id", "source_tab_id", "target_table_id", "new_table_id"):
        if body.get(key):
            target = await resource(Tab if "tab" in key else Table, body[key])
            if tab and target.outlet_id != tab.outlet_id:
                raise HTTPException(404, "Tujuan harus berada di outlet yang sama")
    resource_outlets = {r.outlet_id for r in resources.values() if hasattr(r, "outlet_id")}
    if len(resource_outlets) > 1:
        raise HTTPException(404, "Data harus berada di outlet yang sama")
    if name == "create_payment":
        if not order or body.get("invoice_id"):
            denied("PERMISSION_DENIED", "Pembayaran staf harus berasal dari pesanan POS")
        if body.get("idempotency_key"):
            replay = await db.scalar(select(Payment).where(Payment.idempotency_key == body["idempotency_key"], Payment.outlet_id == outlet_id))
            if replay and replay.order_id != order.id:
                raise HTTPException(409, "Kunci pembayaran sudah dipakai untuk pesanan lain")
    if name == "add_cash_activity":
        try:
            amount = Decimal(str(body.get("amount")))
        except Exception:
            raise HTTPException(422, "Jumlah kas tidak valid")
        if not amount.is_finite() or amount <= 0 or not 1 <= len(str(body.get("description", "")).strip()) <= 500:
            raise HTTPException(422, "Isi jumlah positif dan keperluan kas")
    if name == "sync_data":
        if outlet_id is None:
            raise HTTPException(422, "Pilih outlet untuk sinkronisasi")
        changes = body.get("changes", {})
        if not isinstance(changes, dict):
            raise HTTPException(422, "Perubahan sinkronisasi tidak valid")
        if any(changes.values()):
            denied("OFFLINE_SYNC_REVIEW_REQUIRED", "Antrean transaksi tetap tersimpan. Minta pemilik menyelesaikan sinkronisasi sebelum memakai akun staf dengan izin baru")
    if name in {"list_ingredients", "get_ingredient", "low_stock_ingredients", "read_products", "read_categories", "read_low_stock_products"} and outlet_id is None:
        raise HTTPException(422, "Pilih outlet untuk membaca katalog atau stok")
    if name == "restock_product" and body.get("unit_buy_price") is not None:
        context.require("hpp.manage")
    if name in {"list_couriers", "lookup_customer_for_pos"} and outlet_id is None:
        raise HTTPException(422, "Pilih outlet")
    if name in {"reject_online_order", "update_order_status"} and order and (name == "reject_online_order" or body.get("status") == "cancelled"):
        paid = await db.scalar(select(Payment.id).where(Payment.order_id == order.id, Payment.status == "paid", Payment.deleted_at.is_(None)))
        if paid or (order.tab_id and await db.scalar(select(Tab.id).where(Tab.id == order.tab_id, Tab.paid_amount > 0))):
            context.require("pos.refund.approve")
    if name == "cancel_tab" and tab and tab.paid_amount > 0:
        context.require("pos.refund.approve")
    if body.get("customer_id"):
        context.require("customers.lookup")
        from backend.models.customer import Customer
        await resource(Customer, body["customer_id"])
    request.state.pos_outlet = next((o for o in context.outlets if o.id == outlet_id), None)


COST_FIELDS = frozenset({"buy_price", "buy_qty", "cost_per_base_unit", "overhead_cost_per_day",
                         "hpp", "hpp_per_serving", "total_cost", "ingredient_cost", "cost_per_serving"})
SALES_COUNTERS = frozenset({"sold_today", "sold_total", "order_count"})
SHIFT_TOTALS = frozenset({"starting_cash", "expected_cash", "total_sales", "total_cash", "total_qris",
                          "expected_ending_cash", "ending_cash", "cash_in", "cash_out", "total_amount",
                          "total_card", "total_transfer", "total_cash_in", "total_cash_out", "cash_difference",
                          "difference", "variance", "variance_status", "cash_sales", "qris_sales", "card_sales", "transfer_sales"})
SECRETS = frozenset({"xendit_raw", "delivery_token", "fonnte_token", "xendit_api_key", "xendit_callback_token"})


def redact(value, context, module):
    if isinstance(value, list):
        return [redact(v, context, module) for v in value]
    if not isinstance(value, dict):
        return value
    result = {}
    if module == "shifts" and value.get("id") and not context.allows("sales.detail.view"):
        result.update(blind_close=True, is_owner=False)
    for key, item in value.items():
        if key in result:
            continue
        if key in SECRETS:
            continue
        if module == "shifts" and key in {"cash_payments", "review"} and not context.allows("sales.detail.view"):
            result[key] = []
        elif module == "shifts" and key == "activities" and not context.allows("pos.cash.manage"):
            result[key] = []
        elif module == "shifts" and key == "amount" and not context.allows("pos.cash.manage"):
            result[key] = None
        elif module == "shifts" and key in {"total_cash_sales", "total_qris_sales", "net_amount", "change_amount", "sales_count", "order_count"} and not context.allows("sales.detail.view"):
            result[key] = None
        elif key == "buy_price":
            result[key] = item if context.allows("supplier.price.view") else None
        elif key in COST_FIELDS and not context.allows("hpp.view"):
            result[key] = None
        elif key in SALES_COUNTERS and not context.allows("sales.detail.view"):
            result[key] = None
        elif module == "shifts" and key in SHIFT_TOTALS and not context.allows("sales.detail.view"):
            result[key] = None
        else:
            result[key] = redact(item, context, module)
    return result


async def validate_order(db, body, context):
    from backend.models import Product
    from backend.services.variant_utils import resolve_variant, variant_price
    brands = {o.brand_id for o in context.outlets if o.id == body.outlet_id}
    gross = Decimal(0)
    reductions = body.discount_amount
    for item in body.items:
        product = await db.scalar(select(Product).where(Product.id == item.product_id,
            Product.brand_id.in_(brands), Product.deleted_at.is_(None), Product.is_active.is_(True)))
        if not product:
            raise HTTPException(404, "Produk tidak tersedia di outlet ini")
        try:
            variant = await resolve_variant(db, product.id, item.product_variant_id)
        except ValueError as error:
            raise HTTPException(400, str(error))
        price = variant_price(product, variant)
        if item.unit_price != price:
            context.require("pos.discount.override")
        line_gross = item.unit_price * item.quantity
        if item.discount_amount > line_gross or item.total_price != line_gross - item.discount_amount:
            raise HTTPException(422, "Jumlah harga baris pesanan tidak sesuai")
        gross += line_gross
        reductions += item.discount_amount
    if reductions > gross:
        raise HTTPException(422, "Diskon melebihi nilai pesanan")
    if reductions > gross * Decimal("0.20"):
        context.require("pos.discount.override")
    body.subtotal = sum((item.total_price for item in body.items), Decimal(0))
    body.user_id = context.user_id


class PosAccessRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def scoped_handler(request):
            response = await handler(request)
            context = getattr(request.state, "access", None)
            if context and context.mode == "managed" and response.headers.get("content-type", "").startswith("application/json"):
                module = self.endpoint.__module__.rsplit(".", 1)[-1]
                payload = redact(json.loads(response.body), context, module)
                from backend.services.business_access import redact as redact_business
                payload = redact_business(payload, context, module)
                if self.endpoint.__name__ == "get_shift_review" and not context.allows("sales.detail.view"):
                    payload["data"] = []
                if self.endpoint.__name__ == "close_shift" and not context.allows("sales.detail.view"):
                    payload["message"] = "Hitungan kas tercatat"
                response.body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
                response.headers["content-length"] = str(len(response.body))
            return response

        return scoped_handler
