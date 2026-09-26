import math
import secrets

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..utils import extract_order_code

class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    monapay_order_code = fields.Char(copy=False, index=True, readonly=True)
    monapay_qr_code_id = fields.Char(copy=False, readonly=True)
    monapay_qr_data_url = fields.Text(copy=False, readonly=True)
    monapay_virtual_account_number = fields.Char(copy=False, index=True, readonly=True)
    monapay_display_token = fields.Char(copy=False, index=True, readonly=True)

    def _get_specific_rendering_values(self, processing_values):
        values = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "monapay":
            return values
        self.ensure_one()
        self._monapay_prepare_qr()
        return {
            **values,
            "api_url": "/payment/monapay/qr",
            "token": self.monapay_display_token,
        }

    def _monapay_prepare_qr(self):
        self.ensure_one()
        if self.currency_id.name != "VND":
            raise UserError(_("MONA Pay only supports VND transactions."))
        if self.monapay_qr_data_url and self.monapay_display_token:
            return

        amount = int(round(self.amount))
        if amount <= 0 or self.currency_id.compare_amounts(self.amount, amount) != 0:
            raise UserError(_("MONA Pay requires a positive whole-number VND amount."))

        order_code = self.monapay_order_code or f"DH{self.id}"
        payload = {
            "ownerNumber": self.provider_id.monapay_owner_number,
            "ownerType": self.provider_id.monapay_owner_type,
            "merchantId": self.provider_id.monapay_merchant_id,
            "terminalId": self.provider_id.monapay_terminal_id,
            "orderId": order_code,
            "virtualAccountPrefix": self.provider_id.monapay_va_prefix,
            "beneficiaryName": self.provider_id.monapay_beneficiary_name,
            "amount": amount,
            "description": order_code,
        }
        if self.partner_email:
            payload["payer_email"] = self.partner_email
        data = self.provider_id._monapay_api_request("/api/v1/acb/qr-payment/generate", payload)
        qr_url = data.get("qr_data_url") or data.get("qr_image_url")
        if not data.get("id") or not qr_url:
            raise UserError(_("MONA Pay QR response is missing id or QR image URL."))
        self.write(
            {
                "monapay_order_code": order_code,
                "monapay_qr_code_id": str(data["id"]),
                "monapay_qr_data_url": qr_url,
                "monapay_virtual_account_number": data.get("virtual_account_number"),
                "monapay_display_token": self.monapay_display_token or secrets.token_urlsafe(32),
            }
        )
        self._set_pending(state_message=_("Waiting for the MONA Pay bank transfer."))

    @classmethod
    def _monapay_extract_order_code(cls, description):
        return extract_order_code(description)

    @api.model
    def _monapay_find_transaction(self, payload, provider):
        order_code = self._monapay_extract_order_code(payload.get("description"))
        tx = self.search(
            [
                ("provider_id", "=", provider.id),
                ("monapay_order_code", "=", order_code or ""),
            ],
            limit=1,
        )
        if tx:
            return tx
        account_number = str(payload.get("account_number") or "").strip()
        if not account_number:
            return self.browse()
        return self.search(
            [
                ("provider_id", "=", provider.id),
                ("monapay_virtual_account_number", "=", account_number),
            ],
            limit=1,
        )

    def _monapay_apply_payment(self, payload):
        self.ensure_one()
        transaction_code = str(payload.get("transaction_code") or "").strip()
        try:
            paid_amount = float(payload.get("amount"))
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid payment amount.") from exc
        if not transaction_code or not math.isfinite(paid_amount) or paid_amount < 0:
            raise ValueError("Invalid transaction.")

        reused = self.search_count(
            [
                ("provider_code", "=", "monapay"),
                ("provider_reference", "=", transaction_code),
                ("id", "!=", self.id),
            ]
        )
        if reused:
            raise ValueError("Transaction code was already used.")
        if self.provider_reference == transaction_code and self.state == "done":
            return "duplicate"
        if self.currency_id.compare_amounts(paid_amount, self.amount) < 0:
            message = _(
                "MONA Pay received %(paid)s VND, below the required %(required)s VND (%(code)s).",
                paid=paid_amount,
                required=self.amount,
                code=transaction_code,
            )
            if self.state == "pending":
                self.state_message = message
            else:
                self._set_pending(state_message=message)
            return "underpaid"

        self.provider_reference = transaction_code
        self._set_done(state_message=_("MONA Pay confirmed transaction %s.", transaction_code))
        self._finalize_post_processing()
        return "done"
