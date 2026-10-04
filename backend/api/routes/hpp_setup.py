import logging
from datetime import timedelta
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy import select, text, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api import deps
from backend.core.database import get_db, AsyncSessionLocal
from backend.models.base import utc_now
from backend.models.brand import Brand
from backend.models.outlet import Outlet
from backend.models.user import User
from backend.models.hpp_setup import HppSetupSession, HppSetupTurn
from backend.models.ingredient import Ingredient
from backend.models.product import Product
from backend.models.recipe import Recipe, RecipeIngredient
from backend.models.audit_log import AuditLog
from backend.models.event import Event
from backend.models.knowledge_graph import KnowledgeGraphEdge
from backend.services import hpp_setup_service as service

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(deps.require_pro_tier)])
Mode = Literal["manual", "estimate"]


class Create(BaseModel):
    outlet_id: UUID
    mode: Mode = "manual"
    product_id: UUID | None = None


class Message(BaseModel):
    outlet_id: UUID
    request_id: UUID
    revision: int = Field(ge=0)
    mode: Mode
    message: str = Field(min_length=1, max_length=100000)


class Approval(BaseModel):
    outlet_id: UUID
    revision: int = Field(ge=1)
    fingerprint: str = Field(min_length=64, max_length=64)
    replace_recipe: bool = False


async def scope(db, user):
    # Auth's SET LOCAL expires on commit; re-establish it for every new phase.
    await db.execute(text("SELECT set_config('app.current_tenant_id', :tenant, true)"),
                     {"tenant": str(user.tenant_id)})


async def outlet_owned(db, outlet_id, user):
    outlet = (await db.execute(select(Outlet).where(Outlet.id == outlet_id,
        Outlet.tenant_id == user.tenant_id, Outlet.deleted_at.is_(None)))).scalar_one_or_none()
    if not outlet:
        raise HTTPException(404, "Outlet tidak ditemukan")
    if not outlet.brand_id:
        raise HTTPException(409, "Lengkapi data usaha outlet sebelum menyiapkan HPP")
    return outlet


async def owned(db, session_id, user, lock=False):
    await scope(db, user)
    stmt = select(HppSetupSession).where(HppSetupSession.id == session_id,
        HppSetupSession.user_id == user.id, HppSetupSession.tenant_id == user.tenant_id,
        HppSetupSession.deleted_at.is_(None)).execution_options(populate_existing=True)
    if lock:
        stmt = stmt.with_for_update()
    session = (await db.execute(stmt)).scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Percakapan tidak ditemukan")
    outlet = await outlet_owned(db, session.outlet_id, user)
    return session, outlet


async def turns(db, session):
    return list((await db.execute(select(HppSetupTurn).where(
        HppSetupTurn.session_id == session.id, HppSetupTurn.tenant_id == session.tenant_id)
        .order_by(HppSetupTurn.created_at, HppSetupTurn.id))).scalars())


async def view(db, session):
    return {"id": str(session.id), "outlet_id": str(session.outlet_id), "mode": session.mode,
        "status": session.status, "revision": session.revision, "preview": session.preview,
        "result": session.result, "error": session.error,
        "pending": bool(session.pending_request),
        "retry_allowed": bool(session.pending_until and session.pending_until < utc_now()) or bool(session.error),
        "turns": [{"id": str(t.request_id), "mode": t.mode, "message": t.message,
                   "reply": t.reply} for t in await turns(db, session)]}


@router.post("/sessions")
async def create(body: Create, db: AsyncSession = Depends(get_db), user: User = Depends(deps.get_current_user)):
    outlet = await outlet_owned(db, body.outlet_id, user)
    draft = None
    if body.product_id:
        product = (await db.execute(select(Product).where(Product.id == body.product_id,
            Product.brand_id == outlet.brand_id, Product.deleted_at.is_(None)))).scalar_one_or_none()
        if not product:
            raise HTTPException(404, "Produk tidak ditemukan")
        ctx = await service.context(db, outlet.brand_id)
        existing = [r for r in ctx[2] if r.product_id == product.id]
        data = service.Draft(product_name=product.name)
        if len(existing) == 1:
            recipe = existing[0]
            data.servings = Decimal(1)
            data.servings_source = "existing"
            data.notes = recipe.notes or ""
            by_id = {i.id: i for i in ctx[0]}
            data.ingredients = [service.DraftIngredient(name=by_id[row.ingredient_id].name,
                quantity=Decimal(str(row.quantity)), quantity_unit=row.quantity_unit,
                quantity_source="estimate" if recipe.is_estimated else "existing",
                price_source="existing", is_optional=row.is_optional, notes=row.notes or "")
                for row in recipe.ingredients if row.deleted_at is None and row.ingredient_id in by_id]
        draft = data.model_dump(mode="json")
    session = HppSetupSession(id=uuid4(), tenant_id=user.tenant_id, outlet_id=outlet.id,
        user_id=user.id, mode=body.mode, draft=draft, status="draft", revision=0)
    db.add(session)
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, action="HPP_SETUP_STARTED",
        entity="hpp_setup_session", entity_id=session.id, after_state={"mode": body.mode}))
    await db.commit()
    await scope(db, user)
    return {"data": await view(db, session)}


