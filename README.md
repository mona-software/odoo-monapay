# MONA Pay for Odoo

Odoo 17/18 payment provider module (`payment_monapay`) that lets Odoo Website/eCommerce customers pay by bank transfer with a dynamic VietQR, and marks the payment transaction done when a signed MONA Pay webhook confirms the transfer.

## Requirements

- Odoo 17 or 18 with the `payment` and `website_sale` modules
- Python `requests` (already an Odoo dependency)
- A company currency or pricelist in `VND`; the provider only supports VND, whole-number amounts
- A MONA Pay account with API client credentials, VietQR/virtual-account details and a webhook secret
- HTTPS and an NTP-synchronised clock in production (webhooks outside a five-minute window are rejected)

## Install

1. Copy the `payment_monapay/` directory into a folder on your Odoo `addons_path`.
2. Update the Apps list, search for **MONA Pay** and install the module.

## Configuration

Open **Accounting → Configuration → Payment Providers → MONA Pay** and fill in:

| Field | Notes |
| --- | --- |
| API base URL | Defaults to `https://api.monapay.vn`; must use HTTPS |
| Client ID, Client secret | MONA Pay API client credentials |
| Webhook secret | Shared secret for webhook signatures |
| Owner number, Owner type | VietQR beneficiary account; type `ORG` or `PER` |
| Merchant ID, Terminal ID | From your MONA Pay VietQR setup |
| Virtual account prefix | `virtualAccountPrefix` sent with each QR |
| Beneficiary name | Name shown on the QR |
| Webhook URL | Read-only, `<web.base.url>/payment/monapay/webhook` |

Copy the **Webhook URL** into MONA Pay, choose `HMAC_SHA256` as the signature type, then enable the provider and publish it on the website. Credential fields are restricted to system administrators; do not commit them anywhere.

## Usage

1. Odoo exchanges the client ID and client secret for a bearer token (`POST /api/v1/oauth/token`) and caches it until shortly before it expires.
2. At checkout Odoo calls `POST /api/v1/acb/qr-payment/generate` with order code and transfer memo `DH<transaction_id>`, and sets the transaction to pending.
3. The payment page shows the QR and polls `/payment/monapay/status/<token>` every 3 seconds.
4. MONA Pay posts a flat JSON payload to `/payment/monapay/webhook` with `X-Mona-Timestamp` and `X-Mona-Signature` headers.
5. The module verifies `sha256=HMAC_SHA256(timestamp + "." + raw_body)` with a 300-second window, accepts only incoming transactions, finds the transaction by the `DH<id>` memo or the virtual account number, rejects reused transaction codes, keeps underpaid transactions pending, and otherwise calls `_set_done()`.

API reference: [monapay.vn/docs](https://monapay.vn/docs).

## Development

Core tests (signature, memo parsing, amount rules) run without Odoo:

```bash
python3 -m unittest discover -s tests -v
```

Integration tests (`TransactionCase`) need an Odoo environment with its dependencies installed:

```bash
odoo-bin -d monapay_test --addons-path=addons,. -i payment_monapay --test-enable --stop-after-init --test-tags=/payment_monapay
```

## License

MIT. See [LICENSE](LICENSE).

**MONA Pay is part of MONA Cloud by The MONA Group.**
