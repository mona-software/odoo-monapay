import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class MonaPayController(http.Controller):
    """Public QR page, status polling, and signed webhook endpoint."""

    @http.route(
        "/payment/monapay/qr",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def monapay_qr(self, token=None, **_kwargs):
        tx = request.env["payment.transaction"].sudo().search(
            [("monapay_display_token", "=", token or ""), ("provider_code", "=", "monapay")],
            limit=1,
        )
        if not tx:
            return request.not_found()
        return request.render(
            "payment_monapay.payment_page",
            {
                "tx": tx,
                "status_url": f"/payment/monapay/status/{tx.monapay_display_token}",
                "return_url": "/payment/status",
            },
        )

    @http.route(
        "/payment/monapay/status/<string:token>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
        save_session=False,
    )
    def monapay_status(self, token, **_kwargs):
        tx = request.env["payment.transaction"].sudo().search(
            [("monapay_display_token", "=", token), ("provider_code", "=", "monapay")],
            limit=1,
        )
        if not tx:
            return request.make_json_response({"error": "not_found"}, status=404)
        return request.make_json_response({"state": tx.state})

    @http.route(
        "/payment/monapay/webhook",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def monapay_webhook(self, **_kwargs):
        raw_body = request.httprequest.get_data(cache=False, as_text=False)
        timestamp = request.httprequest.headers.get("X-Mona-Timestamp", "")
        signature = request.httprequest.headers.get("X-Mona-Signature", "")

        providers = request.env["payment.provider"].sudo().search(
            [("code", "=", "monapay"), ("state", "!=", "disabled")]
        )
        provider = next(
            (
                item
                for item in providers
                if item._monapay_verify_signature(raw_body, timestamp, signature)
            ),
            None,
        )
        if not provider:
            _logger.warning("MONA Pay webhook rejected: invalid signature or timestamp")
            return request.make_json_response(
                {"success": False, "message": "Invalid signature."}, status=401
            )

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return request.make_json_response(
                {"success": False, "message": "Invalid JSON payload."}, status=400
            )

        try:
            outcome = provider._monapay_process_webhook(payload)
        except ValueError as exc:
            _logger.warning("MONA Pay webhook rejected: %s", exc)
            return request.make_json_response(
                {"success": False, "message": str(exc)}, status=400
            )

        messages = {
            "test": "Test webhook verified.",
            "not_found": "Webhook received; no matching transaction.",
            "underpaid": "Webhook received; amount is insufficient.",
            "duplicate": "Transaction was already processed.",
            "done": "Payment confirmed.",
        }
        return request.make_json_response(
            {"success": True, "message": messages[outcome]}, status=200
        )

