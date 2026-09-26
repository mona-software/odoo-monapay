# MONA Pay for Odoo 17/18

Provider chuyển khoản ngân hàng tự động cho Odoo Website/eCommerce: VietQR động đúng số tiền/nội dung, tài khoản ảo và webhook HMAC-SHA256. Tiền vào thẳng tài khoản của merchant; MONA Pay không giữ tiền.

## Cài đặt / Configuration

Chép thư mục này vào `addons_path`, cập nhật Apps List và cài **MONA Pay**. Trong Payment Providers, nhập client ID, client secret, webhook secret và thông tin QR; chép webhook URL hiển thị sang MONA Pay, sau đó enable/publish provider.

Copy this directory into the Odoo `addons_path`, update the Apps List and install **MONA Pay**. Configure the client ID, client secret, webhook secret and QR profile, copy the displayed webhook URL to MONA Pay, then enable and publish the provider.

Tài liệu / Documentation: https://monapay.vn · https://monapay.vn/docs

Kiểm thử / Tests: xem `../README.md` trong source repository hoặc chạy Odoo với `--test-tags=/payment_monapay`.

License: MIT.

