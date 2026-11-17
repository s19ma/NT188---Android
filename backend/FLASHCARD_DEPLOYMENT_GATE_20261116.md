# Flashcard production preflight — 16/11/2026

**Chưa deploy; chờ phê duyệt riêng.** Người dùng chọn chặn review sớm cho cả client cũ, vì vậy candidate mới có checksum khác candidate ban đầu.

## SUCCESS

- Production direct endpoint `ep-icy-lab-a16xdltv.ap-southeast-1.aws.neon.tech`, database `english_video_db`, PostgreSQL 18.7, revision `c693a17e4d08`; 5 tài khoản và 3 saved words tại lần kiểm tra. Project ID `autumn-sound-55302844`, branch ID `br-gentle-shape-a166ho81` là thông tin đã được người dùng xác nhận; chưa có quyền Console/API để xác minh độc lập. Không thấy transaction quá 60 giây trong phạm vi role quan sát được.
- API, Caddy, email worker và queue timer active; HTTPS `/health` và `/openapi.json` 200; queue email `sent=2`, check exit 0. SMTP và Fernet hiện diện trong EnvironmentFile mode 0600; không đọc/in giá trị ra báo cáo. VM còn khoảng 25 GB disk, khoảng 430 MiB RAM available, không swap. `pip check` production pass.
- Database backup mới qua direct connection, read-only custom pg_dump, mã hóa trước khi ghi: `C:\Users\HP\AppData\Local\EnglishThroughVideo\production-backups\english-video-20261116T121716Z.pgdump.fernet`; SHA-256 `02AB81445B1C2B2E316203FBA4ED10B0D318C7A688D5A4A814157A5D3C589A6C`. Backup code/config mã hóa `azure-code-config-20261116T121709Z.tar.gz.fernet`, SHA-256 `A84F1B749FDAB5E52B549E1D2943A5180DBC2F25F097AA35AD6402124A2F48AF`; giải mã và đọc 76 file thành công.
- Restore backup mới vào PostgreSQL 18 local độc lập `otp_restore`: 14 bảng, data fingerprints, metadata cột, index, revision và 5 user khớp tại thời điểm so sánh. Bốn CHECK expressions khác cách biểu diễn ép kiểu đã được so sánh tương đương. Restore dùng `--no-owner --no-privileges`.
- Diễn tập migration trên restore `c693a17e4d08 → d4e9b137c802`: tạo bảng và primary key, 13 bảng dữ liệu cũ giữ fingerprint; lock test 2 giây thất bại có rollback, sau đó upgrade thành công trong khoảng 0,75 giây. Đây không phải dự báo thời gian hoặc lock production.
- Code API production hiện tại trích từ backup mã hóa đã chạy trên restore sau migration: health, model queries, synthetic login, `/users/me`, flashcard queue/overview pass. Không gửi email thật.
- Candidate cũ được xác minh đúng checksum yêu cầu `69878528D6270346E7E6571CCE44406FD463E665D5A5A2620CAA860CA5B751F2`. Sau lựa chọn chặn review sớm cho tất cả client, candidate **mới** `deploy/flashcard-due-strict-candidate.tar` SHA-256 `B52EBDAE32CAE84235DAF83B3AD3FDD5E9D7B252763AE5DDD276117FDA23A65D`, 5 file khớp source. Candidate cũ được giữ nguyên, không dùng để triển khai theo lựa chọn mới.
- **23 tests pass, 0 fail** trên PostgreSQL Docker test, bao gồm client cũ review due và bị 409 khi chưa due, retry/concurrency/rollback, JWT, vocabulary/progress. Một cảnh báo Starlette/httpx.
- APK debug SHA-256 `CE8AA11ADC1652BC338DFCC7E1E8CA066F45C6598DFBB18252A8E699DC75B9C8`, URL production, chữ ký Android Debug; kiểm tra các byte ZIP giải nén không thấy sáu secret được cấu hình hoặc marker test. Đây là kiểm tra có giới hạn, không chứng minh tuyệt đối APK không có secret. Các test process death/session theo user được ghi tại `FLASHCARD_PROCESS_DEATH_READINESS.md`.
- DB role cho biết có quyền schema CREATE, REFERENCES trên users/user_vocabulary và UPDATE alembic_version. Điều này chưa chứng minh mọi quyền/owner/grant trong phương án restore.

