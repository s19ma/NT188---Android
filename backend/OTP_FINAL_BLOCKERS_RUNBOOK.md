# Gmail OTP: blockers và runbook trước triển khai

Ngày 16/11/2026. **CHƯA SẴN SÀNG TRIỂN KHAI.** Tài liệu này thay thế thứ tự lệnh trong `PRODUCTION_DEPLOYMENT_OTP_PLAN.md`: các file migration mới phải có mặt trước khi gọi Alembic. Không chạy các bước production dưới đây khi chưa được phê duyệt riêng.

## Xác nhận và điều kiện dừng

- API production hiện cấu hình database `english_video_db`, direct endpoint `ep-icy-lab-a16xdltv.ap-southeast-1.aws.neon.tech`; revision read-only `f31a7c4d2e01`, PostgreSQL 18.7, 4 tài khoản tại thời điểm kiểm tra. Chưa biết Neon project ID, branch ID, plan hoặc retention. Không suy ra project ID từ endpoint.
- Không dùng thao tác **restore in-place** trên branch production để tạo môi trường thử. Neon mô tả thao tác restore branch có thể chuyển các kết nối hiện tại sang trạng thái được khôi phục. Đề xuất tạo branch mới từ thời điểm được chọn hoặc restore snapshot vào branch mới, xác minh tính năng, chi phí và đích trong Console. Đây là bản sao logic độc lập, vẫn thuộc cùng project nếu dùng branch và không phải backup ngoài project. Chỉ tạo sau khi người dùng phê duyệt riêng nguồn, đích, thời điểm và chi phí.
- Trước khi ghi vào bản sao, đối chiếu project ID, branch ID, database name, endpoint, tài khoản kết nối và revision; bảo đảm endpoint đích khác production. Giới hạn truy cập bản sao vì chứa dữ liệu người dùng thật; không đưa vào log, chat hoặc môi trường public. Chạy backend staging với email mock, tắt tác vụ phụ và mọi tích hợp có thể ghi ra ngoài.
- Trên restore: lưu tổng hợp số tài khoản và các thống kê cần thiết trước/sau trong cùng bản sao, kiểm tra schema và một tài khoản cũ với thông tin thử hợp lệ do chủ tài khoản cung cấp. Đặt `lock_timeout` và `statement_timeout` được thống nhất, quan sát chờ lock và thời gian từng bước, thử trường hợp lock bị giữ; số đo trên bản sao không bảo đảm giống tải production. Không ghi password, token hoặc email người dùng vào báo cáo.
- Azure CLI/đăng nhập subscription chưa sẵn có. Kiểm thử staging độc lập cần VM/container Linux riêng, database staging riêng, endpoint và secret riêng; host production chỉ được kiểm tra read-only. VM hiện có khoảng 836 MiB RAM và không swap, không đủ bằng chứng để chạy thêm staging trên cùng máy một cách an toàn.
- Candidate `deploy/email-otp-readiness-candidate.tar` SHA-256 `866A2DCAB0A7EF9054599DFA0408B67CB7C95BFC223F3746F9B4DF61E3A765A3`; 17 file đều khớp source và không có `.env`. `pip check` local và venv production pass; cả 43 phiên bản pin trong requirements khớp venv production. Vẫn phải thử candidate trên Linux staging.

## Staging và kiểm tra vận hành

1. Trên Linux staging độc lập, cài candidate, dependencies đã pin và schema staging; dùng cổng nội bộ khác production, cấu hình `APP_ENVIRONMENT=development`, `EMAIL_DELIVERY_MODE=mock` và vô hiệu hóa tích hợp bên ngoài. Không dùng connection string production.
2. Tạo Fernet key staging ngẫu nhiên trong secret store được bảo vệ; API và worker nhận **cùng** key staging, tách khỏi JWT/SMTP và khỏi key production. Không ghi key vào lệnh, process arguments, log, candidate hoặc APK. Các template riêng trong `deploy/staging/` dùng user, working directory, EnvironmentFile và cổng staging riêng; chưa cài hay xác minh bằng systemd trên Linux. Kiểm tra lại path, quyền và cấu hình trước khi sử dụng. Các template này không có trong candidate production đã chốt checksum.
3. Xác minh quyền EnvironmentFile, service tự khởi động lại, start/stop/recovery worker, xử lý queue, hết hạn, key sai và trạng thái uncertain. Cài lịch giám sát `python -m scripts.email_outbox_status --check`, báo lỗi kết nối DB, worker inactive, pending/sending quá ngưỡng, failed và uncertain vào kênh vận hành. Công cụ chỉ có exit code, chưa tự gửi cảnh báo. `uncertain`/`failed` được đếm tích lũy, cần quy trình ghi nhận và ngưỡng/retention trước khi bật cảnh báo lâu dài; không tự gửi lại uncertain.
4. Test Android register/verify/login/forgot/reset trên staging bằng phương án OTP giả lập được kiểm soát. Không gửi email thật khi chưa có phê duyệt. Test Brevo end-to-end và headers chỉ sau khi có phép gửi riêng.

