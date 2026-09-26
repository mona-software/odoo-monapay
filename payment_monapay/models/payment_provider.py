from datetime import timedelta

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from ..utils import verify_webhook_signature

class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("monapay", "MONA Pay")],
        ondelete={"monapay": "set default"},
    )
    monapay_api_base_url = fields.Char(
        string="API base URL",
        default="https://api.monapay.vn",
        required_if_provider="monapay",
    )
    monapay_client_id = fields.Char(
        string="Client ID", required_if_provider="monapay", groups="base.group_system"
    )
    monapay_client_secret = fields.Char(
        string="Client secret",
        required_if_provider="monapay",
        groups="base.group_system",
        copy=False,
    )
    monapay_webhook_secret = fields.Char(
        string="Webhook secret",
        required_if_provider="monapay",
        groups="base.group_system",
        copy=False,
    )
    monapay_owner_number = fields.Char(
        string="Owner number", required_if_provider="monapay"
    )
    monapay_owner_type = fields.Selection(
        [("PER", "Individual (PER)"), ("ORG", "Organization (ORG)")],
        string="Owner type",
        default="ORG",
        required_if_provider="monapay",
    )
    monapay_merchant_id = fields.Char(
        string="Merchant ID", required_if_provider="monapay"
    )
    monapay_terminal_id = fields.Char(
        string="Terminal ID", required_if_provider="monapay"
    )
    monapay_va_prefix = fields.Char(
        string="Virtual account prefix", required_if_provider="monapay"
    )
    monapay_beneficiary_name = fields.Char(
        string="Beneficiary name", required_if_provider="monapay"
    )
    monapay_access_token = fields.Char(copy=False, groups="base.group_system")
    monapay_access_token_expires_at = fields.Datetime(copy=False, groups="base.group_system")
    monapay_webhook_url = fields.Char(
        string="Webhook URL", compute="_compute_monapay_webhook_url"
    )

    @api.depends("code")
    def _compute_monapay_webhook_url(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        for provider in self:
            provider.monapay_webhook_url = (
                f"{base_url.rstrip('/')}/payment/monapay/webhook"
                if provider.code == "monapay" and base_url
                else False
            )

    @api.constrains("monapay_api_base_url")
    def _check_monapay_api_base_url(self):
        for provider in self.filtered(lambda item: item.code == "monapay"):
            if not (provider.monapay_api_base_url or "").startswith("https://"):
                raise ValidationError(_("MONA Pay API base URL must use HTTPS."))

    def _get_supported_currencies(self):
        currencies = super()._get_supported_currencies()
        if self.code == "monapay":
            return currencies.filtered(lambda currency: currency.name == "VND")
        return currencies

    def _get_default_payment_method_codes(self):
        self.ensure_one()
        if self.code != "monapay":
            return super()._get_default_payment_method_codes()
        return ["monapay"]

    def _monapay_verify_signature(self, raw_body, timestamp, signature, now=None):
        """Verify the raw MONA Pay webhook body and its five-minute replay window."""
        self.ensure_one()
        return verify_webhook_signature(
            raw_body, timestamp, signature, self.monapay_webhook_secret or "", now=now
        )

    def _monapay_api_request(self, path, payload, retry=True):
        self.ensure_one()
        token = self._monapay_get_access_token()
        url = f"{self.monapay_api_base_url.rstrip('/')}{path}"
        headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Client-Secret": self.monapay_client_secret,
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=20)
        except requests.RequestException as exc:
            raise UserError(_("Could not connect to MONA Pay: %s", exc)) from exc
        if response.status_code == 401 and retry:
            self.write({"monapay_access_token": False, "monapay_access_token_expires_at": False})
            return self._monapay_api_request(path, payload, retry=False)
        return self._monapay_unwrap_response(response)

    def _monapay_get_access_token(self):
        self.ensure_one()
        now = fields.Datetime.now()
        if (
            self.monapay_access_token
            and self.monapay_access_token_expires_at
            and self.monapay_access_token_expires_at > now + timedelta(seconds=60)
        ):
            return self.monapay_access_token

        url = f"{self.monapay_api_base_url.rstrip('/')}/api/v1/oauth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.monapay_client_id,
            "client_secret": self.monapay_client_secret,
        }
        try:
            response = requests.post(url, json=payload, headers={"Accept": "application/json"}, timeout=20)
        except requests.RequestException as exc:
            raise UserError(_("Could not authenticate with MONA Pay: %s", exc)) from exc
        data = self._monapay_unwrap_response(response)
        token = data.get("access_token")
        if not token:
            raise UserError(_("MONA Pay authentication response did not contain an access token."))
        expires_in = max(1, int(data.get("expires_in", 3600)))
        self.write(
            {
                "monapay_access_token": token,
                "monapay_access_token_expires_at": now + timedelta(seconds=expires_in),
            }
        )
        return token

    @staticmethod
    def _monapay_unwrap_response(response):
        try:
            body = response.json()
        except ValueError as exc:
            raise UserError(_("MONA Pay returned an invalid JSON response (HTTP %s).", response.status_code)) from exc
        if not response.ok or body.get("success") is False:
            message = body.get("message") or body.get("detail") or _("Unknown error")
            raise UserError(_("MONA Pay error (HTTP %(status)s): %(message)s", status=response.status_code, message=message))
        data = body.get("data")
        if not isinstance(data, dict):
            raise UserError(_("MONA Pay response did not contain a data object."))
        return data

    def _monapay_process_webhook(self, payload):
        self.ensure_one()
        if not isinstance(payload, dict):
            raise ValueError("Invalid payload.")
        if payload.get("transaction_code") == "DUMMY123":
            return "test"
        event = payload.get("event") or payload.get("event_type") or "TRANSACTION_IN"
        if event != "TRANSACTION_IN":
            raise ValueError("Unsupported event.")
        required = {"amount", "description", "transaction_code", "account_number"}
        if not required.issubset(payload):
            raise ValueError("Missing required webhook fields.")
        if payload.get("type") not in (None, "income"):
            raise ValueError("Webhook is not an incoming transaction.")

        tx = self.env["payment.transaction"].sudo()._monapay_find_transaction(payload, self)
        if not tx:
            return "not_found"
        return tx._monapay_apply_payment(payload)
