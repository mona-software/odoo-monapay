import hashlib
import hmac
import importlib.util
import json
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "payment_monapay" / "utils.py"
SPEC = importlib.util.spec_from_file_location("monapay_utils", MODULE_PATH)
UTILS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UTILS)


class MonaPayCoreTest(unittest.TestCase):
    def test_signature_accepts_exact_body_inside_five_minutes(self):
        raw = json.dumps({"amount": 150000, "description": "DH42"}, separators=(",", ":")).encode()
        timestamp = "1700000000"
        signature = "sha256=" + hmac.new(
            b"webhook-secret", timestamp.encode() + b"." + raw, hashlib.sha256
        ).hexdigest()

        self.assertTrue(
            UTILS.verify_webhook_signature(
                raw, timestamp, signature, "webhook-secret", now=1700000300
            )
        )
        self.assertFalse(
            UTILS.verify_webhook_signature(
                raw, timestamp, signature, "webhook-secret", now=1700000301
            )
        )
        self.assertFalse(
            UTILS.verify_webhook_signature(
                raw + b" ", timestamp, signature, "webhook-secret", now=1700000000
            )
        )

    def test_order_content_matching_is_delimited(self):
        self.assertEqual(UTILS.extract_order_code("Thanh toan DH9876"), "DH9876")
        self.assertEqual(UTILS.extract_order_code("dh #9876"), None)
        self.assertEqual(UTILS.extract_order_code("XXDH9876YY"), None)

    def test_amount_matching_allows_exact_or_overpayment(self):
        self.assertFalse(UTILS.amount_is_sufficient(149999, 150000))
        self.assertTrue(UTILS.amount_is_sufficient(150000, 150000))
        self.assertTrue(UTILS.amount_is_sufficient(150001, 150000))
        self.assertFalse(UTILS.amount_is_sufficient("invalid", 150000))


if __name__ == "__main__":
    unittest.main()

