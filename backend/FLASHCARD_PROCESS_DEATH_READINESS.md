# Flashcard process death — kiểm thử và readiness

Ngày 16/11/2026. Thay thế blocker process-recreation trong `FLASHCARD_FINAL_TEST_REPORT.md`; chưa triển khai production.

## SUCCESS

- Snapshot session được lưu riêng theo từng tài khoản bằng EncryptedSharedPreferences, gắn với UUID user lấy từ `/users/me`: session ID, thời gian tạo/cập nhật, tối đa 30 thẻ theo thứ tự, chỉ số thẻ, mặt thẻ, ID đã hoàn thành, tiến độ, request ID/card/rating và trạng thái kết quả chưa xác định. Snapshot không chứa JWT, mật khẩu hay OTP. Trước khi gửi review, snapshot request được ghi đồng bộ; lỗi ghi ngăn gửi.
- Home hỏi `Tiếp tục học` / `Bỏ phiên` / `Để sau`. Chỉ hiện sau khi xác minh UUID user với API. Khi tiếp tục, client đối chiếu các saved ID với API, kiểm tra capability idempotency và server clock, giữ thứ tự phiên và retry request chưa xác định bằng ID/payload cũ. Đánh giá mới vẫn do backend quyết định, không ghi đè lịch từ Android.
- Snapshot tự xóa sau thẻ cuối hoặc khi người dùng bỏ phiên; code kiểm tra session ID/user trước khi callback cũ ghi/xóa snapshot, tránh làm sống lại phiên đã bỏ hoặc xóa phiên khác. Force-stop không được dùng làm phép thử duy nhất cho process death.
- Android emulator + FastAPI HTTPS local + PostgreSQL Docker test riêng, email delivery disabled: xoay khi đang học giữ mặt sau; xoay trong request giữ tiến độ và một review. Trước thay đổi khóa lưu riêng theo user, thứ tự 30 ID trước/sau khôi phục SIGKILL có cùng SHA-256; với bản cuối, kiểm tra đổi hai tài khoản giữ đúng thứ tự 27 ID. Probe chỉ chạy ở bản sao app test.
- SIGKILL process **sau khi DB commit, trước HTTP response**: sau launcher, chọn Tiếp tục, request được retry, UI chuyển đúng tiến độ và DB giữ `review_count=1`, một request record. SIGKILL **trước commit** với test server trì hoãn: count trước kill 0, sau resume count 1 và một request record. Đây là SIGKILL có kiểm tra PID; không khẳng định đã mô phỏng đầy đủ system low-memory reclaim.
- `am kill` không thực sự dừng process trong một lần thử (PID không đổi), nên không tính là bằng chứng process death. Thử `force-stop` riêng và mở thủ công vẫn hiện lựa chọn tiếp tục; force-stop không đồng nghĩa system reclaim.
- Logout/login tài khoản test khác không hiện phiên cũ; tài khoản thứ hai tạo phiên riêng, login lại tài khoản thứ nhất vẫn thấy phiên gốc với fingerprint thứ tự 27 thẻ không đổi. Bỏ phiên xóa snapshot local, server giữ 31 từ và 4 review; mở lại không hiện prompt. Session một thẻ sau review hoàn thành không hiện prompt khi mở lại. File encrypted preferences không chứa plaintext email test, JWT prefix hoặc tên trường snapshot.
- PostgreSQL Docker regression: **22 pass, 0 fail**, một cảnh báo Starlette/httpx; gồm idempotency, concurrency, vocabulary/progress/JWT, UTC và due queue. Build APK debug pass.
- Migration backend `c693a17e4d08 → d4e9b137c802` đã diễn tập trên bản restore PostgreSQL 18 của backup read-only trước đó, dữ liệu cũ không đổi và lock timeout rollback đạt. Candidate backend SHA-256 `69878528D6270346E7E6571CCE44406FD463E665D5A5A2620CAA860CA5B751F2`, 5 file khớp source. APK debug SHA-256 `CE8AA11ADC1652BC338DFCC7E1E8CA066F45C6598DFBB18252A8E699DC75B9C8`.

## WARNING

- SIGKILL được chủ động gửi tới process test, không phải áp lực bộ nhớ thật; không chứng minh mọi hành vi OEM hoặc trường hợp mất nguồn đúng lúc ghi storage. Cần thử thiết bị vật lý trước phát hành rộng. Session snapshot phụ thuộc Android Keystore, nếu mất key hoặc xóa dữ liệu app thì không thể khôi phục local; review đã commit vẫn ở server.
- Reconciliation phụ thuộc authenticated API `/users/me/vocabulary` và HTTP Date; khi offline/server không cung cấp Date hoặc backend cũ không quảng báo capability, app không tự retry hay tự quyết định đã lưu. UUID snapshot được gắn với user do backend xác thực. Nhiều thiết bị và dữ liệu đổi đồng thời có thể dẫn đến 409 và thẻ bị loại khỏi phiên sau khi server báo chưa đến hạn.
- Client cũ không gửi request ID vẫn dùng hành vi cũ và không có bảo đảm idempotency. Bảng request tăng theo lượt review; chưa có retention policy. Không tự xóa record vì sẽ mất bảo đảm retry cũ.
- Backup production đã diễn tập trong lượt trước dùng `--no-owner --no-privileges` khi restore; owner/grant và toàn bộ kịch bản tải production chưa được chứng minh. APK debug mặc định trỏ production hiện tại và sẽ từ chối phiên ôn đến khi backend mới có capability.

## NOT EXECUTED / triển khai dự kiến

- Không deploy/restart Azure, không migration hay ghi Neon production, không thay Gmail OTP, SMTP/Fernet key, worker hay Blob. Emulator và server test đã dừng; không gửi email thật.
- Trước production: xác minh backup/revision/rehearsal còn phù hợp, checksum và RAM, chốt cửa sổ và quyền owner/grant; đưa migration file, chạy `d4e9b137c802` với timeout sau phê duyệt riêng, xác minh schema/dữ liệu. Deploy backend candidate, restart API có kiểm soát, xác minh health/JWT/queue OTP và flashcard bằng tài khoản được phép; chỉ sau đó phát hành APK.
- Khi lỗi code, rollback code tương thích schema mở rộng, giữ bảng idempotency; không tự downgrade vì sẽ xóa kết quả retry. Nếu lỗi dữ liệu ưu tiên forward-fix và xin phê duyệt riêng trước restore production.
