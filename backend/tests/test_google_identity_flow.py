import os
import unittest
import uuid
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from backend.core.config import settings
from backend.models.tenant import Tenant
from backend.models.brand import Brand
from backend.models.outlet import Outlet
from backend.models.user import User
from backend.api.routes import auth


class MemoryRedis:
    def __init__(self):
        self.values = {}

    async def get(self, key):
        return self.values.get(key)

    async def setex(self, key, ttl, value):
        self.values[key] = value

    async def delete(self, key):
        self.values.pop(key, None)


@unittest.skipUnless(os.environ.get("SELARIS_AUTH_TEST_DATABASE") == "1", "isolated auth database only")
class GoogleIdentityFlowTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_shop_links_and_new_shop_is_created_only_once(self):
        self.assertEqual(settings.POSTGRES_DB, "authcheck")
        self.assertEqual(settings.POSTGRES_SERVER, "selaris-auth-check-20261004")
        engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        redis = MemoryRedis()
        identity = {"project": "shared-project", "uid": "existing-owner", "email": "owner@example.com", "name": "Owner"}
        with patch.object(auth, "get_redis_client", AsyncMock(return_value=redis)), \
             patch.object(auth, "verify_google_token", AsyncMock(side_effect=lambda _: dict(identity))), \
             patch.object(auth, "_send_welcome_wa", AsyncMock()), \
             patch.object(settings, "GOOGLE_FIREBASE_PROJECT_ID", "shared-project"):
            async with factory() as db:
                tenant = Tenant(id=uuid.uuid4(), name="Existing demo", schema_name="test_google_existing", is_active=True)
                brand = Brand(id=uuid.uuid4(), tenant_id=tenant.id, name="Existing demo", type="cafe")
                outlet = Outlet(id=uuid.uuid4(), tenant_id=tenant.id, brand_id=brand.id, name="Existing demo", slug="test-google-existing")
                user = User(id=uuid.uuid4(), tenant_id=tenant.id, full_name="Owner", phone="628900001111", is_active=True, is_superuser=True)
                db.add_all([tenant, brand, outlet, user])
                await db.commit()
                redis.values[f"otp:{user.phone}"] = "123456"
                linked = await auth.google_phone(auth.GooglePhoneRequest(id_token="test-token-long-enough", phone=user.phone, otp="123456"), db)
                self.assertTrue(linked.data["registered"])
                self.assertEqual(linked.data["tenant_id"], str(tenant.id))
                self.assertEqual(linked.data["outlet_id"], str(outlet.id))
                self.assertEqual(await db.scalar(select(func.count()).select_from(Tenant)), 1)
                self.assertIsNone(await redis.get(f"otp:{user.phone}"))
                direct = await auth.google_sign_in(auth.GoogleSignInRequest(id_token="test-token-long-enough"), db)
                self.assertTrue(direct.data["registered"])
                self.assertEqual(direct.data["tenant_id"], str(tenant.id))

                identity["uid"] = "other-google"
                redis.values[f"otp:{user.phone}"] = "123456"
                with self.assertRaises(HTTPException) as rejected:
                    await auth.google_phone(auth.GooglePhoneRequest(id_token="test-token-long-enough", phone=user.phone, otp="123456"), db)
                self.assertEqual(rejected.exception.status_code, 409)
                await db.rollback()

                phone = "628900002222"
                redis.values[f"otp:{phone}"] = "654321"
                pending = await auth.google_phone(auth.GooglePhoneRequest(id_token="test-token-long-enough", phone=phone, otp="654321"), db)
                self.assertFalse(pending.data["registered"])
                self.assertEqual(await db.scalar(select(func.count()).select_from(Tenant)), 1)
                request = auth.RegisterRequest(phone=phone, owner_name="New Owner", business_name="New demo",
                                               pin="123456", google_proof=pending.data["google_proof"])
                created = await auth.register(request, db)
                self.assertTrue(created.data.access_token)
                self.assertEqual(await db.scalar(select(func.count()).select_from(Tenant)), 2)
                created_user = await db.scalar(select(User).where(User.phone == phone))
                self.assertEqual(created_user.google_uid, "other-google")
                with self.assertRaises(HTTPException) as replay:
                    await auth.register(request, db)
                self.assertEqual(replay.exception.status_code, 401)
                self.assertEqual(await db.scalar(select(func.count()).select_from(Tenant)), 2)
                created_user.is_active = False
                await db.commit()
                with self.assertRaises(HTTPException) as inactive:
                    await auth.google_sign_in(auth.GoogleSignInRequest(id_token="test-token-long-enough"), db)
                self.assertEqual(inactive.exception.status_code, 403)
        await engine.dispose()


if __name__ == "__main__":
    unittest.main()
