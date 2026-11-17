# Gmail OTP production: preflight và đề nghị xác nhận

Ngày 16/11/2026. Tài liệu này cập nhật `OTP_DIRECT_DEPLOY_PREFLIGHT.md` và `OTP_FINAL_DEPLOYMENT_GATE.md` theo quyết định mới nhất của người dùng: chấp nhận rủi ro DPAPI và chưa có thông báo queue chủ động, không yêu cầu RSA, Neon branch test hoặc Azure staging. Không thực hiện Phase F trước khi nhận xác nhận riêng.

## Kết quả preflight

- Người dùng xác nhận project `autumn-sound-55302844` và branch `br-gentle-shape-a166ho81`; host database production được đối chiếu read-only là `ep-icy-lab-a16xdltv.ap-southeast-1.aws.neon.tech`, database `english_video_db`, revision `f31a7c4d2e01`, 4 tài khoản. Lần kiểm tra không thấy transaction quá 60 giây trong phạm vi role quan sát được.
- `english-video-api`, Caddy active; khoảng 481 MiB RAM available, không swap và khoảng 25 GB trống. Theo dõi bộ nhớ khi chạy thêm worker.
- Candidate SHA-256 `866A2DCAB0A7EF9054599DFA0408B67CB7C95BFC223F3746F9B4DF61E3A765A3`, 17 file khớp source; Alembic chain đầy đủ. Các dependency đã được đối chiếu trước đó.
- Backup database mã hóa SHA-256 `DEC595AA3F860F191802D56870C9FD2B49C7038DE585866B6D07808D75520892`; backup code/config `324E02B74EBFCDDBEF29A4281CD08D5E5B4E2CF04DA73644939158F19BD23115`. Backup code/config giải mã và 67 file khớp production hiện tại.
- Giải mã, pg_restore và khôi phục lại vào PostgreSQL 18 local độc lập thành công. Tại thời điểm so sánh hiện tại, 12 bảng cùng số dòng và fingerprint dữ liệu, schema cột và index khớp; 4 CHECK constraints có cách ép kiểu khác nhưng đối chiếu chính xác hình dạng biểu thức và các mảng hằng trên hai server xác nhận tương đương. Revision và 4 tài khoản khớp. Restore dùng `--no-owner --no-privileges`, chưa xác minh owner/grant.
- Trước đó migration đã được thử thành công trên bản restore, bảo toàn fingerprint dữ liệu và 4 tài khoản; mô phỏng lock timeout dừng và rollback thành công. API cũ chạy được trên schema mở rộng nhưng đăng ký theo luồng cũ không xác minh OTP.
- Đã chuẩn bị Fernet key production khác staging, được bảo vệ DPAPI; SMTP key hiện tại có sẵn local và không thay đổi. Worker unit và ba unit kiểm tra queue/ghi journal được kiểm tra syntax systemd trong container; 3 unit monitoring nằm ngoài candidate và cần được chuyển riêng.

## Danh sách thao tác production chờ xác nhận

1. Kiểm tra lại checksum, backup, revision, tình trạng service/transaction ngay trước thao tác. Dừng `english-video-api` để ngăn đăng ký và các API ghi dữ liệu trong chuyển tiếp; Caddy vẫn chạy và client có thể nhận lỗi cho đến khi API được mở lại. Việc dừng API không chặn các client database khác.
2. Đưa ba migration scripts từ candidate lên đúng chỗ, xác nhận Alembic nhận diện chain rồi upgrade đến `c693a17e4d08` với `lock_timeout=5s`, `statement_timeout=60s`; dừng khi có lỗi, kiểm tra trạng thái transaction/revision và dữ liệu.
3. Cài 17 file candidate theo manifest, bảo tồn các file khác và cấu hình cũ. Thiết lập SMTP bằng chính key hiện tại và Fernet key production đã chuẩn bị qua kênh bảo mật; không in secret hoặc ghi vào arguments/history. Giữ các giá trị DB/JWT hiện hữu, file env có quyền 0600 và API/worker dùng cùng Fernet key.
4. Cài systemd worker và riêng ba unit queue-check/alert; start API, worker, timer, không restart Caddy. Kiểm tra journal, trạng thái queue, API/Caddy/worker/timer, revision, health/OpenAPI và số liệu tài khoản. Queue alert chỉ ghi journal, chưa có kênh chủ động.
5. Mở lại đăng ký bằng cách đưa API mới vào hoạt động khi kiểm tra đạt. Không gửi email thật hoặc tạo tài khoản test production khi chưa có phép riêng; yêu cầu Gmail test và quyền gửi sau khi triển khai.

Thời gian gián đoạn chưa đo được. Khi code lỗi: dừng worker, phục hồi code cũ và giữ đăng ký bị chặn vì API cũ không yêu cầu OTP; không tự downgrade. Nếu database lỗi: dừng, đánh giá forward-fix và không restore đè khi chưa được duyệt riêng. Backup phụ thuộc Windows DPAPI; người dùng đã chấp nhận hạn chế và rủi ro key SMTP từng lộ. Chưa xác nhận Brevo quota, sender/domain authentication hay email delivery thực tế trong lượt này.
