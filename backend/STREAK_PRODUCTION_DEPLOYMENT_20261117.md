# Streak production deployment — 17/11/2026 (giờ Việt Nam)

## SUCCESS
- Revision Neon `d4e9b137c802 → e8a72c14d931`; migration chạy với lock_timeout 5s, statement_timeout 60s. Không downgrade.
- Candidate SHA-256 `65C3A2A2A082F591B3845DE8FCDBCC0AB74FD1671433805F29819EFD93ED7500`; 5 file trên server khớp hash candidate. API restart có kiểm soát; API, Caddy, email worker và queue timer active; HTTPS health 200.
- Backup PostgreSQL mã hóa `english-video-20261117T014853Z.pgdump.fernet`, SHA-256 `CFAD112C8FB4E16FAAACD5CEC9564EF8518C8E589A73AEB7FF3D3B7DB2971887`, được giải mã và restore PostgreSQL 18 độc lập. Migration diễn tập trên restore thành công; số dòng 14 bảng cũ không đổi.
- Backup code/config `azure-code-config-20261117T014846Z.tar.gz.fernet`, SHA-256 `B7F051FF98F2AFA186286F0E4C5FE3A0FA754577D1BACC57B402246667D5E3C1`, giải mã được, các file rollback có mặt. Backup nằm trong thư mục profile local được bảo vệ DPAPI.
- Sau triển khai: 5 users, 14 từ đã lưu, 2 learning days; số lượng không đổi so với backup. Login, /users/me, /streak, overview và due queue của tài khoản test trả 200.
- Android debug APK SHA-256 `4452DC6BB4FE4196F798C93180D0BA66BAA2E36AA63B74CC024AFB25F76040E7`, build thành công, cài cập nhật giữ dữ liệu, checksum trên thiết bị khớp, mở được Home.
- PostgreSQL test: 35 tests pass; gồm giới hạn 30, Lặp lại, idempotency, concurrency và lịch; migration rehearsal trên bản restore thành công.

## WARNING / NOT EXECUTED
- Không gửi review thật, không thay đổi tiến độ hoặc lịch của tài khoản test production, nên chưa xác nhận UI end-to-end cho hoàn thành mục tiêu/đánh giá Lặp lại trên production.
- APK ký debug, chưa phát hành bản release. Tài khoản dùng APK cũ có thể không hiển thị đúng thông báo khi phải chờ thẻ Lặp lại.
- Dữ liệu streak trước deployment giữ nguyên, không tính lại lịch sử cũ. Mục tiêu ngày cố định khi ghi review đầu tiên, tối đa 30 thẻ; thẻ thêm/đến hạn sau đó chờ ngày tiếp theo.
- Backup phụ thuộc Windows DPAPI; không gửi email, không thay SMTP/Fernet, worker, Azure Blob hay cấu hình. Không tự restore đè production.
