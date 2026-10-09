"""Alat Selaris AI untuk bahan: ubah harga beli dan tambah stok. 9 Okt 2026.

Rumah konsep:
- Alat di sini HANYA menyiapkan kartu konfirmasi. Tidak ada yang tersimpan sampai
  pengguna menekan Simpan, dan Simpan memanggil endpoint yang sama dengan halaman
  Bahan Baku dan Nota Belanja (PUT /ingredients/{id}, POST /ingredients/{id}/restock,
  POST /purchases). Jadi izin, audit, rata-rata bergerak HPP, dan utang nota tetap
  diputuskan di satu tempat; file ini tidak menulis ke database.
- Model hanya MENYALIN nama bahan, jumlah, satuan, dan harga dari ucapan pengguna.
  Konversi satuan, stok sebelum/sesudah, harga per satuan dasar, dan dampak ke modal
  produk dihitung kode di sini (qty_to_base_unit, moving_average, unit_utils), sama
  dengan yang dipakai nota belanja.
- Menggantikan jalur lama RESTOCK di ai_service yang langsung menambah stok tanpa
  konfirmasi.

Kalau salah, ketahuan dari: kartu menampilkan angka lama ke baru sebelum disimpan;
setelah disimpan, riwayat ada di audit_log + events (ingredient.price_updated,
stock.ingredient_restock) dan nota di Pembelian.
"""
from decimal import Decimal, ROUND_HALF_UP
from types import SimpleNamespace

from sqlalchemy import select, text

PRICE_TOOL = {"type": "function", "function": {
    "name": "ubah_harga_bahan",
    "description": ("Siapkan perubahan harga beli satu bahan baku yang SUDAH ADA di toko, misalnya 'harga gula aren "
                    "naik jadi 38 ribu per kg'. Hanya harga, stok tidak berubah. Kalau pengguna juga menyebut barang "
                    "datang atau baru dibeli, pakai tambah_stok. Belum tersimpan sampai pengguna menekan Simpan."),
    "parameters": {"type": "object", "properties": {
        "bahan": {"type": "string", "description": "Nama bahan seperti diucapkan pengguna."},
        "harga": {"type": "number", "description": "Harga dalam rupiah untuk jumlah dan satuan di bawah, disalin dari pengguna. 38 ribu = 38000."},
        "jumlah": {"type": "number", "description": "Jumlah yang dihargai, misalnya 1 untuk 'per kg'. Default 1."},
        "satuan": {"type": "string", "description": "Satuan yang disebut pengguna: kg, gram, liter, ml, pcs, butir, dan sebagainya."},
    }, "required": ["bahan", "harga", "satuan"]}}}

STOCK_TOOL = {"type": "function", "function": {
    "name": "tambah_stok",
    "description": ("Siapkan pencatatan bahan yang datang atau baru dibeli, misalnya 'baru beli susu 5 liter 90 ribu' "
                    "atau 'gula masuk 2 kg'. Kalau harga disebut, dicatat sebagai nota belanja dan harga modal bahan "
                    "ikut diperbarui. Belum tersimpan sampai pengguna menekan Simpan."),
    "parameters": {"type": "object", "properties": {
        "barang": {"type": "array", "items": {"type": "object", "properties": {
            "bahan": {"type": "string", "description": "Nama bahan seperti diucapkan pengguna."},
            "jumlah": {"type": "number"},
            "satuan": {"type": "string"},
            "harga_total": {"type": "number", "description": "Total rupiah untuk baris ini kalau disebut pengguna. Kosongkan kalau tidak disebut."},
        }, "required": ["bahan", "jumlah", "satuan"]}},
        "pemasok": {"type": "string", "description": "Nama toko/pemasok kalau disebut. Kosongkan kalau tidak."},
    }, "required": ["barang"]}}}


