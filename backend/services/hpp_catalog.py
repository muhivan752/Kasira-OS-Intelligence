"""Read-only recipe and ingredient answers from the current tenant's catalog."""
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field
from backend.services import hpp_math as math


class CatalogQuery(BaseModel):
    kind: Literal['overview', 'ingredients', 'recipes', 'missing_recipes', 'recipe_details', 'ingredient_usage']
    name: str = Field(default='', max_length=150)


def match(items, name):
    if not name.strip():
        return list(items)
    wanted = name.strip().casefold()
    exact = [item for item in items if item.name.strip().casefold() == wanted]
    return exact or [item for item in items if wanted in item.name.casefold()]


def amount(value):
    formatted = format(Decimal(str(value)), 'f')
    return formatted.rstrip('0').rstrip('.') if '.' in formatted else formatted


def rupiah(value):
    whole, fraction = math.money(Decimal(str(value))).split('.')
    return 'Rp' + f'{int(whole):,}'.replace(',', '.') + (',' + fraction if fraction != '00' else '')


def recipe_rows(recipe, by_ingredient):
    return [(row, by_ingredient[row.ingredient_id]) for row in recipe.ingredients
        if row.deleted_at is None and row.ingredient_id in by_ingredient and row.quantity > 0]


def recipe_cost(recipe, by_ingredient):
    try:
        if not any(not row.is_optional for row, _ in recipe_rows(recipe, by_ingredient)):
            return None
        return math.money(sum((math.line_cost(row.quantity, row.quantity_unit, ingredient)
            for row, ingredient in recipe_rows(recipe, by_ingredient) if not row.is_optional), Decimal(0)))
    except (ValueError, ArithmeticError):
        return None


def summary(ctx):
    ingredients, products, recipes = ctx
    covered = {recipe.product_id for recipe in recipes}
    return {'ingredient_count': len(ingredients), 'product_count': len(products),
        'active_recipe_count': len(recipes), 'missing_recipe_count':
        sum(product.id not in covered for product in products)}


def answer(query: CatalogQuery, ctx):
    ingredients, products, recipes = ctx
    by_product = {product.id: product for product in products}
    by_ingredient = {ingredient.id: ingredient for ingredient in ingredients}
    facts = summary(ctx)
    if query.kind == 'overview':
        sections = [f"Di toko sekarang ada {len(ingredients)} bahan, {len(recipes)} resep aktif, dan {len(products)} menu."]
        sections.append('Bahan: ' + (', '.join(i.name for i in ingredients) if ingredients else 'belum ada yang tersimpan') + '.')
        sections.append('Resep aktif: ' + (', '.join(by_product[r.product_id].name for r in recipes if r.product_id in by_product)
            if recipes else 'belum ada yang tersimpan') + '.')
        if facts['missing_recipe_count']:
            covered = {recipe.product_id for recipe in recipes}
            sections.append('Menu yang belum punya resep: ' + ', '.join(p.name for p in products if p.id not in covered) + '.')
        return '\n\n'.join(sections)
    if query.kind == 'ingredients':
        found = match(ingredients, query.name)
        if not found:
            return ('Belum ada bahan ' + query.name + ' yang tersimpan di toko.' if query.name else 'Belum ada bahan yang tersimpan di toko.')
        return 'Bahan yang sudah tersimpan:\n' + '\n'.join(
            '- ' + i.name + (f': biaya satuan {amount(i.cost_per_base_unit)} Rp/{i.base_unit}' if query.name else '')
            + (' (harga estimasi)' if i.needs_review else '') for i in found)
    if query.kind == 'missing_recipes':
        covered = {recipe.product_id for recipe in recipes}
        found_products = match(products, query.name)
        if query.name and not found_products:
            return 'Menu ' + query.name + ' belum ditemukan di toko.'
        found = [p for p in found_products if p.id not in covered]
        return ('Menu yang belum punya resep aktif:\n' + '\n'.join('- ' + p.name for p in found)
            if found else 'Semua menu yang ditemukan sudah punya resep aktif.' if products else 'Belum ada menu yang tersimpan di toko.')
    if query.kind == 'ingredient_usage':
        found = match(ingredients, query.name)
        if not found:
            return 'Bahan itu belum ditemukan di toko. Sebutkan nama bahan yang ingin dicek.'
        sections = []
        for ingredient in found:
            used = [by_product[r.product_id].name for r in recipes if r.product_id in by_product and any(
                row.ingredient_id == ingredient.id and row.deleted_at is None and row.quantity > 0 for row in r.ingredients)]
            sections.append(ingredient.name + ': ' + (', '.join(used) if used else 'belum dipakai pada resep aktif') + '.')
        return '\n'.join(sections)
    found_products = match(products, query.name)
    chosen = {product.id for product in found_products}
    found_recipes = [recipe for recipe in recipes if recipe.product_id in chosen]
    if not found_recipes:
        if query.name and found_products:
            return 'Menu ' + ', '.join(p.name for p in found_products) + ' sudah ada, tetapi belum punya resep aktif.'
        return ('Belum ada resep untuk ' + query.name + ' yang tersimpan di toko.' if query.name else 'Belum ada resep aktif yang tersimpan di toko.')
    sections = []
    for recipe in sorted(found_recipes, key=lambda r: by_product[r.product_id].name.casefold()):
        total = recipe_cost(recipe, by_ingredient)
        heading = by_product[recipe.product_id].name + (' (estimasi)' if recipe.is_estimated else '')
        heading += ': HPP bahan ' + rupiah(total) + ' per porsi.' if total is not None else ': HPP belum bisa dihitung karena data bahan atau satuannya perlu diperiksa.'
        if query.kind == 'recipe_details':
            rows = recipe_rows(recipe, by_ingredient)
            heading += '\n' + '\n'.join('- ' + ingredient.name + ': ' + amount(row.quantity) + ' ' + row.quantity_unit
                + (' (opsional)' if row.is_optional else '') + ('. ' + row.notes if row.notes else '') for row, ingredient in rows)
            if recipe.notes:
                heading += '\nCatatan: ' + recipe.notes
        sections.append(heading)
    return '\n\n'.join(sections) + '\nHPP ini hanya biaya bahan, belum termasuk biaya operasional.'
