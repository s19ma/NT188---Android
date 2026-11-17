# Production fixed review and video vocabulary — 17/11/2026

## SUCCESS
- Deployed scheduler: again 10 minutes, hard 1 day, good 3 days, easy 7 days; 4 consecutive successful ratings marks learned. Existing scheduled dates retained until next review.
- API video vocabulary default now 30; all 3 published videos returned 30 entries. Flashcard overview returns fixed_review_intervals=true. Health and authorized GET smoke checks passed.
- Database revision remains e8a72c14d931; no migration. Counts after: users 5, vocabulary 516, user_vocabulary 14, learning_days 2, daily_flashcard_goals 0. API, Caddy, email worker, queue timer active.
- Candidate SHA-256 2C8C61356FDF7721531EA64B4E4E34326774D88B89AE97F99FE2BF5C9635A6A4; deployed file hashes match candidate. API restarted under control; no SMTP/Fernet/OTP/Blob change.
- 37 backend tests and 12 subtests pass in isolated PostgreSQL; Android debug build and unit tests pass.
- Backup database english-video-20261117T025731Z.pgdump.fernet SHA-256 67B51E65F028028C4D99065DA2ED13743EDBD8617FC3B39DD5D6A5775A6B2360, decrypt and pg_restore list pass. Backup code/config azure-code-config-20261117T023714Z.tar.gz.fernet SHA-256 8732C6DC1C62BBCA6BC8083F1303B708512C1B688DAD586AB12F216D1FDB340B, decrypt and rollback file presence checked.

## WARNING / NOT EXECUTED
- No production flashcard review was submitted; rating/streak behavior was tested in isolated database, not end to end on production. No email was sent.
- Device subsequently reconnected; installed debug APK SHA-256 223BC3C37D3E406A8C1E85CADE6E21C3BA745664BE42ACB947D27DF029BB4502 matches latest build installed previously. Old Android clients cannot infer changed fixed intervals unless updated; APK is debug signed.
- Existing learned flags and schedules are not migrated; they are recalculated by new policy upon next review. Manually assigning learned remains a distinct operation. Backups depend on Windows DPAPI.