@router.get("/sessions")
async def listing(outlet_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(deps.get_current_user)):
    await outlet_owned(db, outlet_id, user)
    sessions = (await db.execute(select(HppSetupSession).where(HppSetupSession.tenant_id == user.tenant_id,
        HppSetupSession.user_id == user.id, HppSetupSession.outlet_id == outlet_id,
        HppSetupSession.deleted_at.is_(None)).order_by(HppSetupSession.updated_at.desc()).limit(100))).scalars()
    return {"data": [{"id": str(s.id), "name": (s.draft or {}).get("product_name") or "Resep baru",
        "status": s.status, "updated_at": s.updated_at.isoformat()} for s in sessions]}


@router.get("/sessions/{session_id}")
async def get(session_id: UUID, db: AsyncSession = Depends(get_db), user: User = Depends(deps.get_current_user)):
    session, _ = await owned(db, session_id, user)
    return {"data": await view(db, session)}


@router.post("/sessions/{session_id}/messages", status_code=202)
async def message(session_id: UUID, body: Message, background: BackgroundTasks, db: AsyncSession = Depends(get_db), user: User = Depends(deps.get_current_user)):
    if not body.message.strip():
        raise HTTPException(422, "Pesan belum diisi")
    session, outlet = await owned(db, session_id, user, lock=True)
    if session.outlet_id != body.outlet_id:
        raise HTTPException(409, "Percakapan ini milik outlet lain. Pilih outlet yang sesuai")
    previous = (await db.execute(select(HppSetupTurn).where(
        HppSetupTurn.session_id == session.id, HppSetupTurn.request_id == body.request_id))).scalar_one_or_none()
    if previous and (previous.message != body.message or previous.mode != body.mode):
        raise HTTPException(409, "ID pesan sudah digunakan untuk isi yang berbeda")
    if previous and previous.reply:
        return {"data": await view(db, session)}
    if session.pending_until and session.pending_until > utc_now():
        raise HTTPException(409, "Pesan masih diproses. Muat percakapan terbaru dahulu")
    if session.revision != body.revision:
        raise HTTPException(409, "Draft sudah berubah. Muat percakapan terbaru dahulu")
    await db.execute(select(User.id).where(User.id == user.id).with_for_update())
    running = (await db.execute(select(HppSetupSession.id).where(
        HppSetupSession.tenant_id == user.tenant_id, HppSetupSession.user_id == user.id,
        HppSetupSession.id != session.id, HppSetupSession.pending_until > utc_now())
        .limit(2))).scalars().all()
    if len(running) >= 2:
        raise HTTPException(409, "Dua percakapan Anda masih diproses. Tunggu salah satunya selesai")
    previous_mode = session.mode
    session.pending_request = body.request_id
    session.pending_until = utc_now() + timedelta(minutes=8)
    session.mode = service.conversation_mode(body.message, body.mode)
    session.error = None
    if not previous:
        db.add(HppSetupTurn(tenant_id=user.tenant_id, session_id=session.id,
            request_id=body.request_id, mode=body.mode, message=body.message,
            usage={"previous_mode": previous_mode}))
    await db.commit()
    background.add_task(process_message, session_id, body, user.id, user.tenant_id)
    await scope(db, user)
    snapshot = await view(db, session)
    await db.commit()
    return {"data": snapshot}


async def process_message(session_id, body, user_id, tenant_id):
    async with AsyncSessionLocal() as db:
        await db.execute(text("SELECT set_config('app.current_tenant_id', :tenant, true)"), {"tenant": str(tenant_id)})
        user = (await db.execute(select(User).where(User.id == user_id,
            User.tenant_id == tenant_id, User.is_active.is_(True), User.deleted_at.is_(None)))).scalar_one_or_none()
        if not user:
            return
        session, outlet = await owned(db, session_id, user)
        if session.pending_request != body.request_id or session.revision != body.revision:
            return
        await generate_and_save(db, session, outlet, session_id, body, user)


