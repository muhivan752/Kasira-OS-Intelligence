from fastapi import APIRouter
from backend.api.routes import auth, users, tenants, outlets, categories, products, orders, payments, sync, shifts, reports, connect, ai, reservations, loyalty, media, customers, tables, tabs, webhook

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(outlets.router, prefix="/outlets", tags=["outlets"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(sync.router, prefix="/sync", tags=["sync"])
api_router.include_router(shifts.router, prefix="/shifts", tags=["shifts"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(connect.router, prefix="/connect", tags=["connect"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(reservations.router, prefix="/reservations", tags=["reservations"])
api_router.include_router(loyalty.router, prefix="/loyalty", tags=["loyalty"])
api_router.include_router(media.router, prefix="/media", tags=["media"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(tables.router, prefix="/tables", tags=["tables"])
api_router.include_router(tabs.router, prefix="/tabs", tags=["tabs"])
api_router.include_router(webhook.router, prefix="/webhook", tags=["webhook"])

# app/version endpoint (prefix di auth router sudah handle ini)
# route: GET /api/v1/auth/app/version — dipanggil dari SplashPage
