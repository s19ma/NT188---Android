# Android UI test report — 16/11/2026

Thiết bị 2406APNFAG, Android 16/API 36, 1220x2712; APK debug SHA-256 EA588E6BF766BA3B69D9E94C4A7331E37CCCAA24CB6EA4D13C32B3D6F22C6423, cài install -r. Kiểm tra thực tế bằng UI hierarchy, không có bằng chứng visual QA đầy đủ.

| Activity | Kết quả |
|---|---|
| LoginActivity | PASS — hiển thị, đăng nhập tài khoản test |
| HomeActivity | PASS — catalog/streak hiển thị; có prompt tiếp tục phiên |
| RegisterActivity | NOT EXECUTED — chưa thao tác runtime |
| OtpVerificationActivity | NOT EXECUTED — chưa thao tác runtime |
| RegisterSuccessActivity | NOT EXECUTED — chưa thao tác runtime |
| ForgotPasswordActivity | NOT EXECUTED — chưa thao tác runtime |
| ForgotPasswordOtpActivity | NOT EXECUTED — chưa thao tác runtime |
| ResetPasswordActivity | NOT EXECUTED — chưa thao tác runtime |
| ResetPasswordSuccessActivity | NOT EXECUTED — chưa thao tác runtime |
| PlayerTranscriptActivity | NOT EXECUTED — chưa thao tác runtime |
| SearchActivity | NOT EXECUTED — chưa thao tác runtime |
| NotificationActivity | NOT EXECUTED — chưa thao tác runtime |
| ProfileActivity | PASS — sửa và kiểm tra lại tên null trên APK mới |
| VocabularyActivity | PASS — 16 từ; 11 đang học (gồm mới), 5 đã thuộc |
| FlashcardActivity | PASS một phần — 10 đến hạn, phiên 1/10, tiếp tục phiên và lật thấy nghĩa; chưa đánh giá thẻ |
| ProgressActivity | PASS — 16 từ, 5 đã thuộc, 10 đến hạn khớp dữ liệu mẫu |
| QuizActivity | NOT EXECUTED — chưa thao tác runtime |
| QuizFillActivity | NOT EXECUTED — chưa thao tác runtime |
| QuizDictationActivity | NOT EXECUTED — chưa thao tác runtime |
| QuizResultActivity | NOT EXECUTED — chưa thao tác runtime |
| AdminActivity | NOT EXECUTED — chưa thao tác runtime |
| AdminVideoManagementActivity | NOT EXECUTED — chưa thao tác runtime |
| AdminReportActivity | NOT EXECUTED — chưa thao tác runtime |
| DictionaryPopupActivity | NOT EXECUTED — chưa thao tác runtime |
| SpacedRepetitionActivity | NOT EXECUTED — chưa thao tác runtime |
| VocabDetailActivity | NOT EXECUTED — chưa thao tác runtime |
| UploadVideoActivity | NOT EXECUTED — chưa thao tác runtime |
| SummaryActivity | NOT EXECUTED — chưa thao tác runtime |
| VideoVocabActivity | NOT EXECUTED — chưa thao tác runtime |
| VideoDetailActivity | NOT EXECUTED — chưa thao tác runtime |
| EditTranscriptActivity | NOT EXECUTED — chưa thao tác runtime |

6 activity đã quan sát; không coi các trạng thái chưa thử là PASS. Portrait được quan sát; landscape, xoay khi request, process death, mạng, crash/ANR, OTP, admin và player chưa thử. Player có PUT progress khi onPause nên không mở trong production khi chưa được phép ghi.
Resume chỉ xác nhận prompt và mở lại phiên, chưa giả lập process death. Không gửi review.