SELL_TOOL = {"type": "function", "function": {
    "name": "ubah_harga_jual",
    "description": ("Siapkan perubahan harga jual menu yang SUDAH ADA, misalnya 'naikkan kopi susu jadi 22 ribu'. "
                    "Bisa beberapa menu sekaligus. Isi SATU dari harga (harga akhir), naik_rupiah, atau naik_persen, "
                    "persis seperti yang diucapkan; turun ditulis negatif. Jangan menghitung sendiri, kode yang menghitung. "
                    "Belum tersimpan sampai pengguna menekan Simpan."),
    "parameters": {"type": "object", "properties": {
        "menu": {"type": "array", "items": {"type": "object", "properties": {
            "nama": {"type": "string", "description": "Nama menu seperti diucapkan pengguna."},
            "harga": {"type": "number", "description": "Harga jual akhir dalam rupiah kalau disebut. 22 ribu = 22000."},
            "naik_rupiah": {"type": "number", "description": "Kalau pengguna bilang naik/turun sekian rupiah. Turun 1 ribu = -1000."},
            "naik_persen": {"type": "number", "description": "Kalau pengguna bilang naik/turun sekian persen. Turun 5 persen = -5."},
        }, "required": ["nama"]}},
    }, "required": ["menu"]}}}


def _ok(access, *perms):
    return access.mode == "owner" or all(access.allows(p) for p in perms)


def tools_for(access, tenant) -> list:
    """Alat bahan yang boleh ditawarkan ke model, sesuai izin endpoint tujuan Simpan
    (business_access/pos_access). Bahan baku = fitur Pro."""
    from backend.services.subscription import is_pro_tier
    if not is_pro_tier(tenant) or not _ok(access, "ai.chat"):
        return []
    tools = []
    if _ok(access, "hpp.manage", "hpp.approve", "supplier.price.view"):
        tools.append(PRICE_TOOL)
    if _ok(access, "stock.receive"):
        tools.append(STOCK_TOOL)
    if access.mode == "owner":
        # PUT /products/{id} belum terdaftar untuk jabatan managed (access registry),
        # jadi harga jual = pemilik saja. Tawarkan sama dengan yang bisa disimpan.
        tools.append(SELL_TOOL)
    return tools


def can_record_purchase(access) -> bool:
    return _ok(access, "purchasing.manage", "supplier.price.view", "stock.receive")


def _num(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number and number not in (float("inf"), float("-inf")) else None


def _rp(value) -> int | None:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)) if value is not None else None


async def _bind(db, tenant_id):
    await db.execute(text("SELECT set_config('app.current_tenant_id', :t, true)"), {"t": str(tenant_id)})


async def _ingredients(db, brand_id):
    from backend.models.ingredient import Ingredient
    return (await db.execute(select(Ingredient).where(Ingredient.brand_id == brand_id,
        Ingredient.deleted_at.is_(None), Ingredient.ingredient_type == "recipe"))).scalars().all()


def match(ingredients, name: str):
    """(bahan, kandidat). Cocok persis dulu, lalu nama mengandung kata yang diucapkan.
    Lebih dari satu kandidat = tanya pengguna, jangan menebak."""
    key = " ".join((name or "").casefold().split())
    if not key:
        return None, []
    exact = [i for i in ingredients if " ".join(i.name.casefold().split()) == key]
    if len(exact) == 1:
        return exact[0], []
    near = [i for i in ingredients if key in i.name.casefold() or i.name.casefold() in key]
    if len(near) == 1:
        return near[0], []
    if not near:
        words = [w for w in key.split() if len(w) > 2]
        near = [i for i in ingredients if words and all(w in i.name.casefold() for w in words)]
        if len(near) == 1:
            return near[0], []
    return None, near[:6]


async def _stock(db, outlet_id, ingredient_id) -> float:
    from backend.models.product import OutletStock
    value = (await db.execute(select(OutletStock.computed_stock).where(OutletStock.outlet_id == outlet_id,
        OutletStock.ingredient_id == ingredient_id, OutletStock.deleted_at.is_(None)))).scalar_one_or_none()
    return float(value or 0)


def recipe_modal(recipe, costs: dict | None = None):
    """(modal_sekarang, modal_dengan_costs) satu resep, atau None kalau ada satuan yang
    tidak bisa dikonversi. Satu-satunya hitungan modal di modul ini; filter 5 kondisi
    resep sama dengan compute HPP (CLAUDE.md), pakai helper unit_utils."""
    from backend.services.unit_utils import decimal_ingredient_cost_contribution, normalize_recipe_qty
    costs = costs or {}
    before = after = Decimal("0")
    for ri in recipe.ingredients:
        if not (ri.deleted_at is None and not ri.is_optional and ri.quantity > 0
                and ri.ingredient is not None and ri.ingredient.deleted_at is None):
            continue
        part = decimal_ingredient_cost_contribution(ri)
        if part is None:
            return None
        before += part
        if ri.ingredient_id in costs:
            after += Decimal(str(normalize_recipe_qty(ri))) * Decimal(str(costs[ri.ingredient_id]))
        else:
            after += part
    return before, after


