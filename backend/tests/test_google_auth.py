import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from fastapi import HTTPException
from jose import jwt

from backend.services import google_auth
from backend.api.routes import auth


class GoogleTokenTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.private = key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        cls.public = key.public_key().public_bytes(serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo)

    def claims(self, **overrides):
        now = int(time.time())
        return {"aud": "shared-project", "iss": "https://securetoken.google.com/shared-project",
                "sub": "google-user", "iat": now, "auth_time": now, "exp": now + 3600,
                "firebase": {"sign_in_provider": "google.com"}, "email_verified": True,
                "email": "owner@example.com", "name": "Owner", **overrides}

    async def verify(self, **overrides):
        token = jwt.encode(self.claims(**overrides), self.private, algorithm="RS256", headers={"kid": "test"})
        with patch.object(google_auth.settings, "GOOGLE_FIREBASE_PROJECT_ID", "shared-project"), \
             patch.object(google_auth, "_public_keys", AsyncMock(return_value={"test": self.public})):
            return await google_auth.verify_google_token(token)

    async def test_google_identity_is_verified(self):
        identity = await self.verify()
        self.assertEqual(identity["uid"], "google-user")
        self.assertEqual(identity["project"], "shared-project")

    async def test_wrong_project_and_provider_are_rejected(self):
        for claims in ({"aud": "different-project"}, {"iss": "https://attacker.invalid"},
                       {"firebase": {"sign_in_provider": "password"}}, {"email_verified": False},
                       {"exp": int(time.time()) - 60}, {"iat": int(time.time()) + 600},
                       {"auth_time": int(time.time()) + 600}, {"sub": ""}):
            with self.subTest(claims=claims), self.assertRaises(HTTPException) as rejected:
                await self.verify(**claims)
            self.assertEqual(rejected.exception.status_code, 401)

    async def test_unsigned_and_wrong_signature_are_rejected(self):
        for token in ("not-a-token", jwt.encode(self.claims(), "other-secret", algorithm="HS256", headers={"kid": "test"})):
            with patch.object(google_auth.settings, "GOOGLE_FIREBASE_PROJECT_ID", "shared-project"), \
                 self.assertRaises(HTTPException) as rejected:
                await google_auth.verify_google_token(token)
            self.assertEqual(rejected.exception.status_code, 401)

    async def test_missing_audience_or_issuer_is_rejected(self):
        for omitted in ("aud", "iss", "exp", "iat", "sub"):
            claims = self.claims()
            del claims[omitted]
            token = jwt.encode(claims, self.private, algorithm="RS256", headers={"kid": "test"})
            with self.subTest(omitted=omitted), \
                 patch.object(google_auth.settings, "GOOGLE_FIREBASE_PROJECT_ID", "shared-project"), \
                 patch.object(google_auth, "_public_keys", AsyncMock(return_value={"test": self.public})), \
                 self.assertRaises(HTTPException) as rejected:
                await google_auth.verify_google_token(token)
            self.assertEqual(rejected.exception.status_code, 401)

    async def test_unconfigured_google_returns_unavailable(self):
        with patch.object(google_auth.settings, "GOOGLE_FIREBASE_PROJECT_ID", ""), self.assertRaises(HTTPException) as rejected:
            await google_auth.verify_google_token("not-a-token")
        self.assertEqual(rejected.exception.status_code, 503)


class RegistrationProofTests(unittest.IsolatedAsyncioTestCase):
    async def test_phone_binding_expiry_and_consumption_prevent_registration(self):
        for changed, pending in (({"phone": "628111111111"}, "628222222222"),
                                 ({"exp": int(time.time()) - 60}, "628222222222"),
                                 ({"aud": "selaris:onboarding"}, "628222222222"), ({}, None)):
            claims = {"aud": "selaris:registration", "phone": "628222222222",
                      "jti": "one-use-proof", "exp": int(time.time()) + 900, **changed}
            proof = jwt.encode(claims, auth.settings.SECRET_KEY, algorithm=auth.settings.ALGORITHM)
            request = auth.RegisterRequest(phone="628222222222", owner_name="Owner", business_name="Demo",
                                           pin="123456", otp_proof=proof)
            db = SimpleNamespace(execute=AsyncMock(), commit=AsyncMock())
            redis = SimpleNamespace(get=AsyncMock(return_value=pending))
            with self.subTest(claims=claims, pending=pending), \
                 patch.object(auth, "get_redis_client", AsyncMock(return_value=redis)), \
                 self.assertRaises(HTTPException) as rejected:
                await auth.register(request, db)
            self.assertEqual(rejected.exception.status_code, 401)
            db.execute.assert_not_called()
            db.commit.assert_not_called()

    async def test_verification_rate_limit_blocks_even_correct_code(self):
        redis = SimpleNamespace(get=AsyncMock(return_value="5"))
        with self.assertRaises(HTTPException) as rejected:
            await auth._check_google_phone_otp("628222222222", "123456", redis)
        self.assertEqual(rejected.exception.status_code, 429)

    async def test_wrong_code_counts_attempts_and_cannot_mint_proof(self):
        redis = SimpleNamespace(get=AsyncMock(side_effect=[None, "654321"]),
                                incr=AsyncMock(return_value=1), expire=AsyncMock(), setex=AsyncMock())
        with patch.object(auth, "get_redis_client", AsyncMock(return_value=redis)), self.assertRaises(HTTPException):
            await auth.verify_registration_otp(auth.OTPVerifyRequest(phone="628222222222", otp="123456"))
        redis.incr.assert_awaited_once()
        redis.setex.assert_not_called()


if __name__ == "__main__":
    unittest.main()
