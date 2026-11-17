# Flashcard — kiểm thử cuối và kế hoạch production

Ngày 16/11/2026. **Chưa triển khai production.** Cần quyết định cách xử lý việc mở lại sau process kill không khôi phục nguyên phiên trước khi xác nhận kế hoạch triển khai.

## SUCCESS

- Neon production được đọc với transaction read-only: revision `c693a17e4d08`, 5 tài khoản. Không chạy migration production.
- Backup PostgreSQL 18 custom qua direct connection được mã hóa DPAPI/Fernet: `C:\Users\HP\AppData\Local\EnglishThroughVideo\production-backups\english-video-20261116T112118Z.pgdump.fernet`, SHA-256 `98F92129297EC431B4732AB371D79C3D70F499B492E895A6549D934BB32B2A89`. Backup code/config Azure được mã hóa: `azure-code-config-20261116T112510Z.tar.gz.fernet`, SHA-256 `1EFC81076CFFCDDC5103607F46375E1441F6CEB8DEDEACA78A8DBFCA3CE8842D`. Có chứa dữ liệu/secret, thư mục ACL giới hạn và key phụ thuộc Windows DPAPI.
- Restore vào PostgreSQL 18 cục bộ, endpoint loopback, tmpfs; `pg_restore --no-owner --no-privileges`. Đối chiếu 14 bảng, dữ liệu, metadata cột, index, revision và 5 tài khoản: khớp. Bốn CHECK constraint biểu diễn khác nhau nhưng đã đối chiếu các biểu thức và mảng hằng tương đương. Owner/grant không nằm trong kết quả đối chiếu này.
- Migration trên restore `c693a17e4d08 → d4e9b137c802` thành công sau 0,78 giây, 13 bảng cũ fingerprint không đổi. Bảng mới và index primary key tồn tại; kiểm tra catalog thấy 8 constraints. Giữ khóa users, đặt `lock_timeout=2s`: migration thất bại theo dự kiến sau 2,83 giây, revision/dữ liệu giữ nguyên. Thời gian local không dự báo lock/downtime trên Neon.
- **22 test pass, 0 fail**, một cảnh báo Starlette/httpx; PostgreSQL test độc lập. Bao gồm 0/5/30/31/50/100 thẻ, future/NULL/thứ tự, user isolation, review sớm client cũ, request ID sai/trùng/khác payload, concurrent cùng/khác ID, rollback, snapshot replay, JWT, vocabulary list/save/delete/status và progress GET/PUT. Kiểm thử health và flashcard HTTP qua TestClient.
- Emulator chạy app ID thử nghiệm riêng, chỉ kết nối `https://127.0.0.1:18443` qua adb reverse tới FastAPI + Docker PostgreSQL test. TLS certificate riêng chỉ có trong bản sao test; email delivery disabled, không dùng production hay gửi mail thật. Tài khoản/test data giả có 31 thẻ due và 2 future: API trả 30 và không có 2 thẻ future; màn hình hiển thị 31 due, phiên 1/30; lật thẻ hiển thị nghĩa.
- Review rồi xoay khi response bị trì hoãn: UI sang phiên 2/30, DB `review_count=1`. Giả lập lỗi response HTTP 500 sau commit rồi retry cùng rating: UI tiếp tục sang phiên 3/30, DB vẫn `review_count=1` và một request record. Đây là mô phỏng lỗi sau commit, không phải thử mọi kiểu mất mạng vật lý.
- Emulator hiển thị toast ngày ôn và thời gian theo timezone thiết bị sau review. Nhãn tĩnh `1 ngày`/`3 ngày` ở nút Khó/Tốt đã đổi thành `Theo lịch` cho đúng SM-2; null phonetic/context không còn hiện chữ `null`. APK debug build pass.
- Candidate `deploy/flashcard-idempotency-candidate.tar` SHA-256 `69878528D6270346E7E6571CCE44406FD463E665D5A5A2620CAA860CA5B751F2`; 5 file khớp source. Diff với code production chỉ gồm thay đổi flashcard/schema/import liên quan; không thay source OTP/SMTP/worker. Test API HTTPS local health 200.

## WARNING / BLOCKED

- Sau Home → `am kill` → mở lại app qua launcher, ứng dụng quay về Home thay vì khôi phục nguyên phiên/tiến độ cũ. Review đã commit vẫn có đúng một bản ghi trong DB. Chưa chứng minh phục hồi phiên/pending request khi process chết đột ngột ở mọi thời điểm; cần xác nhận yêu cầu và xử lý trước khi coi lifecycle hoàn chỉnh.
- Client cũ không có `request_id` không có bảo đảm idempotency và giữ khả năng review sớm. Client mới yêu cầu backend quảng báo capability; APK debug mặc định trỏ production hiện tại nên sẽ từ chối phiên ôn tới khi backend mới triển khai.
- Bảng request snapshot tăng theo lượt review, chưa có chính sách retention. Xóa record có thể làm retry quá cũ mất tính idempotent. Backup phụ thuộc Windows DPAPI; người dùng từng chấp nhận giới hạn này cho tác vụ OTP, nhưng vẫn là rủi ro recovery.
- Không test mọi kết hợp timezone, nhiều thiết bị cùng user, network partition vật lý, hay tải cao. UI toast đã quan sát trên emulator, không phải kiểm thử thiết bị vật lý. Kiểm tra mail OTP thực tế sau thay đổi flashcard chưa thực hiện vì không được gửi email thật.

## NOT EXECUTED

- Không deploy hoặc restart Azure, không chạy migration/ghi dữ liệu Neon production, không thay Gmail OTP, SMTP/Fernet secret, email worker hoặc Azure Blob. FastAPI local, emulator và container restore đã dừng sau test.

## Kế hoạch sau khi xử lý blocker và được duyệt riêng

1. Chốt xử lý process recreation; chạy lại emulator và regression liên quan. Kiểm tra backup mới, revision `c693a17e4d08`, checksum, transaction dài và RAM; xác minh quyền/owner/grant cần phục hồi.
2. Chuyển candidate vào vùng staging file an toàn trên VM, không thay secret. Sao lưu code và config; cài migration file trước, xác nhận Alembic chain, chạy `d4e9b137c802` với lock/statement timeout phù hợp sau phê duyệt.
3. Kiểm tra revision, schema, số liệu và lịch cũ; deploy 5 file backend, restart API có kiểm soát, giữ worker OTP đang hoạt động. Theo dõi API/Caddy/worker, DB locks, 5xx và queue OTP; phát hành APK sau backend.
4. Smoke test health, JWT và flashcard trên tài khoản được phép. Nếu code lỗi, khôi phục code backup tương thích schema mở rộng; không tự downgrade vì sẽ xóa kết quả idempotency. Ưu tiên forward-fix; phục hồi DB chỉ theo phê duyệt riêng.
