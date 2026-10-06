import unittest
from uuid import uuid4
from pydantic import ValidationError
from backend.schemas.purchasing import PurchaseCreate, PurchaseLineIn, PurchasePay, SupplierCreate, SupplierUpdate
from backend.services.purchasing_service import qty_to_base_unit, moving_average
from decimal import Decimal


class PurchasingTests(unittest.TestCase):
    def test_money_and_quantity_validation(self):
        for quantity in [0, -1, float('nan'), float('inf')]:
            with self.assertRaises(ValidationError):
                PurchaseLineIn(name='QA',quantity=quantity,unit_price='1')
        for amount in ['1.001', '10000000000']:
            with self.assertRaises(ValidationError):
                PurchasePay(amount=amount,row_version=0)
        self.assertEqual(PurchasePay(amount='12.34',row_version=0).amount,Decimal('12.34'))

    def test_receipt_dates(self):
        args={'outlet_id':uuid4(),'items':[{'name':'QA','quantity':1,'unit_price':'1'}]}
        for date in ['2026-09-01T12:00:00','2099-01-01T00:00:00Z']:
            with self.assertRaises(ValidationError):
                PurchaseCreate(**args,received_at=date)
        with self.assertRaises(ValidationError):
            PurchaseCreate(**args,received_at='2026-09-02T00:00:00Z',due_at='2026-09-01T00:00:00Z')

    def test_supplier_names_and_nullable_updates(self):
        self.assertEqual(SupplierCreate(name='  QA  ').name,'QA')
        with self.assertRaises(ValidationError): SupplierCreate(name='  ')
        for patch in [{'name':None},{'payment_terms_days':None},{'is_active':None}]:
            with self.assertRaises(ValidationError): SupplierUpdate(row_version=0,**patch)

    def test_conversions_and_precision(self):
        self.assertEqual(qty_to_base_unit(2,'kg','gram'),2000)
        self.assertEqual(qty_to_base_unit(2,'dus','pcs'),24)
        self.assertIsNone(qty_to_base_unit(2,'liter','gram'))
        self.assertEqual(moving_average(1000,Decimal('.01'),2000,Decimal('.015'),precision=Decimal('.00000001')),Decimal('.01333333'))

if __name__=='__main__': unittest.main()