def _active_recipes(product_ids=None, ingredient_ids=None):
    from sqlalchemy.orm import selectinload
    from backend.models.recipe import Recipe, RecipeIngredient
    q = select(Recipe).where(Recipe.is_active.is_(True), Recipe.deleted_at.is_(None)).options(
        selectinload(Recipe.ingredients).selectinload(RecipeIngredient.ingredient))
    if product_ids is not None:
        q = q.where(Recipe.product_id.in_(list(product_ids)))
    if ingredient_ids is not None:
        q = q.where(Recipe.id.in_(select(RecipeIngredient.recipe_id).where(
            RecipeIngredient.ingredient_id.in_(list(ingredient_ids)), RecipeIngredient.deleted_at.is_(None))))
    return q


async def product_impact(db, brand_id, costs: dict) -> list:
    """Modal per porsi produk yang memakai bahan di `costs` ({ingredient_id: biaya baru per satuan dasar}),
    sebelum dan sesudah."""
    from backend.models.product import Product
    if not costs:
        return []
    recipes = (await db.execute(_active_recipes(ingredient_ids=costs))).scalars().all()
    products = {p.id: p for p in (await db.execute(select(Product).where(Product.id.in_([r.product_id for r in recipes]),
        Product.brand_id == brand_id, Product.deleted_at.is_(None)))).scalars().all()} if recipes else {}
    out = []
    for recipe in recipes:
        product, modal = products.get(recipe.product_id), recipe_modal(recipe, costs)
        if not product or modal is None:
            continue
        before, after = modal
        price = float(product.base_price) if product.base_price else None
        out.append({"produk": product.name, "modal_lama": _rp(before), "modal_baru": _rp(after),
            "margin_baru": round((price - float(after)) / price * 100, 1) if price else None, "harga_jual": price})
    out.sort(key=lambda r: abs((r["modal_baru"] or 0) - (r["modal_lama"] or 0)), reverse=True)
    return out[:6]


def _unit_label(qty, base_unit):
    return f"{qty:,.0f} {base_unit}".replace(",", ".") if qty == int(qty) else f"{qty:,.2f} {base_unit}".replace(",", "X").replace(".", ",").replace("X", ".")


async def run_price_tool(db, *, user, outlet, bahan, harga, jumlah, satuan):
    from backend.services.purchasing_service import qty_to_base_unit
    await _bind(db, user.tenant_id)
    ingredients = await _ingredients(db, outlet.brand_id)
    ing, candidates = match(ingredients, bahan)
    if not ing:
        return {"status": "perlu_pilih" if candidates else "tidak_ditemukan", "bahan": bahan,
                "kandidat": [c.name for c in candidates],
                "pesan": "Tanyakan bahan mana yang dimaksud." if candidates else
                         "Bahan belum ada di daftar. Bahan baru dibuat lewat susun_resep atau halaman Bahan Baku."}, None
    price, qty = _num(harga), _num(jumlah) or 1.0
    if price is None or price <= 0 or qty <= 0:
        return {"status": "gagal", "pesan": "Tanyakan harga dan jumlahnya, misalnya Rp 38.000 per 1 kg."}, None
    base_qty = qty_to_base_unit(qty, satuan, ing.base_unit)
    if base_qty is None or base_qty <= 0:
        return {"status": "gagal", "pesan": f"{ing.name} dihitung dalam {ing.base_unit}; satuan {satuan} tidak bisa dikonversi. "
                "Tanyakan harga dalam satuan yang sesuai."}, None
    from backend.services.hpp_math import UNIT_COST
    old_cost = Decimal(str(ing.cost_per_base_unit or 0))
    new_cost = (Decimal(str(price)) / Decimal(str(base_qty))).quantize(UNIT_COST, rounding=ROUND_HALF_UP)
    impact = await product_impact(db, outlet.brand_id, {ing.id: new_cost})
    card = {"type": "ingredient_price", "ingredient_id": str(ing.id), "row_version": ing.row_version,
        "bahan": ing.name, "base_unit": ing.base_unit,
        "harga_lama": float(ing.buy_price or 0), "jumlah_lama": float(ing.buy_qty or 1),
        "harga_baru": float(price), "jumlah_baru": float(base_qty),
        "biaya_lama": float(old_cost), "biaya_baru": float(new_cost), "produk": impact}
    result = {"status": "kartu_siap", "bahan": ing.name, "harga_baru": f"Rp {_rp(price):,} per {_unit_label(base_qty, ing.base_unit)}".replace(",", "."),
              "harga_lama": f"Rp {_rp(ing.buy_price or 0):,} per {_unit_label(float(ing.buy_qty or 1), ing.base_unit)}".replace(",", "."),
              "dampak_modal_produk": impact,
              "catatan": "Belum tersimpan. Pengguna menekan Simpan di kartu. Sebut angka dari hasil ini saja."}
    return result, card


