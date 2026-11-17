# Chuẩn bị Gmail OTP production – báo cáo local/test

Ngày 16/11/2026. Đây là kết quả chuẩn bị, không phải phê duyệt triển khai.

## SUCCESS

- Đối chiếu qua SSH/SELECT chỉ đọc: service production đang active; Alembic revision `f31a7c4d2e01`; PostgreSQL server_version_num `180007`; cột `users.email_verified` chưa tồn tại. Source production auth/users/config khác local; code OTP local chưa deploy. Git status/branch không thể xác định vì workspace không có Git repository.
- Xem SQL offline chain `f31a7c4d2e01 → a42c7f3e9810 → b531d7e28a22 → c693a17e4d08`: thêm cột, hai bảng và index; không có DROP trong upgrade. Bản `a42...` thêm `email_verified DEFAULT true` cho tài khoản hiện có. SQL chỉ được sinh offline, không chạy trên Neon.
- Docker PostgreSQL 16 test tại `127.0.0.1:5433`, database `english_video_test`: đã chạy upgrade `b531d7e28a22 → c693a17e4d08`. Đây là test database dùng schema fixture tối thiểu, **không phải bản sao Neon**. Các revision `f31... → b531...` đã được thử upgrade/downgrade/upgrade trong lượt trước trên fixture này.
- Thêm transactional outbox: OTP hash và job được ghi trong cùng transaction; job chứa payload mã hóa Fernet, không lưu OTP plaintext. Worker claim bằng `FOR UPDATE SKIP LOCKED`, commit claim trước SMTP; kết quả ambiguous/worker chết được đánh dấu `uncertain`, không tự retry. Chỉ lỗi trước bước gửi có backoff, tối đa 3 lần và không vượt thời hạn OTP. Payload ciphertext được xóa khi job kết thúc/ambiguous.
- Chạy `pytest` trên Docker test với `EMAIL_DELIVERY_MODE=mock`, khóa mã hóa test tạm thời: **29 passed**, 1 cảnh báo dependency Starlette/httpx. Gồm rollback transaction, commit lỗi, mã hóa, hai worker tranh cùng job, rate limit hai resend đồng thời, retry trước SMTP, ambiguous timeout mô phỏng, claim bỏ dở, register/verify/reset/login. Test tài khoản verified được tạo trong schema đã migrate; chưa chứng minh trên bản sao tài khoản trước migration.
- DMARC DNS của domain có record `p=none`; hai tên `brevo1._domainkey` và `brevo2._domainkey` có CNAME. Đây không phải bằng chứng xác thực domain/end-to-end DKIM/SPF/DMARC pass.

## WARNING

- SMTP không hỗ trợ exactly-once: lỗi/timeout sau khi bắt đầu `send_message`, hoặc worker chết sau khi SMTP chấp nhận nhưng trước khi lưu trạng thái, không thể xác định đã gửi. Job chuyển uncertain và không tự gửi lại. Cần quy trình vận hành/quan sát và hỗ trợ người dùng yêu cầu mã mới.
- Có khoảng thời gian giữa kiểm tra OTP còn hiệu lực và SMTP; resend đồng thời có thể làm mã trong email đang gửi trở thành mã cũ. Cần test tải/concurrency sâu hơn và quyết định chính sách sản phẩm.
- Key mã hóa outbox phải là Fernet key ngẫu nhiên, riêng với JWT/SMTP, đặt trong secret store/EnvironmentFile quyền hạn chế cho cả API và worker. Mất hoặc thay key khi còn job pending sẽ làm job không giải mã được; cần quy trình rotate key, theo dõi và xử lý pending. Không để key trong Git, APK, log hay báo cáo.
- OTP hết hạn từ lúc enqueue, không phải lúc gửi. Worker dừng hoặc backlog quá lâu có thể làm job hết hạn; cần monitoring trạng thái, độ trễ và cảnh báo worker. API báo yêu cầu được chấp nhận, không bảo đảm email đã tới inbox.
- Existing helper `scripts/gmail_test_server.py` được viết cho luồng gửi đồng bộ và revision cũ; chưa cập nhật để test outbox mới. Không dùng nó để kết luận outbox đã gửi email thật.
- Migration thêm cột `NOT NULL DEFAULT` trên `users` và `password_reset_otps`, cần khóa bảng; `CREATE INDEX` chạy trong transaction. PostgreSQL 18 có thể tối ưu default phù hợp, nhưng thời gian chờ lock, kích thước bảng và downtime thực tế chưa đo trên bản sao độc lập. Kiểm tra transaction dài, lên lịch và giới hạn lock timeout trước khi quyết định.
- Unit test nhiều nhánh dùng mock; timeout kiểm thử là giả lập, chưa có SMTP integration test cho outbox mới. Độ bền sau mất nguồn, retry thật và nhiều worker dài hạn chưa được kiểm tra.
- SMTP key local vẫn có cùng hậu tố với key đã lộ; đây chỉ là phép kiểm tra dấu hiệu, chưa chứng minh key mới. Cần thu hồi/rotate và cấu hình secret mới ngoài chat.
- Một số trạng thái từ giao diện Android đang nói mã đã gửi, trong khi API giờ chỉ xếp hàng. Cần rà soát/điều chỉnh thông báo và test end-to-end trước production.

