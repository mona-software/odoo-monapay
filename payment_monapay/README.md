# MONA Pay for Odoo

Payment provider for Odoo 17/18 Website/eCommerce: customers pay by bank transfer with a dynamic VietQR for the exact amount, and an HMAC-SHA256 signed MONA Pay webhook marks the transaction done.

## Install

Copy this directory into your Odoo `addons_path`, update the Apps list and install **MONA Pay**. The module depends on `payment` and `website_sale`, and only supports VND.

## Configuration

In **Accounting → Configuration → Payment Providers → MONA Pay**, enter the client ID, client secret, webhook secret and VietQR fields (owner number and type, merchant ID, terminal ID, virtual account prefix, beneficiary name). Copy the displayed **Webhook URL** into MONA Pay with signature type `HMAC_SHA256`, then enable and publish the provider.

API reference: [monapay.vn/docs](https://monapay.vn/docs). Full instructions and tests: [github.com/mona-software/odoo-monapay](https://github.com/mona-software/odoo-monapay).

## License

MIT. See [LICENSE](LICENSE).

**MONA Pay is part of MONA Cloud by The MONA Group.**
