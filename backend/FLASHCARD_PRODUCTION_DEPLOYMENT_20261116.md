# Flashcard production deployment — 16/11/2026

## SUCCESS

- Người dùng phê duyệt Phase F với candidate strict SHA-256 `B52EBDAE32CAE84235DAF83B3AD3FDD5E9D7B252763AE5DDD276117FDA23A65D`. Candidate xác minh trên VM, 5 file sau khi giải nén đều khớp archive. Staging file ở `/home/azureuser/flashcard-deploy-20261116122653`, thư mục mode 0700.
- Production database direct `english_video_db`: Alembic `c693a17e4d08 → d4e9b137c802` thành công với `lock_timeout=5s`, `statement_timeout=60s`. Sau migration có 5 tài khoản và 3 saved words; fingerprint 13 bảng cũ khớp backup đã restore, không có sai khác tại thời điểm so sánh.
- Backup mới trước deploy: database `C:\Users\HP\AppData\Local\EnglishThroughVideo\production-backups\english-video-20261116T122603Z.pgdump.fernet`, SHA-256 `A3703D9911D98C6D474C23FBA5AC6A1C40814FF5F0F71738348AB73EEB4864FD`; code/config `azure-code-config-20261116T122556Z.tar.gz.fernet`, SHA-256 `94321012D76DB3BFE0ABFB7B93EF2351362C59E4E6E3233B12EBFF749B6E4DCA`. Backup mã hóa, giải mã được; database được restore và diễn tập migration PostgreSQL 18 local thành công. Code/config giải mã và 76 file khớp production trước triển khai.
- API đã tạm dừng và start lại; API, Caddy, email worker, queue timer active. HTTPS health và OpenAPI 200; queue email `sent=2`, check pass. So sánh sau deploy: `.env`, cấu hình và source OTP/email worker được chọn không đổi so với backup; SMTP/Fernet key không thay.
- Smoke test chỉ đọc bằng tài khoản test đã có: login 200, JWT `/users/me` 200, flashcard overview 200, due queue 200, capability idempotency true; tài khoản này có 0 thẻ đến hạn nên chưa test review ghi dữ liệu.
- APK debug local SHA-256 `CE8AA11ADC1652BC338DFCC7E1E8CA066F45C6598DFBB18252A8E699DC75B9C8`; URL production, ký Android Debug. Chưa cài do ADB không thấy thiết bị.

## WARNING / BLOCKED

- Chưa thử review thật trên production: cần tài khoản/thẻ đến hạn được người dùng cho phép và phê duyệt phạm vi ghi dữ liệu. Không tạo user, không review và không gửi email thật trong lượt này.
- Client cũ không gửi `request_id` vẫn review được thẻ đến hạn nhưng không được bảo đảm idempotency; review chưa đến hạn trả 409 theo lựa chọn người dùng, client cũ có thể hiển thị lỗi 409 không phù hợp.
- APK chỉ debug-signed, chưa phát hành/cài lên thiết bị; không coi là release ký production. Queue email chỉ có journal, không cảnh báo chủ động. Backup phụ thuộc Windows DPAPI; restore thử dùng `--no-owner --no-privileges`.
- OTP routes và worker đang active; không gửi email thật nên chưa xác minh lại giao mail end-to-end sau deploy. Không có kiểm thử flashcard trên thiết bị vật lý.

## NOT EXECUTED / RECOVERY

- Không đổi SMTP/Fernet key, email worker, Caddy, Gmail OTP hoặc Blob; không downgrade, restore đè production hay gửi email thật.
- Nếu lỗi backend, kiểm tra log đã lọc secret; phục hồi code cũ tương thích schema mở rộng từ backup và giữ bảng `flashcard_review_requests`. Không tự downgrade xóa kết quả idempotency. Sự cố dữ liệu cần đánh giá forward-fix; restore production chỉ theo phê duyệt riêng.
