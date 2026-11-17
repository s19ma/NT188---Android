# Full API test matrix — 16/11/2026

49 operations; production read-only + login; no response bodies or credentials retained.

| Method | Path | Tag | Auth (OpenAPI) | Request → Response | Effect / access | Result |
|---|---|---|---|---|---|---|
| POST | `/api/v1/users/register` | Users | public / xem source | application/json UserCreate → 201 UserResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| POST | `/api/v1/users/login` | Users | public / xem source | application/x-www-form-urlencoded Body_login_api_v1_users_login_post → 200 Token, 422 HTTPValidationError | Read-only; admin nếu /admin/ | PASS — HTTP 200, tài khoản test |
| GET | `/api/v1/users/me` | Users | JWT | none → 200 UserResponse | Read-only; admin nếu /admin/ | PASS — HTTP 200; JWT missing: 401; JWT invalid: 401 |
| DELETE | `/api/v1/users/me` | Users | JWT | none → 204 inline | Mutation; admin/email/user | NOT EXECUTED |
| PATCH | `/api/v1/users/me` | Users | JWT | application/json UserUpdate → 200 UserResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| GET | `/api/v1/videos` | Videos | public / xem source | cefr_level, category → 200 inline, 422 HTTPValidationError | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| GET | `/api/v1/videos/{video_id}` | Videos | public / xem source | video_id → 200 VideoResponse, 422 HTTPValidationError | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| GET | `/api/v1/videos/{video_id}/summary` | Videos | public / xem source | video_id → 200 VideoSummaryResponse, 422 HTTPValidationError | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| GET | `/api/v1/videos/{video_id}/playback` | Playback | JWT | video_id → 200 PlaybackResponse, 422 HTTPValidationError | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| GET | `/api/v1/videos/{video_id}/subtitles` | Subtitles | JWT | video_id, language_code → 200 SubtitleResponse, 422 HTTPValidationError | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| GET | `/api/v1/vocabulary` | Vocabulary | public / xem source | language_code, part_of_speech, skip, limit → 200 inline, 422 HTTPValidationError | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| GET | `/api/v1/vocabulary/search` | Vocabulary | public / xem source | q, language_code, limit → 200 inline, 422 HTTPValidationError | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| GET | `/api/v1/dictionary/{word}` | Vocabulary | public / xem source | word → 200 DictionaryLookupResponse, 422 HTTPValidationError | Có thể ghi dictionary cache; không chạy | NOT EXECUTED |
| GET | `/api/v1/videos/{video_id}/vocabulary` | Vocabulary | JWT | video_id, limit → 200 inline, 422 HTTPValidationError | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| GET | `/api/v1/vocabulary/{vocabulary_id}` | Vocabulary | public / xem source | vocabulary_id → 200 VocabularyResponse, 422 HTTPValidationError | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| POST | `/api/v1/vocabulary/{vocabulary_id}/save` | Vocabulary | JWT | application/json SaveVocabularyRequest → 201 UserVocabularyResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| GET | `/api/v1/users/me/vocabulary` | Vocabulary | JWT | learning_status, skip, limit → 200 inline, 422 HTTPValidationError | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| DELETE | `/api/v1/users/me/vocabulary/{saved_id}` | Vocabulary | JWT | saved_id → 204 inline, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| PATCH | `/api/v1/users/me/vocabulary/{saved_id}/status` | Vocabulary | JWT | application/json UpdateLearningStatusRequest → 200 UserVocabularyResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| GET | `/api/v1/users/me/flashcards/overview` | Flashcards | JWT | none → 200 FlashcardOverviewResponse | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| GET | `/api/v1/users/me/flashcards` | Flashcards | JWT | due_only, limit → 200 inline, 422 HTTPValidationError | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| POST | `/api/v1/users/me/flashcards/{saved_id}/review` | Flashcards | JWT | application/json ReviewVocabularyRequest → 200 UserVocabularyResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| GET | `/api/v1/users/me/progress` | Learning Progress | JWT | skip, limit → 200 inline, 422 HTTPValidationError | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| GET | `/api/v1/users/me/progress/{video_id}` | Learning Progress | JWT | video_id → 200 LearningProgressResponse, 422 HTTPValidationError | Read-only; admin nếu /admin/ | BLOCKED — HTTP 404, video không có progress; chưa thử response 200 |
| PUT | `/api/v1/users/me/progress/{video_id}` | Learning Progress | JWT | application/json LearningProgressUpdate → 200 LearningProgressResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| GET | `/api/v1/users/me/streak` | Statistics | JWT | none → 200 inline | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| GET | `/api/v1/users/me/statistics` | Statistics | JWT | none → 200 LearningStatisticsResponse | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| POST | `/api/v1/auth/email-verification/resend` | Authentication | public / xem source | application/json PasswordResetRequest → 200 MessageResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| POST | `/api/v1/auth/email-verification/confirm` | Authentication | public / xem source | application/json PasswordResetVerify → 200 MessageResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| POST | `/api/v1/auth/password-reset/request` | Authentication | public / xem source | application/json PasswordResetRequest → 200 MessageResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| POST | `/api/v1/auth/password-reset/verify` | Authentication | public / xem source | application/json PasswordResetVerify → 200 MessageResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| POST | `/api/v1/auth/password-reset/confirm` | Authentication | public / xem source | application/json PasswordResetConfirm → 200 MessageResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| GET | `/api/v1/quizzes/default` | Quizzes | JWT | none → 200 QuizResponse | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| POST | `/api/v1/quizzes/default/submit` | Quizzes | JWT | application/json QuizSubmission → 200 QuizResult, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| GET | `/api/v1/quizzes/history` | Quizzes | JWT | none → 200 inline | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| GET | `/api/v1/admin/overview` | Administration | JWT | none → 200 AdminOverview | Read-only; admin nếu /admin/ | BLOCKED — learner HTTP 403 đúng; chưa kiểm thử quyền Admin |
| GET | `/api/v1/admin/videos` | Administration | JWT | q, category, cefr_level, status, limit, skip → 200 inline, 422 HTTPValidationError | Read-only; admin nếu /admin/ | BLOCKED — learner HTTP 403 đúng; chưa kiểm thử quyền Admin |
| POST | `/api/v1/admin/videos` | Administration | JWT | application/json AdminVideoCreate → 201 VideoResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| PATCH | `/api/v1/admin/videos/{video_id}` | Administration | JWT | application/json AdminVideoUpdate → 200 VideoResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| POST | `/api/v1/admin/videos/{video_id}/upload-video` | Administration | JWT | multipart/form-data Body_upload_video_api_v1_admin_videos__video_id__upload_video_post → 200 VideoResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| POST | `/api/v1/admin/videos/{video_id}/upload-thumbnail` | Administration | JWT | multipart/form-data Body_upload_thumbnail_api_v1_admin_videos__video_id__upload_thumbnail_post → 200 VideoResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| POST | `/api/v1/admin/videos/{video_id}/upload-subtitle` | Administration | JWT | multipart/form-data Body_upload_subtitle_api_v1_admin_videos__video_id__upload_subtitle_post → 200 inline, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| POST | `/api/v1/admin/videos/{video_id}/publish` | Administration | JWT | video_id → 200 VideoResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| PATCH | `/api/v1/admin/videos/{video_id}/status` | Administration | JWT | application/json VideoStatusUpdate → 200 VideoResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| PUT | `/api/v1/admin/videos/{video_id}/summary` | Administration | JWT | application/json VideoSummaryUpsertRequest → 200 VideoSummaryResponse, 422 HTTPValidationError | Mutation; admin/email/user | NOT EXECUTED |
| GET | `/` | health | public / xem source | none → 200 inline | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| GET | `/health` | health | public / xem source | none → 200 inline | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| GET | `/health/db` | health | public / xem source | none → 200 inline | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
| GET | `/health/models` | health | public / xem source | none → 200 inline | Read-only; admin nếu /admin/ | PASS — HTTP 200 |
