# Gmail OTP: final production deployment gate

Ngày 16/11/2026 — **NO-GO: chưa xác thực phục hồi độc lập DPAPI và chưa có kênh cảnh báo chủ động.** Đây không phải phê duyệt Phase F.

## Bằng chứng

- Người dùng xác nhận project Neon `autumn-sound-55302844`, branch `br-gentle-shape-a166ho81` là production cho `english_video_db`. Không có quyền Neon Console/API để xác nhận độc lập project/branch/plan/retention. Cấu hình API và truy vấn chỉ đọc xác nhận direct endpoint `ep-icy-lab-a16xdltv.ap-southeast-1.aws.neon.tech`, database `english_video_db`, revision `f31a7c4d2e01`, 4 user; 0 transaction trên 60 giây trong phạm vi role nhìn thấy tại thời điểm kiểm tra.
- `english-video-api` và Caddy active; EnvironmentFile `/home/azureuser/english-video/backend/.env` thuộc uid 1000, mode 0600. Azure có khoảng 25 GB trống, 484 MiB RAM available, không swap; API dùng khoảng 82 MiB tại thời điểm kiểm tra. Worker làm tăng sử dụng RAM, phải theo dõi sau deploy.
- SHA-256 candidate `866A2DCAB0A7EF9054599DFA0408B67CB7C95BFC223F3746F9B4DF61E3A765A3`, 17 file khớp source, không có `.env`; Alembic chain local `f31a7c4d2e01 → a42c7f3e9810 → b531d7e28a22 → c693a17e4d08`.
- SHA-256 backup mã hóa `DEC595AA3F860F191802D56870C9FD2B49C7038DE585866B6D07808D75520892`. Backup giải mã bằng DPAPI và `pg_restore --list` thành công với container PostgreSQL 18 không network; không kết nối database production. Kiểm thử restore/migration, fingerprints 12 bảng và lock timeout trước đó xem `OTP_DIRECT_DEPLOY_PREFLIGHT.md`.
- Worker unit và ba unit theo dõi local được `systemd-analyze verify` kiểm tra trong container tạm, với đường dẫn Python giả lập; các executable tương ứng có tồn tại trên Azure. Chưa chứng minh unit chạy thành công với production config hoặc quyền thực tế.
- Key Fernet production đã được chuẩn bị trong thư mục được hạn chế ACL và bảo vệ DPAPI; API và worker dự kiến dùng cùng `EnvironmentFile` mode 0600. SMTP key hiện tại không thay đổi; chưa cấu hình Fernet/SMTP trên Azure.
- Các template `deploy/english-video-email-queue-check.service`, `.timer`, `deploy/english-video-email-alert.service` chạy kiểm tra queue và ghi lỗi vào journal. Chúng không có trong candidate 17 file, cần đưa riêng sau phê duyệt. Journal không phải kênh thông báo chủ động: cần cấu hình và kiểm tra bộ thu cảnh báo/nhân sự trực.

## Điều kiện chưa đạt

1. Backup gốc phụ thuộc DPAPI của profile Windows. Người dùng nói có khóa công khai độc lập và sẽ cung cấp; chưa có khóa để bọc key backup, chưa thử giải mã bằng private key đó hoặc cất bản sao an toàn ở vị trí độc lập. `scripts/prepare_backup_recovery_capsule.py` hỗ trợ RSA public key/certificate PEM, `scripts/verify_portable_backup.py` xác minh không cần DPAPI; test end-to-end dùng key tạm và dump fixture độc lập đã pass. Nếu public key thuộc định dạng khác cần hỗ trợ tương ứng, không yêu cầu gửi private key hoặc passphrase qua chat.
2. Cần kênh nhận cảnh báo chủ động và kiểm tra báo động, bao gồm worker dừng, queue lỗi/già và DB mất kết nối. `failed`/`uncertain` được đếm tích lũy nên cần quy trình xử lý/ghi nhận; không tự retry uncertain.
3. Không có quyền Brevo Console xác minh sender/domain authentication, SMTP activation hoặc quota. Không có bằng chứng header mới; không gửi email thật trước phê duyệt riêng. SMTP key cũ từng lộ, giữ nguyên theo yêu cầu.
4. Restore cho kết quả CHECK constraint khác biểu diễn trên 4 constraint; mẫu hợp lệ/sai/NULL cho cùng kết quả, chưa chứng minh đầy đủ. Owner/grant chưa đối chiếu do restore dùng `--no-owner --no-privileges`. Chưa thử đăng nhập bằng mật khẩu của 4 tài khoản thực.

## Kế hoạch Phase F dự thảo — chưa thực hiện

1. Thống nhất cửa sổ, xác nhận backup và recovery portable, checksum, revision, người trực và không có transaction dài; xem lại quyền/owner backup. Dừng API có kiểm soát để ngăn đăng ký và ghi từ API trong quá trình chuyển tiếp; Caddy tiếp tục chạy và có thể trả lỗi trong lúc API dừng. Không giả định thao tác này chặn các client DB khác; xác minh và hạn chế chúng trong cửa sổ.
2. Tạo bản sao an toàn code/config hiện hành và kiểm tra hash; đưa 3 migration scripts vào deployment, xác nhận Alembic nhận diện chain. Các script là `a42c7f3e9810_email_verification.py`, `b531d7e28a22_otp_send_limits.py`, `c693a17e4d08_email_outbox.py`.
3. Chạy upgrade đến `c693a17e4d08` với lock_timeout/statement_timeout đã thống nhất, dựa trên diễn tập nhưng không coi thời gian local là dự báo. Kiểm tra revision, schema và số liệu tài khoản; dừng khi có sai lệch.
4. Deploy candidate 17 file trong manifest, thiết lập EnvironmentFile bảo vệ mode 0600 có SMTP key hiện tại và Fernet production chung cho API/worker, không in secret, không đưa secret vào shell history/argument. Cài worker unit và 3 unit giám sát riêng; cấu hình bộ nhận cảnh báo được chấp thuận.
5. Start API, start worker và timer; kiểm tra service API/Caddy/worker/timer, queue, health/OpenAPI, revision và logs lọc secret. Không tạo account production hoặc gửi mail thật nếu chưa phê duyệt riêng. Test đăng nhập tài khoản cũ khi có thông tin thử hợp lệ được cấp an toàn.
6. Nếu code lỗi, dừng worker và khôi phục code cũ đã backup; phải tiếp tục chặn đăng ký vì code cũ bỏ qua OTP. Không tự downgrade schema. Nếu database lỗi, đánh giá forward-fix hoặc trình kế hoạch restore riêng; không tự restore đè production.

## File trong candidate

`app/api/deps.py`; `app/api/v1/endpoints/auth.py`, `users.py`; `app/core/config.py`; `app/models/__init__.py`, `user.py`, `password_reset_otp.py`, `email_verification_otp.py`, `email_outbox.py`; `app/services/email_sender.py`, `email_outbox.py`; `scripts/email_outbox_worker.py`, `email_outbox_status.py`; ba migration ở trên; `deploy/english-video-email-worker.service`.

## Không thực hiện

Không migration/deploy/restart, không thay production secret/service, không đổi SMTP key, không tạo branch test/staging, không gửi mail thật hoặc ghi database production. Thời gian gián đoạn và cửa sổ chưa được chốt; không thể dự báo từ 1,2 giây migration trên máy local.
