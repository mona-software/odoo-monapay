import hashlib
import hmac
import json

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMonaPay(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = cls.env.ref("payment_monapay.payment_provider_monapay")
        cls.provider.write(
            {
                "state": "test",
                "monapay_webhook_secret": "test-webhook-secret",
                "monapay_client_id": "test-client",
                "monapay_client_secret": "test-secret",
                "monapay_owner_number": "0123456789",
                "monapay_owner_type": "ORG",
                "monapay_merchant_id": "MERCHANT",
                "monapay_terminal_id": "TERMINAL",
                "monapay_va_prefix": "OD",
                "monapay_beneficiary_name": "MONA TEST",
            }
        )
        cls.currency = cls.env.ref("base.VND")
        cls.partner = cls.env.ref("base.main_partner")
        cls.payment_method = cls.env.ref("payment_monapay.payment_method_monapay")

    def _make_tx(self, amount=150000):
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": self.provider.id,
                "payment_method_id": self.payment_method.id,
                "reference": self.env["payment.transaction"]._compute_reference(
                    "monapay", prefix="TEST"
                ),
                "amount": amount,
                "currency_id": self.currency.id,
                "partner_id": self.partner.id,
                "monapay_order_code": "DH9876",
                "monapay_virtual_account_number": "VA9876",
            }
        )
        tx._set_pending()
        return tx

    def test_webhook_signature_and_timestamp(self):
        raw = json.dumps({"transaction_code": "TX001"}, separators=(",", ":")).encode()
        timestamp = "1700000000"
        signature = "sha256=" + hmac.new(
            b"test-webhook-secret", timestamp.encode() + b"." + raw, hashlib.sha256
        ).hexdigest()

        self.assertTrue(
            self.provider._monapay_verify_signature(raw, timestamp, signature, now=1700000299)
        )
        self.assertFalse(
            self.provider._monapay_verify_signature(raw, timestamp, signature, now=1700000301)
        )
        self.assertFalse(
            self.provider._monapay_verify_signature(raw + b" ", timestamp, signature, now=1700000000)
        )

    def test_match_order_and_require_sufficient_amount(self):
        tx = self._make_tx()
        payload = {
            "amount": 149999,
            "description": "Thanh toan DH9876",
            "transaction_code": "BANK-001",
            "account_number": "VA9876",
            "type": "income",
        }

        matched = self.env["payment.transaction"]._monapay_find_transaction(
            payload, self.provider
        )
        self.assertEqual(matched, tx)
        self.assertEqual(tx._monapay_apply_payment(payload), "underpaid")
        self.assertNotEqual(tx.state, "done")

        payload.update({"amount": 150000, "transaction_code": "BANK-002"})
        self.assertEqual(tx._monapay_apply_payment(payload), "done")
        self.assertEqual(tx.state, "done")
        self.assertEqual(tx.provider_reference, "BANK-002")
        self.assertEqual(tx._monapay_apply_payment(payload), "duplicate")

    def test_match_falls_back_to_virtual_account(self):
        tx = self._make_tx()
        payload = {
            "amount": 150000,
            "description": "No order code",
            "transaction_code": "BANK-003",
            "account_number": "VA9876",
        }
        matched = self.env["payment.transaction"]._monapay_find_transaction(
            payload, self.provider
        )
        self.assertEqual(matched, tx)

    def test_reject_invalid_and_non_income_payments(self):
        tx = self._make_tx()
        with self.assertRaises(ValueError):
            tx._monapay_apply_payment(
                {"amount": "nan", "transaction_code": "BANK-NAN"}
            )
        with self.assertRaises(ValueError):
            self.provider._monapay_process_webhook(
                {
                    "amount": 150000,
                    "description": "DH9876",
                    "transaction_code": "BANK-OUT",
                    "account_number": "VA9876",
                    "type": "outcome",
                }
            )