async def run_stock_tool(db, *, user, access, outlet, barang, pemasok=None):
    from backend.services.purchasing_service import moving_average, qty_to_base_unit
    from backend.services.hpp_math import UNIT_COST
    await _bind(db, user.tenant_id)
    ingredients = await _ingredients(db, outlet.brand_id)
    may_buy = can_record_purchase(access)
    lines, problems, costs = [], [], {}
    for item in (barang or [])[:20]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("bahan") or "")
        ing, candidates = match(ingredients, name)
        if not ing:
            problems.append({"bahan": name, "kandidat": [c.name for c in candidates],
                "masalah": "pilih salah satu" if candidates else "belum ada di daftar bahan"})
            continue
        qty, unit = _num(item.get("jumlah")), str(item.get("satuan") or "")
        base_qty = qty_to_base_unit(qty, unit, ing.base_unit) if qty and qty > 0 else None
        if not base_qty or base_qty <= 0:
            problems.append({"bahan": ing.name, "masalah": f"jumlah atau satuan tidak jelas; {ing.name} dihitung dalam {ing.base_unit}"})
            continue
        total = _num(item.get("harga_total"))
        total = total if total and total > 0 and may_buy else None
        before = await _stock(db, outlet.id, ing.id)
        line = {"ingredient_id": str(ing.id), "bahan": ing.name, "jumlah": qty, "satuan": unit or ing.base_unit,
                "jumlah_dasar": base_qty, "base_unit": ing.base_unit, "stok_lama": before, "stok_baru": before + base_qty,
                "harga_total": total, "biaya_lama": float(ing.cost_per_base_unit or 0), "biaya_baru": None}
        if total:
            new_cost = (Decimal(str(total)) / Decimal(str(base_qty))).quantize(UNIT_COST, rounding=ROUND_HALF_UP)
            after = moving_average(before, Decimal(str(ing.cost_per_base_unit or 0)), base_qty, new_cost, precision=UNIT_COST)
            line["biaya_baru"] = float(after)
            costs[ing.id] = after
        lines.append(line)
    if not lines:
        return {"status": "gagal", "masalah": problems,
                "pesan": "Tanyakan ulang bahan dan jumlahnya. Bahan baru dibuat lewat susun_resep atau halaman Bahan Baku."}, None
    priced = [l for l in lines if l["harga_total"]]
    impact = await product_impact(db, outlet.brand_id, costs)
    card = {"type": "stock_in", "outlet_id": str(outlet.id), "pemasok": (pemasok or "").strip()[:120] or None,
            "lines": lines, "nota": bool(priced), "total": sum(l["harga_total"] for l in priced) if priced else None,
            "produk": impact, "masalah": problems}
    result = {"status": "kartu_siap", "dicatat_sebagai": "nota belanja" if priced else "stok masuk tanpa harga",
              "baris": [{"bahan": l["bahan"], "masuk": _unit_label(l["jumlah_dasar"], l["base_unit"]),
                         "stok_sesudah": _unit_label(l["stok_baru"], l["base_unit"]),
                         "harga_total": l["harga_total"]} for l in lines],
              "belum_bisa": problems, "dampak_modal_produk": impact,
              "catatan": ("Harga tidak dicatat karena akun ini tidak punya izin pembelian. " if not may_buy else "")
                         + "Belum tersimpan. Pengguna menekan Simpan di kartu."}
    return result, card


