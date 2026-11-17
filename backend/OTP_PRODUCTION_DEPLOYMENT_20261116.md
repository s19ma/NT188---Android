# Gmail OTP production deployment — 16/11/2026

## SUCCESS

- Người dùng xác nhận Phase F; API đã tạm dừng để ngăn đăng ký trong chuyển tiếp. Migration Alembic production `f31a7c4d2e01 → a42c7f3e9810 → b531d7e28a22 → c693a17e4d08` hoàn tất với `lock_timeout=5s`, `statement_timeout=60s`.
- Candidate SHA-256 `866A2DCAB0A7EF9054599DFA0408B67CB7C95BFC223F3746F9B4DF61E3A765A3` được xác minh local và trên VM trước triển khai.
- Sau migration, đối chiếu read-only fingerprint các cột dữ liệu cũ của 11 bảng với backup đã restore: 0 sai khác; có 4 tài khoản và cả 4 verified. Đối chiếu loại trừ các cột mới được migration thêm và bảng Alembic.
- Đã triển khai candidate 17 file, Fernet key production và SMTP cấu hình qua SSH stdin. Key SMTP là key local hiện có, không cấp mới/đổi/thu hồi. Cấu hình unrelated DB/JWT được kiểm tra không đổi; `.env` mode 0600. Hai process API/worker thực tế nhận cùng Fernet key và SMTP mode.
- API, Caddy, worker và queue-check timer active. Queue rỗng; kiểm tra queue thủ công bằng systemd `Result=success`, exit 0. Timer ghi cảnh báo vào journal, không có kênh chủ động.
- HTTPS health trả 200. OpenAPI có register/login/me, email verification và forgot/reset. Gửi payload thiếu trường đến register, verify và reset trả 422; login thiếu credential 422, `/users/me` không token 401. Đây là kiểm tra định tuyến/validation an toàn, không chứng minh login, JWT hoặc gửi email thành công.
- Backup database mã hóa `C:\Users\HP\AppData\Local\EnglishThroughVideo\production-backups\english-video-20261116T072118Z.pgdump.fernet`, SHA-256 `DEC595AA3F860F191802D56870C9FD2B49C7038DE585866B6D07808D75520892`; code/config archive SHA-256 `324E02B74EBFCDDBEF29A4281CD08D5E5B4E2CF04DA73644939158F19BD23115`. Restore lại vào PostgreSQL local được sử dụng để đối chiếu; container tạm đã dừng.

## Production Gmail smoke test

- Sau khi được người dùng cho phép riêng, đã tạo tài khoản test `vietbactqd@gmail.com` mới, gửi hai OTP thật và được người dùng cung cấp mã nhận được. Không ghi OTP, mật khẩu hoặc token vào báo cáo.
- Register 201; email verification 200; login 200; authenticated `/users/me` 200; reset request 200; reset confirm 200; mật khẩu cũ bị từ chối 401; login bằng mật khẩu mới 200; `/users/me` 200. Worker ghi nhận 2 job `sent`; queue check pass.
- Mật khẩu tài khoản test được sinh ngẫu nhiên và lưu tại máy local bằng DPAPI, không hiển thị. Người dùng có thể sử dụng luồng quên mật khẩu để tự đặt mật khẩu mong muốn.

## WARNING

- Brevo sender/domain/quota chưa xác minh độc lập trong Console dù hai email kiểm thử thực tế đã đến hộp thư. SMTP key từng lộ và giữ nguyên theo yêu cầu.
- Backup phụ thuộc profile Windows/DPAPI; user đã chấp nhận rủi ro này. Khôi phục production có thể làm mất các thay đổi sau snapshot và cần phê duyệt riêng. Không tự downgrade.
- Không có thông báo queue chủ động; lỗi queue ghi journal. `uncertain` không tự gửi lại. RAM VM hạn chế và không swap; cần giám sát.
- Chưa thử đăng nhập bằng mật khẩu thực của các tài khoản cũ; JWT authenticated đã được kiểm tra bằng tài khoản thử mới. Chưa đối chiếu owner/grant do restore thử dùng `--no-owner --no-privileges`.

## NOT EXECUTED

- Không Neon branch test, Azure staging, thay SMTP key, rollback/downgrade hay restore đè production.