## WARNING

- Client cũ không gửi `request_id` vẫn có thể review thẻ đến hạn nhưng không có idempotency; từ nay sẽ nhận 409 khi review sớm, có thể hiển thị thông báo lỗi chưa phù hợp. Đây là thay đổi hành vi đã được người dùng chọn.
- Session recovery đã thử SIGKILL/emulator, không phải mọi kiểu low-memory reclaim/OEM/mất nguồn. Snapshot phụ thuộc Android Keystore; server vẫn giữ review đã commit. Queue email hiện chỉ cảnh báo journal, không có kênh chủ động.
- Backup phụ thuộc profile Windows/DPAPI và chưa diễn tập owner/grant; có thể không khôi phục được nếu mất profile. Người dùng đã chấp nhận giới hạn này trong task production trước; backup hiện tại phản ánh thời điểm snapshot và không bảo vệ dữ liệu phát sinh sau đó.
- APK nêu trên là debug-signed, không phải release-signed; chỉ phù hợp phân phối thử có kiểm soát. Không có bằng chứng phát hành rộng hoặc kiểm thử trên thiết bị vật lý.
- Bảng idempotency tăng theo lượt review, chưa có retention policy. Không tự xóa record hoặc downgrade bảng; client mới cần backend báo capability trước khi review.

## BLOCKED / NOT EXECUTED

- Chưa có phê duyệt riêng cho migration/deploy/restart; chưa thực hiện bất kỳ thao tác production nào ngoài đọc và pg_dump. Không sửa SMTP/Fernet/worker/Blob, không gửi email thật.
- Chưa có tài khoản flashcard production được chỉ định cho smoke test ghi dữ liệu, chưa phát hành APK release, chưa kiểm tra tất cả OEM/network partition.

## Phase F dự kiến — chỉ sau phê duyệt riêng

1. Chốt cửa sổ và đối tượng smoke test; kiểm tra lại hash **candidate mới**, backup/revision/transaction dài, RAM và service. Tạo/kiểm tra backup mới nếu dữ liệu đã thay đổi.
2. Chuyển candidate mới vào thư mục staging file riêng, xác minh checksum; giữ nguyên `.env` và secret. Sao lưu code/config hiện hành. Dừng API có kiểm soát để tránh ghi review trong khoảng chuyển tiếp; Caddy và email worker tiếp tục chạy. Toàn bộ API tạm gián đoạn và Caddy có thể trả lỗi; chưa có số đo downtime production.
3. Đưa riêng migration file vào thư mục Alembic, xác minh chain, chạy upgrade đến `d4e9b137c802` với đề xuất `lock_timeout=5s`, `statement_timeout=60s` sau khi xác nhận không có transaction cản trở. Dừng nếu timeout hoặc revision sai; không tự downgrade.
4. Kiểm tra revision, bảng, 5 tài khoản và lịch ôn cũ; triển khai 5 file candidate mới và start API. Không cài hoặc sửa email worker/Caddy, SMTP/Fernet key, OTP hay Blob.
5. Kiểm tra API/Caddy/email worker/timer, health/OpenAPI, queue email không bất thường, DB locks và API 5xx; smoke GET flashcard/JWT chỉ với tài khoản được phép. Review thật, tạo account hoặc gửi email thật cần phạm vi dữ liệu thử được phê duyệt riêng. Chỉ sau backend hoạt động mới cài APK debug để thử nội bộ.
6. Nếu lỗi code: giữ API/đường dẫn review an toàn, phục hồi code cũ từ backup và xác minh OTP/worker; giữ bảng idempotency, không tự downgrade. Nếu lỗi dữ liệu: dừng, đánh giá forward-fix; không restore đè database nếu chưa có phê duyệt riêng và đánh giá mất dữ liệu sau snapshot.
