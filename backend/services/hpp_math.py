"""Purchase and portion arithmetic, independent of any model/provider."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from backend.services.unit_utils import UNIT_ALIASES

MONEY = Decimal("0.01")
UNIT_COST = Decimal("0.00000001")
MAX_VALUE = Decimal("9999999999")


def number(value, *, zero=False) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("Angka tidak valid")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Angka tidak valid") from None
    if not result.is_finite() or result > MAX_VALUE or result < 0 or (not zero and result == 0):
        raise ValueError("Jumlah harus positif dan harga tidak boleh negatif")
    return result


def unit(value: str) -> tuple[str, Decimal]:
    value = value.strip().lower()
    # Package aliases such as tray/dus/papan are not physical conversion factors:
    # pack contents differ by merchant. Only unambiguous physical units convert.
    known = {key: val for key, val in UNIT_ALIASES.items() if val[0] in ("gram", "ml") and key != "galon"}
    known.update({key: ("pcs", 1) for key in ("pcs", "buah", "butir", "biji", "ekor", "lembar")})
    known.update({key: ("bungkus", 1) for key in ("bungkus", "bks", "pack", "sachet", "pak")})
    if value in known:
        family, factor = known[value]
        return family, Decimal(str(factor))
    if not value or len(value) > 30:
        raise ValueError("Satuan belum diisi")
    return value, Decimal(1)


def convert(value, source: str, target: str) -> Decimal:
    source_family, source_factor = unit(source)
    target_family, target_factor = unit(target)
    if source_family != target_family:
        raise ValueError(f"Satuan {source} tidak bisa diubah ke {target}; isi ukuran yang sesuai")
    return number(value) * source_factor / target_factor


def purchase_cost(price, quantity, purchase_unit: str, base_unit: str, *, pack_size=None, pack_unit="") -> tuple[Decimal, Decimal]:
    price = number(price, zero=True)
    if price != price.quantize(MONEY, rounding=ROUND_HALF_UP):
        raise ValueError("Harga pembelian maksimal dua angka desimal")
    if pack_size is None:
        bought = convert(quantity, purchase_unit, base_unit)
    else:
        if unit(purchase_unit)[0] in ("gram", "ml"):
            raise ValueError("Pembelian kg/liter memakai konversi langsung, tanpa ukuran kemasan")
        bought = number(quantity) * convert(pack_size, pack_unit, base_unit)
    cost = (price / bought).quantize(UNIT_COST, rounding=ROUND_HALF_UP)
    if cost > MAX_VALUE or (price > 0 and cost == 0):
        raise ValueError("Harga per satuan di luar ketelitian penyimpanan")
    return bought, cost


def purchase_total(price, quantity, basis="total") -> Decimal:
    amount = number(price, zero=True)
    if basis not in ("total", "per_unit"):
        raise ValueError("Harga harus menyebut total pembelian atau harga per satuan beli")
    precision = MONEY if basis == "total" else UNIT_COST
    if amount != amount.quantize(precision, rounding=ROUND_HALF_UP):
        raise ValueError("Ketelitian harga pembelian tidak valid")
    total = amount * number(quantity) if basis == "per_unit" else amount
    total = number(total, zero=True)
    if total != total.quantize(MONEY, rounding=ROUND_HALF_UP):
        raise ValueError("Total harga belum sesuai ketelitian rupiah; isi total pembelian dari nota")
    return total


def portion_quantity(quantity, quantity_unit: str, base_unit: str, servings, basis: str) -> Decimal:
    count = number(servings)
    if basis not in ("portion", "batch"):
        raise ValueError("Takaran harus menyebut satu porsi atau satu batch")
    canonical = convert(quantity, quantity_unit, base_unit)
    result = canonical / count if basis == "batch" else canonical
    # Recipes and stock use Float columns. Quantize through their stored value
    # before computing the preview so approval and later recipe reads agree.
    return number(float(result))


def line_cost(quantity, base_unit: str, ingredient) -> Decimal:
    from backend.services.unit_utils import decimal_cost_from_qty_unit
    # Canonical quantity is saved in base_unit, including legacy kg/liter bases.
    contribution = decimal_cost_from_qty_unit(quantity, base_unit, ingredient)
    if contribution is None:
        raise ValueError("Satuan bahan tidak cocok")
    return contribution


def money(value: Decimal) -> str:
    return str(value.quantize(MONEY, rounding=ROUND_HALF_UP))
