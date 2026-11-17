# Gmail OTP: preflight triển khai trực tiếp

Ngày 16/11/2026. **BLOCKED / chưa được phép chạy Phase F.** Không tạo Neon branch test hoặc Azure staging. Không chạy migration, deploy, restart hay sửa secret/service production. Không thay đổi SMTP key hoặc gửi email thật.

## SUCCESS

- SSH Azure qua host key đã biết tại IP `20.205.11.25`: `english-video-api`, Caddy active. HTTPS `/health` 200 healthy; `/openapi.json` 200.
- Production API direct endpoint là `ep-icy-lab-a16xdltv.ap-southeast-1.aws.neon.tech`, database `english_video_db`, PostgreSQL 18.7; kết nối kiểm tra có `default_transaction_read_only=on`. Revision `f31a7c4d2e01`, 4 tài khoản, không có transaction quá 60 giây trong phạm vi hiển thị tại lần kiểm tra cuối. Các thông số project/branch/plan/retention do người dùng cung cấp; chưa xác thực độc lập qua Neon Console/API.
- Database 8.560.640 bytes; ổ C còn khoảng 50 GB, D khoảng 217 GB tại preflight. Azure disk 25 GB trống; RAM 836 MiB, không swap. Dependency production: `pip check` pass và 43 phiên bản pin khớp requirements local.
- Candidate SHA-256 `866A2DCAB0A7EF9054599DFA0408B67CB7C95BFC223F3746F9B4DF61E3A765A3`; 17 file khớp source, không `.env`. Chain local `f31a7c4d2e01 → a42c7f3e9810 → b531d7e28a22 → c693a17e4d08` đầy đủ.
- `pg_dump` client 18 tạo archive custom từ direct endpoint, sử dụng snapshot repeatable-read chỉ đọc. Password cấp qua stdin, không truyền trong process arguments; ciphertext được ghi trực tiếp vào file, không lưu dump plaintext thông thường. Backup gồm schema và dữ liệu; roles toàn cluster không thuộc phạm vi pg_dump một database.
- Giải mã trong bộ nhớ, `pg_restore --list`, restore PostgreSQL 18 cục bộ thành công. Đích là container `english-video-otp-restore-20261116`, database `otp_restore`, port loopback 55432, data directory tmpfs; container đã dừng sau kiểm tra. Đối chiếu 12 bảng: count và aggregate row fingerprints bằng nhau, metadata các cột và định nghĩa index bằng nhau; revision trước migration bằng nhau và có 4 tài khoản. Bốn định nghĩa CHECK được PostgreSQL hiển thị với cú pháp ép kiểu khác; tất cả cho cùng kết quả trên mẫu giá trị hợp lệ, không hợp lệ và NULL, nhưng chưa chứng minh tương đương toàn diện. Restore dùng `--no-owner --no-privileges`; quyền và owner chưa đối chiếu.
- Trên restore: mô phỏng lock giữ bảng `users`, `lock_timeout=2s` dẫn đến thất bại như dự kiến; revision và dấu vân tay dữ liệu không đổi. Khi không giữ lock, migration hoàn tất sau khoảng 1,2 giây với `lock_timeout=5s`, `statement_timeout=60s`; revision `c693a17e4d08`, dấu vân tay dữ liệu cũ không đổi, 4 tài khoản được đánh dấu verified. Thời gian và kết quả khóa trên local không bảo đảm production giống vậy.
- Test code API production cũ đã sao lưu trên schema restore đã migrate: health/models, đăng ký giả, login và `/users/me` pass. Tài khoản giả chỉ được tạo trong restore cục bộ. Chưa kiểm tra login bằng mật khẩu của 4 tài khoản thật.
- Đã sao lưu code, migration, script, `.env`, cấu hình API systemd và Caddy từ Azure bằng SSH read-only; mã hóa trước khi ghi, giải mã và đọc archive thành công. Không sao lưu venv; các dependency pin được xác minh riêng.
- Fernet key production ngẫu nhiên đã chuẩn bị bằng DPAPI cho tài khoản Windows hiện tại, khác key staging. Chưa cài lên Azure. Local có SMTP key hiện tại, host/login/sender khớp thông tin Brevo do người dùng cung cấp; không in hay thay key. Production hiện chưa cấu hình SMTP hoặc Fernet.

## BACKUP REPORT

