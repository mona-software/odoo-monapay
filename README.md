# MONA Pay for Odoo 17/18

Module thanh toán chuyển khoản MONA Pay cho Odoo Website/eCommerce. Khách chọn **Chuyển khoản MONA Pay (VietQR)**, quét VietQR động đúng số tiền/nội dung; webhook hợp lệ sẽ đánh dấu transaction `done` và Odoo tiếp tục xác nhận đơn bán.

MONA Pay xác nhận chuyển khoản ngân hàng tự động (VietQR động, tài khoản ảo, webhook) — tiền vào thẳng tài khoản của bạn, MONA Pay không giữ tiền. Ngân hàng hỗ trợ: xem [monapay.vn/ngan-hang](https://monapay.vn/ngan-hang).

## Cài đặt

1. Chép `payment_monapay/` vào một thư mục trong `addons_path` của Odoo 17 hoặc 18.
2. Cập nhật Apps List, tìm **MONA Pay**, rồi cài module.
3. Vào **Accounting / Configuration / Payment Providers / MONA Pay**.
4. Nhập `client_id`, `client_secret`, webhook secret và thông tin QR/VA trong hồ sơ MONA Pay.
5. Chép **Webhook URL** từ form Odoo sang MONA Pay, chọn HMAC-SHA256, sau đó bật provider và publish trên website.

Không commit credential. Production phải dùng HTTPS và đồng bộ giờ hệ thống (NTP).

## Luồng chạy

1. Odoo đổi `client_id` + `client_secret` lấy Bearer token.
2. Odoo gọi `POST /api/v1/acb/qr-payment/generate`, gắn `DH<transaction_id>` vào nội dung chuyển khoản.
3. Trang checkout hiển thị QR và poll trạng thái mỗi 3 giây.
4. MONA Pay POST payload phẳng tới `/payment/monapay/webhook` với `X-Mona-Timestamp` và `X-Mona-Signature`.
5. Module kiểm HMAC trên raw body, cửa sổ 5 phút, mã giao dịch, số tiền và nội dung/tài khoản ảo trước khi gọi `_set_done()`.

## Kiểm thử

Test lõi không cần Odoo:

```bash
python3 -m unittest discover -s tests -v
```

Test tích hợp `TransactionCase` trong môi trường Odoo đã cài dependencies:

```bash
odoo-bin -d monapay_test --addons-path=addons,. -i payment_monapay --test-enable --stop-after-init --test-tags=/payment_monapay
```

## Ảnh marketplace

- `docs/screenshot-checkout.png` — TODO: màn hình chọn MONA Pay.
- `docs/screenshot-vietqr.png` — TODO: trang VietQR động.
- `docs/screenshot-config.png` — TODO: form cấu hình (che toàn bộ secret).

## English

This Odoo 17/18 payment provider adds automatic bank-transfer confirmation with dynamic VietQR. Funds go directly to the merchant's bank account; MONA Pay does not hold funds.

Install `payment_monapay` in your Odoo addons path, configure the client ID, client secret, webhook secret and QR profile fields, copy the displayed webhook URL to MONA Pay, then enable and publish the provider. The checkout shows an exact-amount QR; the signed flat webhook verifies timestamp, amount, order content and transaction id before completing the Odoo transaction.

Documentation: [monapay.vn](https://monapay.vn) · [monapay.vn/docs](https://monapay.vn/docs)

## License

MIT. See [LICENSE](LICENSE).

**MONA Pay is part of MONA Cloud by The MONA Group.**

**MONA Pay thuộc bộ MONA Cloud của The MONA Group.**
