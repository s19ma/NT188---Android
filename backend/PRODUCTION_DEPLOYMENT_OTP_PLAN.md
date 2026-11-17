# Gmail OTP – kết quả chuẩn bị và kế hoạch production

Ngày 16/11/2026. **NOT READY FOR PRODUCTION.** Chưa có phê duyệt migration/deploy, backup Neon chưa được phục hồi thử, và các bước production bên dưới chưa được thực hiện.

## SUCCESS

- Đã đọc `PRODUCTION_READINESS_EMAIL_OTP.md`, source auth, SMTP, outbox, migration và Android. Không tìm thấy `PROJECT_CONTEXT_NT118_R15.md` trong workspace. Git status/branch không xác định được vì workspace không phải Git repository.
- Kiểm tra read-only: `english-video-api` và Caddy active/enabled; HTTPS `/health` healthy; database production ở revision `f31a7c4d2e01`. Service dùng working directory `/home/azureuser/english-video/backend`, EnvironmentFile tương ứng; file production hiện có quyền 600. Cryptography và Alembic đã cài trong venv production. SMTP host, username, key và sender **không hiện diện trong cấu hình production được đọc**; không thay đổi hoặc ghi đè key nào.
- OTP hash và Fernet-encrypted payload trong cùng DB transaction. Worker claim `FOR UPDATE SKIP LOCKED`, commit trước SMTP; pre-send failure retry/backoff, kết quả không rõ/worker chết chuyển `uncertain`, không retry tự động. Không cam kết exactly-once.
- Sửa race resend/worker: worker khóa hàng OTP trước khi chốt `sending`; resend khóa OTP và từ chối khi job tương ứng đang gửi. Recheck hạn trước khi gọi SMTP. Test đồng thời thực hiện với mock sender; vẫn không thể bảo đảm OTP còn hạn tại thời điểm email được nhận do độ trễ mạng.
- Android wording xác minh/forgot/resend không còn nói chắc mã đã gửi khi request chỉ xếp hàng. Android debug build thành công.
- PostgreSQL Docker 16 tại `127.0.0.1:5433`: **30 pytest pass, 0 fail**, 1 cảnh báo Starlette/httpx; sender mock, không gửi email thật. Bao gồm OTP đúng/sai/hết hạn, reset, rate limit, concurrent resend, hai worker claim cùng job, rollback/commit fail, timeout mô phỏng, worker claim bỏ dở, encryption, pre-send retry. Không chứng minh partition/process crash thật hoặc tải lớn.
- Database fixture Docker độc lập `english_video_migration_test`: tạo account giả **trước** migration, upgrade `f31a7c4d2e01 → a42c7f3e9810 → b531d7e28a22 → c693a17e4d08`, login account fixture HTTP 200 sau upgrade. Fixture không phải bản sao Neon; không chứa dữ liệu production.
- SQL upgrade offline đã review: thêm `users.email_verified DEFAULT true`, bảng `email_verification_otps`, các cột send limit, bảng/index `email_outbox`. Upgrade không có DROP/TRUNCATE. Đây không chứng minh migration không lock hoặc không downtime trên Neon.
- Chuẩn bị worker unit local `deploy/english-video-email-worker.service` và script tổng hợp queue `scripts/email_outbox_status.py`, không chứa secret hoặc payload. Candidate tar local `deploy/email-otp-local-candidate.tar`, SHA256 `B60A33DE2F216EA6C3BB690AC3700EBFA53A13ECD6C0286F5EE718034DF297CD`; danh sách được kiểm tra, không chứa `.env`. Candidate chưa được triển khai hoặc xác minh tương thích đầy đủ trên staging.

## WARNING

- SMTP key cũ từng xuất hiện trong chat và được giữ nguyên theo yêu cầu; rủi ro lộ key **chưa được khắc phục**. Không rotate/revoke/thay key trong lượt này.
- SMTP không bảo đảm exactly-once. `uncertain` cần theo dõi và quy trình xử lý thủ công, không retry tự động. Crash sau commit claim nhưng trước gửi cũng bị xem là uncertain, có thể không gửi được thư.
- Mã hết hạn từ lúc enqueue. Worker dừng/backlog có thể khiến mã hết hạn trước khi gửi. Cần cảnh báo queue, retry/uncertain, tuổi job và worker; script hiện chỉ in aggregate, chưa có cảnh báo tự động.
- Fernet key phải độc lập JWT/SMTP và phải giống nhau giữa API/worker. Mất hoặc thay key khi còn job pending có thể khiến job lỗi; chưa có key rotation/key versioning hoặc thử recovery thực tế. Không in key trong lệnh/log.
- `ALTER TABLE ... ADD COLUMN ... NOT NULL DEFAULT` cần khóa bảng; thời gian chờ lock trên Neon chưa đo, phụ thuộc transaction đồng thời/kích thước bảng. `CREATE INDEX` trên bảng outbox mới sẽ nhỏ lúc tạo, nhưng vẫn cần xem lock timeout và theo dõi.
- DNS trước đó xác nhận DMARC `p=none` và hai tên CNAME DKIM; không khẳng định SPF/DKIM/DMARC pass từ email headers. Chưa xác minh Brevo authentication/quota/SMTP activation trực tiếp; sender Verified chỉ là thông tin người dùng cung cấp.
- `scripts/gmail_test_server.py` là helper thử đồng bộ cũ, chưa phù hợp worker outbox và revision mới; không dùng để kiểm tra outbox thật.