- Encrypted backup: `C:\Users\HP\AppData\Local\EnglishThroughVideo\production-backups\english-video-20261116T072118Z.pgdump.fernet`.
- Thời điểm tên file: 16/11/2026 07:21:18 UTC (14:21:18 GMT+7); đây là thời điểm ghi file sau snapshot.
- SHA-256 ciphertext: `DEC595AA3F860F191802D56870C9FD2B49C7038DE585866B6D07808D75520892`.
- Encrypted code/config: `C:\Users\HP\AppData\Local\EnglishThroughVideo\production-backups\azure-code-config-20261116T072419Z.tar.gz.fernet`; SHA-256 `324E02B74EBFCDDBEF29A4281CD08D5E5B4E2CF04DA73644939158F19BD23115`.
- Thư mục Windows có ACL chỉ cho tài khoản hiện tại, ngừng kế thừa; khóa backup được DPAPI bảo vệ theo user. Khôi phục phụ thuộc tài khoản/profile Windows này; mất profile/máy có thể làm backup không giải mã được. Chưa có bản sao ngoại tuyến hoặc kiểm thử khôi phục trên máy khác.

## WARNING

- SMTP key từng xuất hiện trong chat; được giữ nguyên theo chỉ dẫn, rủi ro chưa được xử lý.
- API cũ đăng ký không có OTP. Trong khoảng giữa schema upgrade và API mới, người dùng có thể tạo tài khoản bỏ qua xác minh nếu API cũ vẫn nhận đăng ký. Kế hoạch chuyển tiếp phải chặn đăng ký hoặc ngưng API có kiểm soát trước migration; việc thay đổi này chỉ làm sau phê duyệt.
- Docker tmpfs giới hạn vị trí dữ liệu restore, nhưng chưa xác minh chính sách swap/mã hóa của host Docker; không khẳng định tuyệt đối không có dấu vết plaintext ở tầng host. Không đưa dữ liệu thật vào log hoặc repo.
- Backup local phản ánh snapshot lúc tạo; dữ liệu phát sinh sau thời điểm đó sẽ mất nếu khôi phục lại. Không tự restore đè production.
- Giám sát queue hiện chỉ có lệnh kiểm tra/exit code, chưa tích hợp cảnh báo; uncertain không tự retry. SMTP, sender/domain/quota và giao email thật chưa được xác minh trong lượt này.

## BLOCKED

1. Chưa xác thực độc lập project ID `autumn-sound-55302844`, branch `br-gentle-shape-a166ho81`, plan Free và retention 6 giờ qua Neon Console/API. Host, database và revision đã xác minh qua production config và truy vấn đọc.
2. Ba migration files mới chưa nằm trong deployment Azure; chỉ có trong candidate local. Không đưa lên trước xác nhận vì đó là thay đổi trên Azure production.
3. SMTP và Fernet production, worker systemd và alerting chưa cài; chỉ chuẩn bị key cục bộ và unit/script. Phương thức chuyển secret, quyền file và giám sát cần được thống nhất trước khi thực thi.
4. Bốn CHECK constraint được biểu diễn khác sau restore; kiểm tra mẫu cho kết quả giống nhau nhưng còn cần xác nhận tính tương đương. Chưa đối chiếu owner/grant, chưa chứng minh tài khoản production cũ đăng nhập với mật khẩu thực; Android không có thiết bị trong lần kiểm tra trước. Chưa xác minh Brevo Console hoặc gửi mail thật.

## PHASE F — phương án chờ phê duyệt sau khi đóng blockers

1. Xác minh project/branch/retention Neon, backup hiện hành, restore khả dụng, hash candidate, sức khỏe, tài khoản và các transaction dài. Thống nhất cửa sổ, chặn đăng ký hoặc bảo trì API để tránh luồng cũ bỏ qua OTP.
2. Xác nhận có thể giải mã code/config và database backup, xác định owner/permissions cần khôi phục; rà soát và chốt lock/statement timeout theo quan sát và mức chấp nhận. Không coi số đo local là dự báo downtime.
3. Cài ba migration file từ candidate, xác thực Alembic chain và revision, sau đó chạy migration có timeout; nếu sai/lỗi dừng, kiểm tra trạng thái thực tế, không downgrade phá dữ liệu.
4. Cài candidate backend, cấu hình Fernet production và SMTP key hiện tại bằng cơ chế secret được duyệt không in key, cài worker và monitoring. API/worker dùng chung Fernet production, khác staging.
5. Restart API và start worker có kiểm soát; xác nhận API/Caddy/worker, revision, queue và health. Smoke test chỉ đọc hoặc dùng tài khoản được cho phép. Không tạo tài khoản hoặc gửi mail thật khi chưa có phép riêng.
6. Nếu code lỗi: dừng worker, khôi phục code/config tương thích schema mở rộng; nếu database lỗi đánh giá forward-fix, không tự downgrade hay restore đè. Restore production cần phê duyệt riêng vì có thể mất dữ liệu phát sinh sau snapshot.

## NOT EXECUTED

Không Neon branch test/staging Azure, production migration/DDL/DML, deploy, restart, thay production secret/service, DROP/TRUNCATE, email thật hoặc thay SMTP key. Không tạo tài khoản production. Container restore local đã dừng; không xóa backup mã hóa.