## BLOCKED

- Chưa có quyền/bằng chứng xác thực Neon plan/PITR, restore point và khôi phục thử vào database độc lập; không thể kết luận backup phục hồi được.
- Chưa có bản sao database độc lập nên chưa kiểm thử migration trên bản sao production, chưa đo lock/downtime hoặc xác minh dữ liệu thật sau restore.
- Không có xác nhận Brevo domain authentication, DKIM 1/2 và SMTP activation/quota từ tài khoản; không có email headers mới. SPF/DKIM/DMARC pass chưa xác minh.
- Key SMTP chưa được xác minh đã rotate; chưa chuẩn bị secret production, chưa tạo hoặc kiểm thử systemd worker production, monitoring, quyền file hoặc phương án restart API/worker phối hợp.
- Chưa có test đủ cho network partition PostgreSQL sau claim, xác nhận 3 lần backoff, retry thất bại liên tục, key rotation và vận hành job uncertain; chưa kiểm tra Android sau thay đổi bất đồng bộ.

## NOT EXECUTED

- Không migration/DDL/DML trên Neon production, không deploy hoặc restart Azure, không sửa production secrets, không gửi email production.
- Không restore/xóa dữ liệu, không cấp mới hoặc thu hồi key Brevo, không thay đổi Azure Blob/network. Không commit/push.

## Tệp local thay đổi trong lượt này

- `app/models/email_outbox.py`, `app/models/__init__.py`, `app/core/config.py`.
- `app/services/email_outbox.py`, `app/services/email_sender.py`, `app/api/v1/endpoints/auth.py`.
- `scripts/email_outbox_worker.py`, `migrations/versions/c693a17e4d08_email_outbox.py`.
- `tests/test_email_outbox_docker.py`, `tests/test_docker_auth_integration.py` và báo cáo này.

## Kế hoạch trước khi xin phê duyệt

1. Xác minh PITR và phục hồi vào database độc lập; kiểm tra dữ liệu, quyền, revision; chạy toàn bộ chain upgrade và đo lock trên bản sao. Không coi downgrade xóa bảng/cột là rollback mặc định.
2. Rotate SMTP key an toàn; cấu hình và bảo vệ `EMAIL_OUTBOX_ENCRYPTION_KEY` riêng cho API/worker trên staging, mô phỏng mất/rotate key. Xác minh Brevo sender/domain và log/header sau khi được phép gửi test.
3. Hoàn thiện kiểm thử crash thật, race resend, retry/backoff, worker lifecycle, retention/cleanup và monitoring; cập nhật Android theo ý nghĩa queued; test đăng nhập tài khoản có sẵn trên bản sao.
4. Viết runbook triển khai có backup code/secret configuration, thứ tự migration → API → worker, health/smoke test và forward-fix. Nếu code lỗi sau migration, rollback code tương thích schema mới; không tự downgrade schema có dữ liệu mới. Chuẩn bị bước khôi phục từ backup/PITR đã diễn tập nếu cần.
5. Chỉ sau khi các điều kiện trên được chứng minh, trình kế hoạch cụ thể để người dùng phê duyệt riêng. Hiện chưa nên deploy.