async def generate_and_save(db, session, outlet, session_id, body, user):
    try:
        mode = session.mode
        await scope(db, user)
        ctx = await service.context(db, outlet.brand_id)
        history = await turns(db, session)
        reference = ""
        product_ids = [p.id for p in ctx[1]]
        edges = (await db.execute(select(KnowledgeGraphEdge).where(
            KnowledgeGraphEdge.tenant_id == user.tenant_id, KnowledgeGraphEdge.deleted_at.is_(None),
            ((KnowledgeGraphEdge.source_node_type == "product") & KnowledgeGraphEdge.source_node_id.in_(product_ids)) |
            ((KnowledgeGraphEdge.target_node_type == "product") & KnowledgeGraphEdge.target_node_id.in_(product_ids)))
            .order_by(KnowledgeGraphEdge.weight.desc()).limit(150))).scalars().all()
        if edges:
            import json
            reference = "Relasi KG (referensi; data resep toko di context adalah acuan terbaru): " + json.dumps([
                {"source": str(e.source_node_id), "target": str(e.target_node_id),
                 "relation": e.relation_type, "metadata": e.metadata_payload} for e in edges])
        from backend.services.embedding_service import enrich_ai_context
        try:
            async with db.begin_nested():
                reference += await enrich_ai_context(body.message[:4000], outlet.brand_id, db)
                # enrich_ai_context catches database errors; test transaction before
                # leaving the savepoint so a failed query cannot poison this phase.
                await db.execute(text("SELECT 1"))
        except Exception:
            logger.info("HPP retrieval unavailable")
        await db.commit()
        answer, usage = await service.generate(session.draft, history, ctx, mode, reference)
        session, outlet = await owned(db, session_id, user, lock=True)
        if session.pending_request != body.request_id or session.revision != body.revision:
            raise HTTPException(409, "Pesan sudah digantikan proses lain. Muat percakapan terbaru")
        # Re-read prices after the network call; the draft shows current data.
        ctx = await service.context(db, outlet.brand_id)
        turn = (await db.execute(select(HppSetupTurn).where(
            HppSetupTurn.session_id == session.id, HppSetupTurn.request_id == body.request_id))).scalar_one()
        previous_mode = (turn.usage or {}).get('previous_mode', mode)
        read_only = answer.action == 'answer' or answer.lookup is not None or session.status == 'applied'
        if read_only:
            session.mode = previous_mode
            if answer.action != 'answer' and answer.lookup is None:
                turn.reply = 'Resep ini sudah tersimpan. Aku tetap bisa bantu cek bahan dan resep toko di sini. Untuk mengubah resep, mulai lewat Resep baru ya.'
            else:
                turn.reply = service.assistant_answer(answer, ctx)
                if answer.lookup and session.draft and session.status != 'applied':
                    turn.reply += '\n\nRancangan di obrolan ini masih draft sampai kamu approve.'
        else:
            if answer.draft is None:
                raise ValueError('Draft resep belum disertakan')
            session.draft = answer.draft.model_dump(mode="json")
            session.preview = service.prepare(answer.draft, ctx, [t.message for t in history], mode)
            session.revision += 1
            turn.reply = service.reply_for_preview(answer.reply, session.preview, mode)
        session.pending_request = None
        session.pending_until = None
        turn.usage = {**usage, 'previous_mode': previous_mode, 'action': 'answer' if read_only else 'edit_recipe'}
        db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, action="HPP_ASSISTANT_ANSWERED" if read_only else "HPP_DRAFT_UPDATED",
            entity="hpp_setup_session", entity_id=session.id, request_id=str(body.request_id),
            after_state={"revision": session.revision, "is_estimated": bool(session.preview and session.preview["is_estimated"]), "usage": usage}))
        await db.commit()
        await scope(db, user)
        return {"data": await view(db, session)}
    except HTTPException:
        await db.rollback()
        raise
    except Exception as exc:
        await db.rollback()
        session, _ = await owned(db, session_id, user, lock=True)
        if session.pending_request == body.request_id:
            session.pending_request = None
            session.pending_until = None
            session.error = str(exc) if isinstance(exc, ValueError) else "AI belum bisa memproses pesan ini. Draft dan pesan tetap tersimpan; coba lagi."
            if len(session.error) > 500:
                session.error = "Jawaban AI belum valid. Draft sebelumnya tetap tersimpan; coba proses pesan ini lagi."
            await db.commit()
        logger.warning("HPP draft failed: %s", type(exc).__name__)
        await scope(db, user)
        return {"data": await view(db, session)}


