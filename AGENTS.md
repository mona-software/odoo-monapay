# AGENTS.md

- Treat `ref/openapi.json`, `ref/llms.txt`, and the WooCommerce reference webhook logic as the MONA Pay source of truth.
- Keep webhook verification on the unmodified raw body: `sha256=HMAC_SHA256(timestamp + "." + raw_body)`, maximum clock drift 300 seconds.
- Webhook payloads are flat. Do not invent an `event.data` envelope.
- Never log, commit, expose in views, or return `client_secret`, webhook secret, or access tokens.
- Preserve idempotency by `transaction_code`; underpayments must never mark an Odoo transaction paid.
- Run the Odoo test command in `README.md` after changes.

