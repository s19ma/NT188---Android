# Flashcard spaced repetition — kiểm thử và triển khai

Ngày 16/11/2026. **Chưa triển khai production.**

## SUCCESS

- Hàng đợi due-only tối đa 30, NULL được ưu tiên, sau đó theo due time và ID; dữ liệu thuộc user hiện hành. Giữ thuật toán 1 ngày, 6 ngày, và Again 10 phút.
- `request_id` UUID tùy chọn cho review: PostgreSQL advisory transaction lock theo user/request ID và row lock trên thẻ; kết quả được lưu trong cùng transaction, retry trả lại snapshot ban đầu; reuse khác card/rating trả 409. Không lưu JWT trong bảng. Thẻ chưa đến hạn trả 409 khi dùng request ID mới; client cũ không gửi request ID giữ hành vi cũ.
- Android giữ trạng thái session và request đang chạy qua ViewModel khi xoay; retry dùng lại request ID và rating, không chuyển thẻ trước thành công. Khi 409 xóa thẻ không còn đến hạn khỏi session. Hiển thị interval và ngày giờ theo múi giờ thiết bị. APK kiểm tra capability backend trước khi bắt đầu phiên, tránh review vào server cũ chưa hỗ trợ idempotency.
- PostgreSQL Docker test riêng `english_video_flashcard_test`, không dùng Neon: **21 tests pass**, gồm 0/5/30/31/50/100 due, future, NULL, thứ tự ID, user isolation, HTTP replay, payload conflict, hai request đồng thời cùng/khác ID, rollback, snapshot replay, UTC/DST, 1 ngày/6 ngày/10 phút. Một cảnh báo Starlette/httpx.
- Migration `c693a17e4d08 → d4e9b137c802` được thử trên database Docker fixture độc lập; schema fixture tối thiểu, không phải bản sao Neon. `assembleDebug` pass.
- Candidate backend `deploy/flashcard-idempotency-candidate.tar`, SHA-256 `69878528D6270346E7E6571CCE44406FD463E665D5A5A2620CAA860CA5B751F2`; 5 file khớp source. APK debug trỏ production hiện tại; capability check sẽ từ chối ôn tập cho tới khi backend mới được deploy.

## WARNING / BLOCKED

- Chưa có kiểm thử UI và lifecycle có xác thực trên thiết bị/emulator hoặc kiểm thử process bị hệ điều hành kill trong lúc request. State pending được lưu qua `onSaveInstanceState`, nhưng không bảo đảm khi process bị kill trước khi state được lưu. Không kết luận Android lifecycle đã được chứng minh đầy đủ.
- Test API dùng TestClient và fixture PostgreSQL, chưa xác nhận trên bản sao schema/data Neon. Chưa chạy đầy đủ regression vocabulary/progress hoặc test tải kéo dài.
- Client cũ không gửi request ID nên không được bảo vệ idempotency và vẫn có thể review sớm theo hành vi cũ. Bảng request lưu snapshot và tăng theo số lần review; cần theo dõi dung lượng và chính sách retention trước khi xóa bất kỳ bản ghi nào. Nếu xóa bản ghi, retry rất cũ không còn đảm bảo idempotency.
- `next_review_at` được hiển thị dựa trên thời gian UTC từ backend; chưa có test UI trên múi giờ thiết bị thực. Trong trường hợp request đã commit nhưng response mất, người dùng cần retry cùng mức đánh giá.

## NOT EXECUTED / kế hoạch production

- Không deploy Azure, không migration hay ghi Neon production; không đổi OTP/SMTP/Fernet/worker/Blob.
- Trước deploy: kiểm tra backup và migration trên bản sao độc lập, compatibility với phiên bản client, checksum candidate, RAM và health. Triển khai migration `d4e9b137c802` trước backend, kiểm tra schema/revision; sau đó triển khai backend rồi APK. Chỉ smoke test account và dữ liệu được phép.
- Nếu lỗi code: rollback backend theo backup sau khi đánh giá compatibility, giữ bảng request và schema mở rộng. Không tự downgrade vì xóa bảng làm mất kết quả idempotency; ưu tiên forward-fix. Đánh giá trường hợp pending request trước mọi rollback.
