from fastapi import APIRouter
from backend.api.routes import auth, users, tenants, outlets, categories, products, orders, payments, sync, shifts, reports

api_router = APIRouter()
api_router.include_router(auth.router, tags=["auth"])
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