def new_sell_price(old: Decimal, item: dict):
    """Harga jual baru dari ucapan pengguna. Model hanya menyalin angka; hitungan di sini.
    Persen dibulatkan ke Rp500 terdekat (kebiasaan harga menu); rupiah dan harga akhir apa adanya.
    Kartu menampilkan cara hitungnya dan angkanya bisa diubah sebelum Simpan."""
    price, plus, pct = _num(item.get("harga")), _num(item.get("naik_rupiah")), _num(item.get("naik_persen"))
    if price is not None and price > 0:
        new, how = Decimal(str(price)), "harga akhir"
    elif plus is not None and plus != 0:
        new, how = old + Decimal(str(plus)), f"{'naik' if plus > 0 else 'turun'} {rupiah_text(abs(plus))}"
    elif pct is not None and pct != 0 and old > 0:
        raw = old * (Decimal(1) + Decimal(str(pct)) / 100)
        new = (raw / 500).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * 500
        how = f"{'naik' if pct > 0 else 'turun'} {abs(pct):g}% dari {rupiah_text(old)}, dibulatkan ke Rp500"
    else:
        return None, None
    new = new.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return (new, how) if Decimal(0) < new < Decimal("10000000000") else (None, None)


def rupiah_text(value) -> str:
    return "Rp " + f"{_rp(value):,}".replace(",", ".")


async def run_sell_price_tool(db, *, user, outlet, menu):
    """Kartu ubah harga jual. Harga lama, modal resep, margin, dan harga varian dihitung kode;
    Simpan memanggil PUT /products/{id} (izin dan audit di sana)."""
    from backend.models.product import Product, ProductVariant
    from backend.services.variant_utils import variant_price
    await _bind(db, user.tenant_id)
    products = (await db.execute(select(Product).where(Product.brand_id == outlet.brand_id,
        Product.deleted_at.is_(None)))).scalars().all()
    rows, problems = [], []
    for item in (menu or [])[:20]:
        if not isinstance(item, dict):
            continue
        name = str(item.get("nama") or "")
        product, candidates = match(products, name)
        if not product:
            problems.append({"menu": name, "kandidat": [c.name for c in candidates],
                             "masalah": "pilih salah satu" if candidates else "belum ada di daftar menu"})
            continue
        new, how = new_sell_price(Decimal(str(product.base_price or 0)), item)
        if new is None:
            problems.append({"menu": product.name, "masalah": "harga baru tidak jelas"})
            continue
        rows.append((product, new, how))
    if not rows:
        return {"status": "gagal", "masalah": problems, "pesan": "Tanyakan menu dan harga akhirnya."}, None
    ids = [p.id for p, _, _ in rows]
    recipes = {r.product_id: r for r in (await db.execute(_active_recipes(product_ids=ids))).scalars().all()}
    variants = (await db.execute(select(ProductVariant).where(ProductVariant.product_id.in_(ids),
        ProductVariant.deleted_at.is_(None), ProductVariant.is_active.is_(True))
        .order_by(ProductVariant.sort_order))).scalars().all()
    lines = []
    for product, new, how in rows:
        old = Decimal(str(product.base_price or 0))
        computed = recipe_modal(recipes[product.id]) if product.id in recipes else None
        modal = computed[0] if computed else None
        margin = lambda price: round(float((price - modal) / price * 100), 1) if modal is not None and price > 0 else None
        mine = [v for v in variants if v.product_id == product.id]
        lines.append({"product_id": str(product.id), "row_version": product.row_version, "menu": product.name, "cara": how,
            "harga_lama": _rp(old), "harga_baru": _rp(new), "modal": _rp(modal) if modal is not None else None,
            "margin_lama": margin(old), "margin_baru": margin(new),
            "di_bawah_modal": bool(modal is not None and new <= modal),
            "lonjakan": bool(old > 0 and (new > old * 3 or new * 3 < old)),
            # Harga varian lewat variant_price (satu rumah, termasuk clamp ke 0).
            "varian": [{"nama": v.name, "lama": _rp(variant_price(product, v)),
                        "baru": _rp(variant_price(SimpleNamespace(id=product.id, base_price=new), v))} for v in mine][:8]})
    card = {"type": "sell_price", "lines": lines, "masalah": problems}
    result = {"status": "kartu_siap", "menu": [{k: l[k] for k in ("menu", "harga_lama", "harga_baru", "modal", "margin_lama",
              "margin_baru", "di_bawah_modal")} for l in lines], "belum_bisa": problems,
              "catatan": "Belum tersimpan. Pengguna menekan Simpan di kartu. Harga varian ikut bergeser karena varian menyimpan selisih."}
    return result, card