@router.post("/sessions/{session_id}/approve")
async def approve(session_id: UUID, body: Approval, db: AsyncSession = Depends(get_db), user: User = Depends(deps.get_current_user)):
    session, outlet = await owned(db, session_id, user, lock=True)
    if session.outlet_id != body.outlet_id:
        raise HTTPException(409, "Percakapan ini milik outlet lain. Pilih outlet yang sesuai")
    if session.status == "applied":
        if session.revision != body.revision or session.preview["fingerprint"] != body.fingerprint:
            raise HTTPException(409, "Persetujuan berbeda dari draft yang sudah disimpan")
        return {"data": await view(db, session)}
    if session.pending_request or session.error:
        raise HTTPException(409, "Selesaikan pesan terakhir sebelum approve")
    preview = session.preview
    if not preview or session.revision != body.revision or preview["fingerprint"] != body.fingerprint:
        raise HTTPException(409, "Approve hanya untuk draft terakhir. Muat percakapan terbaru")
    if not preview["ready"]:
        raise HTTPException(422, "Lengkapi data bahan dan jumlah porsi dahulu")
    if preview["replaces_recipe"] and not body.replace_recipe:
        raise HTTPException(409, "Konfirmasi penggantian resep produk ini")
    # Serialize recipe setup per brand, including duplicate names from two chats.
    await db.execute(select(Brand.id).where(Brand.id == outlet.brand_id,
        Brand.tenant_id == user.tenant_id, Brand.deleted_at.is_(None)).with_for_update())
    await db.execute(select(Ingredient.id).where(Ingredient.brand_id == outlet.brand_id,
        Ingredient.deleted_at.is_(None)).order_by(Ingredient.id).with_for_update())
    await db.execute(select(Product.id).where(Product.brand_id == outlet.brand_id,
        Product.deleted_at.is_(None)).order_by(Product.id).with_for_update())
    await db.execute(select(Recipe.id).join(Product).where(Product.brand_id == outlet.brand_id,
        Recipe.deleted_at.is_(None)).with_for_update(of=Recipe))
    ctx = await service.context(db, outlet.brand_id)
    history = await turns(db, session)
    current = service.prepare(service.Draft.model_validate(session.draft), ctx,
        [t.message for t in history], session.mode)
    if current["fingerprint"] != preview["fingerprint"]:
        session.preview = current
        session.revision += 1
        await db.commit()
        raise HTTPException(409, "Harga atau resep toko sudah berubah. Muat dan periksa draft terbaru sebelum approve")
    ingredients, products, recipes = ctx
    product = next((p for p in products if str(p.id) == preview["product_id"]), None)
    if not product:
        product = Product(id=uuid4(), brand_id=outlet.brand_id, name=preview["product_name"],
            base_price=Decimal(0), is_active=False, stock_enabled=False)
        db.add(product)
        await db.flush()
    refs, changes = [], []
    for line in preview["lines"]:
        ing = next((i for i in ingredients if str(i.id) == line["ingredient_id"]), None)
        if not ing:
            ing = Ingredient(id=uuid4(), brand_id=outlet.brand_id, name=line["name"],
                tracking_mode="simple", base_unit=line["unit"],
                unit_type={"gram": "WEIGHT", "ml": "VOLUME", "pcs": "COUNT", "bungkus": "COUNT"}.get(line["unit"], "CUSTOM"),
                ingredient_type="recipe", buy_price=Decimal(line["buy_price"]),
                buy_qty=float(line["buy_qty"]), cost_per_base_unit=Decimal(line["unit_cost"]),
                needs_review=line["price_source"] == "estimate", ai_setup_complete=True, row_version=0)
            db.add(ing)
            event_type = "ingredient.created"
        elif line["action"] == "update_price":
            ing.buy_price = Decimal(line["buy_price"])
            ing.buy_qty = float(line["buy_qty"])
            ing.cost_per_base_unit = Decimal(line["unit_cost"])
            ing.needs_review = False
            ing.row_version += 1
            event_type = "ingredient.price_updated"
        else:
            event_type = None
        refs.append((ing, line))
        changes.append({**line, "ingredient_id": str(ing.id)})
        if event_type:
            db.add(Event(outlet_id=outlet.id, stream_id=f"ingredient:{ing.id}", event_type=event_type,
                event_data={"source": "hpp_chat_approved", "session_id": str(session.id),
                            "revision": session.revision, **line, "ingredient_id": str(ing.id),
                            "base_unit": ing.base_unit, "cost_per_base_unit": str(ing.cost_per_base_unit)},
                event_metadata={"tenant_id": str(user.tenant_id), "user_id": str(user.id)}))
    await db.flush()
    old = [r for r in recipes if r.product_id == product.id]
    now = utc_now()
    for recipe in old:
        recipe.is_active = False
        recipe.deleted_at = now
        recipe.row_version += 1
        await db.execute(update(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe.id,
            RecipeIngredient.deleted_at.is_(None)).values(deleted_at=now, row_version=RecipeIngredient.row_version + 1))
    previous_version = (await db.execute(select(func.max(Recipe.version)).where(Recipe.product_id == product.id))).scalar() or 0
    recipe = Recipe(id=uuid4(), product_id=product.id, version=previous_version + 1,
        is_active=True, ai_assisted=True, is_estimated=preview["is_estimated"],
        created_by=user.id, notes=preview["notes"] or None, row_version=0)
    db.add(recipe)
    await db.flush()
    for ing, line in refs:
        db.add(RecipeIngredient(recipe_id=recipe.id, ingredient_id=ing.id,
            quantity=float(line["quantity"]), quantity_unit=ing.base_unit,
            is_optional=line["is_optional"], notes=line["notes"] or None, row_version=0))
    # Update only this product's recipe links; other outlets/brands stay scoped.
    await db.execute(update(KnowledgeGraphEdge).where(KnowledgeGraphEdge.tenant_id == user.tenant_id,
        KnowledgeGraphEdge.deleted_at.is_(None), KnowledgeGraphEdge.relation_type.in_(["contains", "used_by"]),
        ((KnowledgeGraphEdge.source_node_type == "product") & (KnowledgeGraphEdge.source_node_id == product.id)) |
        ((KnowledgeGraphEdge.target_node_type == "product") & (KnowledgeGraphEdge.target_node_id == product.id)))
        .values(deleted_at=now))
    for ing, line in refs:
        if line["is_optional"]:
            continue
        for reverse in (False, True):
            db.add(KnowledgeGraphEdge(tenant_id=user.tenant_id,
                source_node_type="ingredient" if reverse else "product",
                source_node_id=ing.id if reverse else product.id,
                target_node_type="product" if reverse else "ingredient",
                target_node_id=product.id if reverse else ing.id,
                relation_type="used_by" if reverse else "contains",
                metadata_payload={"quantity": float(line["quantity"]), "unit": ing.base_unit,
                                  "is_estimated": preview["is_estimated"]}))
    result = {"recipe_id": str(recipe.id), "product_id": str(product.id),
        "new_product": preview["new_product"], "total_cost": preview["total_cost"],
        "is_estimated": preview["is_estimated"], "approved_revision": session.revision,
        "changes": changes}
    session.status = "applied"
    session.result = result
    db.add(AuditLog(tenant_id=user.tenant_id, user_id=user.id, action="HPP_SETUP_APPROVED",
        entity="recipe", entity_id=recipe.id, request_id=str(session.id),
        before_state={"replaced_recipe_ids": [str(r.id) for r in old]}, after_state=result))
    db.add(Event(outlet_id=outlet.id, stream_id=f"product:{product.id}", event_type="recipe.hpp_setup_approved",
        event_data={"source": "hpp_chat_approved", "session_id": str(session.id), **result},
        event_metadata={"tenant_id": str(user.tenant_id), "user_id": str(user.id)}))
    # One commit includes recipe, ingredients, provenance, audit, event and result.
    # No OutletStock rows or physical stock changes are made here.
    await db.commit()
    await scope(db, user)
    try:
        from backend.services.redis import get_redis_client
        redis = await get_redis_client()
        outlet_ids = (await db.execute(select(Outlet.id).where(Outlet.tenant_id == user.tenant_id,
            Outlet.brand_id == outlet.brand_id, Outlet.deleted_at.is_(None)))).scalars().all()
        await redis.delete(*(f"ai:context:{item}" for item in outlet_ids))
    except Exception:
        logger.info("HPP context cache refresh deferred")
    return {"data": await view(db, session)}
