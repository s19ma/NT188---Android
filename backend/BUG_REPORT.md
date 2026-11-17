# Bug report — 16/11/2026

## Đã sửa local

1. Hồ sơ hiện `null` với display_name JSON null. Tái hiện: đăng nhập tài khoản test chưa đặt tên, vào Hồ sơ. Nguyên nhân JSONObject.optString chuyển JSON null thành chuỗi. Sửa ProfileActivity kiểm tra isNull; build/cài APK và quan sát lại không còn `null`. Không chứng minh mọi giá trị khác.
2. `VideoSummary.key_points` khai báo server_default bằng chuỗi khiến ORM create_all tạo SQL DEFAULT bị quote sai, PostgreSQL báo JSON không hợp lệ. Sửa dùng SQL text; schema test tạo thành công, có test compile DDL. Không sửa DB production.
3. Index ORM `lower("email")` nhận literal thay vì cột, dẫn tới unique index trên hằng số khi create_all, ngăn tạo user thứ hai. Sửa dùng SQL text lower(email); kiểm thử DDL và integration test nhiều tài khoản trên DB test. Không chạy migration trên production.

## Giới hạn

Alembic baseline không tạo schema từ đầu: upgrade database trống thất bại tại user_vocabulary; cần tài liệu hoặc baseline khởi tạo riêng nếu muốn hỗ trợ triển khai database mới. Đây là hạn chế setup, không xác nhận lỗi trên DB production. Không đánh giá các phần chưa chạy.
