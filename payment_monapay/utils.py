import hashlib
import hmac
import re
import time

SIGNATURE_RE = re.compile(r"^sha256=[a-f0-9]{64}$")
ORDER_CODE_RE = re.compile(r"(?:^|[^A-Z0-9])(DH[0-9]+)(?:$|[^0-9])", re.IGNORECASE)


def verify_webhook_signature(raw_body, timestamp, signature, secret, now=None, tolerance=300):
    """Verify MONA Pay HMAC-SHA256 against the exact request bytes."""
    if not secret or not isinstance(timestamp, str) or not timestamp.isdigit():
        return False
    if len(timestamp) > 12 or not isinstance(signature, str) or not SIGNATURE_RE.fullmatch(signature):
        return False
    current_time = int(time.time() if now is None else now)
    if abs(current_time - int(timestamp)) > tolerance:
        return False
    body = raw_body if isinstance(raw_body, bytes) else str(raw_body).encode("utf-8")
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), timestamp.encode("ascii") + b"." + body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def extract_order_code(description):
    """Extract only a delimited DH<number> order code from transfer content."""
    match = ORDER_CODE_RE.search(description or "") if isinstance(description, str) else None
    return match.group(1).upper() if match else None


def amount_is_sufficient(paid_amount, required_amount):
    """Mirror the production rule: overpayments pass, underpayments do not."""
    try:
        return float(paid_amount) >= float(required_amount)
    except (TypeError, ValueError):
        return False

