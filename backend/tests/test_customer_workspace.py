import unittest
from decimal import Decimal
from uuid import uuid4

from pydantic import ValidationError

from backend.schemas.customer_workspace import CustomerSave, CustomerNote, normalize_phone
from backend.services.customer_workspace import amount


class CustomerValidationTests(unittest.TestCase):
    def test_phone_formats_and_invalid_content(self):
        for value in ("0812 3456 7890", "+62 (812) 3456-7890", "6281234567890"):
            self.assertEqual(normalize_phone(value), "6281234567890")
        self.assertIsNone(normalize_phone(" "))
        self.assertEqual(normalize_phone("+1 (415) 555-0123"), "14155550123")
        for value in ("abc081234567890", "123", "+1 123"):
            with self.assertRaises(ValueError):
                normalize_phone(value)

    def test_whitespace_and_future_birthdays_are_rejected(self):
        for changes in ({"name": " "}, {"birthday": "2999-01-01"}, {"email": "broken@"}, {"notes": "x" * 2001}):
            with self.assertRaises(ValidationError):
                CustomerSave(client_request_id=uuid4(), **{"name": "QA", **changes})
        with self.assertRaises(ValidationError):
            CustomerNote(client_request_id=uuid4(), body=" ")

    def test_decimal_precision_is_preserved(self):
        self.assertEqual(amount(Decimal("1234567890.12")), "1234567890.12")
        self.assertEqual(amount(Decimal("1.005")), "1.01")


if __name__ == "__main__":
    unittest.main()