## BLOCKED

- Chưa có bằng chứng Neon plan/retention/PITR, restore point, phục hồi vào project/database độc lập và đối chiếu dữ liệu. Không thể khẳng định backup recoverable.
- Chưa có bản sao độc lập Neon để thử migration, đo lock/downtime và xác minh login tài khoản có sẵn thực tế.
- Chưa xác nhận sender/domain DKIM/SPF/DMARC và quota Brevo qua giao diện/email headers. Không được gửi email thật nếu chưa có phép riêng.
- Chưa chuẩn bị secret Fernet trên server, cấu hình SMTP/worker, alerting hay staging. Vì production hiện không có SMTP key được cấu hình, phương thức chuyển key hiện có từ local phải được phê duyệt và thực hiện an toàn mà không in/ghi đè key; không suy đoán giá trị.
- Chưa test Android register/verify/reset/rotation trên thiết bị với API outbox và SMTP giả lập đầy đủ. Chưa xác minh network partition DB sau claim, key rotation, retry nhiều lần hoặc khôi phục sau crash thật.

## NOT EXECUTED

- Không chạy migration, deploy, restart service, sửa env/secret, gửi email hay ghi DB production; không thay key SMTP. Không thay Caddy/Blob/network; không commit/push.

## Files changed trong lượt này

- `app/services/email_outbox.py`, `app/api/v1/endpoints/auth.py`: đồng bộ worker/resend và kiểm tra hạn trước gửi.
- `tests/test_email_outbox_docker.py`: kiểm thử race gửi lại khi worker đang gửi.
- `DoAn/app/src/main/java/com/example/englishthroughvideo/OtpVerificationActivity.java`, `ForgotPasswordOtpActivity.java`: thông báo async.
- `deploy/english-video-email-worker.service`, `scripts/email_outbox_status.py`: template worker và công cụ aggregate local.
- `deploy/email-otp-local-candidate.tar`, báo cáo này: candidate và kế hoạch. Các file outbox/migration trước đó không được coi là mới tạo trong lượt này.

## Dự thảo lệnh sau khi hoàn tất blockers và được phê duyệt riêng

Không chạy các lệnh này lúc này. Trước tiên cần xác nhận PITR và restore độc lập, thử migration trên restore, đo lock, kiểm tra diff/candidate và backup code cùng cấu hình an toàn. `<BACKUP_DIR>` và `<CANDIDATE_TAR>` phải được xác định, kiểm tra quyền và xác thực checksum trước khi chạy.

```sh
# Sao lưu các file code sẽ thay; không đưa .env/secret vào archive code.
cd /home/azureuser/english-video/backend
tar -cf <BACKUP_DIR>/backend-before-email.tar app/api/deps.py app/api/v1/endpoints/auth.py app/api/v1/endpoints/users.py app/core/config.py app/models/__init__.py app/models/user.py app/models/password_reset_otp.py
# Sau khi DBA xác nhận revision/restore và đặt lock_timeout phù hợp:
.venv/bin/alembic current
.venv/bin/alembic upgrade c693a17e4d08
# Candidate cần được kiểm tra đường dẫn/nội dung trước khi giải nén.
tar -tf <CANDIDATE_TAR>
tar -xf <CANDIDATE_TAR> -C /home/azureuser/english-video/backend
# Chỉ sau khi secret Fernet và SMTP đã được cấu hình an toàn, giữ key hiện có:
sudo install -m 0644 deploy/english-video-email-worker.service /etc/systemd/system/english-video-email-worker.service
sudo systemctl daemon-reload
sudo systemctl restart english-video-api
sudo systemctl enable --now english-video-email-worker
systemctl is-active english-video-api english-video-email-worker caddy
.venv/bin/alembic current
.venv/bin/python -m scripts.email_outbox_status
curl -fsS https://englishvideoapi20261114.eastasia.cloudapp.azure.com/health
```

Thứ tự migration và code cần được thử staging: trong khoảng chuyển tiếp, API cũ vẫn phải hoạt động trên schema mở rộng; không chạy code mới trước khi schema sẵn sàng. Sau đó kiểm tra OpenAPI, GET public và authenticated smoke test bằng tài khoản test; gửi email thật chỉ khi được phép riêng.

Nếu code mới lỗi sau migration, dừng worker và khôi phục code archive tương thích schema mở rộng; xem log đã lọc secret, kiểm tra queue và forward-fix. Không chạy Alembic downgrade xóa bảng/cột có dữ liệu. Khôi phục database chỉ theo runbook PITR đã được diễn tập và phê duyệt. Candidate unit dùng cùng EnvironmentFile với API; việc thêm secret, quyền file và rollback unit phải được xác định/duyệt trước.

## FINAL RECOMMENDATION

**NOT READY FOR PRODUCTION.** Cần đóng các blocker restore/PITR, staging, secret Fernet, monitoring và kiểm thử Android/Brevo trước khi trình kế hoạch cuối cùng xin phê duyệt.