## Trình tự production dự kiến — KHÔNG THỰC THI

Điều kiện: restore/PITR và migration trên bản sao đã diễn tập; staging, Android, Brevo, giám sát, recovery và dependency pass; đã xác minh đúng máy/project; migration và kế hoạch secret đã được phê duyệt riêng; có người trực theo dõi và phương án dừng.

1. Kiểm tra checksum candidate ngay tại nơi staging file, manifest không có đường dẫn tuyệt đối/`..`, revision production vẫn là `f31a7c4d2e01`, tình trạng API/DB và transaction dài. Xác nhận restore point và khả năng phục hồi thực tế. Nếu sai bất kỳ điều kiện nào: dừng.
2. Sao lưu an toàn các file code, unit và cấu hình liên quan, ghi lại những file chưa tồn tại và quyền/owner; không đưa secret vào archive hoặc log. Kiểm tra khả năng khôi phục code. Chuẩn bị secret production theo phương thức được duyệt, giữ SMTP key hiện tại; API và worker dùng cùng Fernet key production riêng với staging/JWT/SMTP. Không cài key hoặc sửa production env khi chưa có phép.
3. Cài **chỉ ba file migration mới** vào đường dẫn Alembic của deployment, hoặc chạy Alembic từ candidate đã kiểm nghiệm có đầy đủ chuỗi migration và cấu hình tương thích production. Xác nhận `alembic history` nhìn thấy đúng chain. Thiết lập lock/statement timeout đã thử trên restore, chạy upgrade đến `c693a17e4d08`, kiểm tra revision. Nếu timeout/lỗi: dừng, xác định trạng thái transaction/revision và forward-fix; không tiếp tục cài API theo giả định.
4. Triển khai các file API đã kiểm tra; khởi động lại API theo cửa sổ được duyệt và kiểm tra health, login tài khoản cũ, khả năng truy cập DB và log đã lọc. Chỉ sau schema sẵn sàng mới chạy code API mới. Nếu lỗi: dừng worker nếu đã chạy, khôi phục file/unit code cũ và xác nhận API cũ tương thích schema mở rộng; không chạy downgrade phá dữ liệu.
5. Cài unit worker và secret configuration đã duyệt, xác minh user/path/quyền, `daemon-reload`, bật worker, xác nhận worker và monitoring active; theo dõi pending/failed/uncertain và thời gian chờ. Kiểm tra authenticated smoke test bằng tài khoản test. Không gửi email thật trừ khi được phê duyệt riêng.
6. Nếu worker hỏng, giữ queue, sửa key/config và kiểm tra trước thời hạn OTP. Với `uncertain`, không retry tự động: xác minh theo quy trình hỗ trợ và yêu cầu người dùng lấy mã mới khi thích hợp. Khi key sai, job được giữ pending nhưng vẫn có thể hết hạn và bị xóa ciphertext theo logic hết hạn.
7. Nếu lỗi schema hoặc dữ liệu, ưu tiên forward-fix sau đánh giá. Không coi Alembic downgrade là rollback an toàn; phục hồi database chỉ theo runbook đã diễn tập và phê duyệt, có tính đến dữ liệu phát sinh sau restore point.

## Kết quả chưa thực hiện

Chưa tạo restore, chạy migration trên restore, tạo staging Azure, triển khai/cấu hình/restart production, thay đổi SMTP key hoặc gửi email thật. Chưa có thiết bị Android qua ADB. Neon Console và Brevo Console chưa được xác thực trong lượt này.
