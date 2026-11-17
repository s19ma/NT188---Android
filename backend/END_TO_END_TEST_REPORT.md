# End-to-end test report — 16/11/2026

## SUCCESS

- Production OpenAPI: 49 operations, giống local về method/path; 26 operations có request runtime (gồm login và 2 kiểm tra learner bị từ chối admin). Đây không phải 26 endpoint được kiểm thử toàn diện. Matrix ghi HTTP cụ thể.
- Android 16 thiết bị thật: đăng nhập, Home, 16 từ vựng, tiến độ, hồ sơ, flashcard 10 due, lật thẻ và mở lại phiên đã quan sát. API và 4 service API/Caddy/worker/timer active. APK debug build và cài update không xóa dữ liệu; checksum EA588E6BF766BA3B69D9E94C4A7331E37CCCAA24CB6EA4D13C32B3D6F22C6423 khớp thiết bị.
- PostgreSQL 18 Docker độc lập, loopback 5433, schema từ ORM; 37 pytest pass bao gồm flashcard/concurrency/idempotency, auth và regression schema; thêm 15 auth/outbox integration pass trên database test riêng với SMTP mock; thêm 1 test worker process riêng với mock SMTP pass. 53 lượt test pass, một cảnh báo thư viện Starlette/httpx. Không phải migration rehearsal.

## WARNING / BLOCKED

- API playback/subtitles trả 200; thử một video: SAS read-only hạn 1.800 giây, GET Range trả 206, HEAD không có SAS trả 409. Chưa chứng minh phát trên Android, tính riêng tư tổng quát hoặc đồng bộ phụ đề; Android player ghi progress khi pause, nên không mở trên production. Chưa kiểm tra đủ metadata, SAS expiry, blob privacy hoặc mọi filter.
- Không thử review production, lịch 1/6 ngày, retry trên máy thật, process death, network, rotation hay mọi màn hình. Kiểm thử concurrency và SM-2 giới hạn ở PostgreSQL local. OTP production, đăng ký/reset, email, admin mutation không chạy.
- Migration Alembic từ DB trống thất bại vì revision baseline giả định schema đã tồn tại; test này không phản ánh migration trên production có sẵn. Các sửa schema chỉ nằm local.
- Tài khoản test chứa dữ liệu tổng hợp; 32 lượt ôn hiển thị là số review_count mẫu, không phải thao tác người dùng thật.

## NOT EXECUTED

- Không thay Neon production, review, progress, OTP, SMTP/Fernet/JWT, worker, Blob, deploy hoặc restart production. Không gửi email. Chưa chạy Android end-to-end với backend Docker và chưa kiểm tra phân quyền admin tích cực.

