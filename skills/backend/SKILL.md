# BACKEND SKILL

## Response Format (WAJIB SEMUA ENDPOINT)
return {
    "success": True,
    "data": {...},
    "meta": {"request_id": str(uuid4()), "ts": now()},
}
# Error:
raise HTTPException(status_code=422, detail={
    "success": False,
    "error": "VALIDATION_ERROR",
    "message": "Pesan error dalam bahasa Indonesia",
})

## Middleware (Auto di setiap request)
1. Set tenant schema: SET search_path TO {tenant_id}
2. JWT verify + device binding check
3. Rate limit check via Redis
4. Write audit log (semua POST/PUT/DELETE)

## Audit Log (WAJIB setiap WRITE)
await write_audit(
    user_id=current_user.id,
    action="product.update",
    entity_type="product",
    entity_id=product_id,
    old_data=old.dict(),
    new_data=new.dict(),
    request_id=request_id,
)

## Async Only
# Benar:
async def get_products(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Product))
# SALAH: jangan pakai sync Session
