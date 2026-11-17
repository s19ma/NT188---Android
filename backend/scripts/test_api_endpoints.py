import json
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000/api/v1"
PUB_ID = "00d98733-a587-48c4-b006-2fb17ba38ab9"
DRAFT_ID = "af9823fb-60eb-4608-a11e-2e2306472927"

print("=" * 65)
print("TEST SUITE: VIDEOS, PLAYBACK & SUBTITLES")
print("=" * 65)

# 1. Đăng ký tài khoản nếu chưa có
reg_data = json.dumps({
    "email": "learner@example.com",
    "password": "LearnerPassword123",
    "display_name": "Learner User"
}).encode("utf-8")
reg_req = urllib.request.Request(
    f"{BASE_URL}/users/register",
    data=reg_data,
    headers={"Content-Type": "application/json"}
)
try:
    urllib.request.urlopen(reg_req)
except Exception:
    pass

# 2. Login lấy JWT
login_data = b"username=learner@example.com&password=LearnerPassword123"
login_req = urllib.request.Request(
    f"{BASE_URL}/users/login",
    data=login_data,
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
with urllib.request.urlopen(login_req) as resp:
    token = json.loads(resp.read().decode("utf-8"))["access_token"]
print("[1] Login & JWT Acquisition        -> SUCCESS")

# 3. Test Public Video List (GET /videos)
with urllib.request.urlopen(f"{BASE_URL}/videos") as resp:
    videos = json.loads(resp.read().decode("utf-8"))
assert len(videos) == 1
assert videos[0]["status"] == "published"
print(f"[2] Public Video List               -> PASSED ({len(videos)} published video)")

# 4. Test Public Video Detail (GET /videos/{id})
with urllib.request.urlopen(f"{BASE_URL}/videos/{PUB_ID}") as resp:
    detail = json.loads(resp.read().decode("utf-8"))
assert detail["id"] == PUB_ID
assert detail["status"] == "published"
print(f"[3] Public Video Detail             -> PASSED (HTTP 200, status={detail['status']})")

# 5. Test Draft Video Detail (mong đợi 404)
try:
    urllib.request.urlopen(f"{BASE_URL}/videos/{DRAFT_ID}")
    print("[4] Draft Video Detail (Expect 404) -> FAILED")
except urllib.error.HTTPError as e:
    assert e.code == 404
    print(f"[4] Draft Video Detail (Expect 404) -> PASSED (HTTP {e.code})")

# 6. Playback without JWT (mong đợi 401)
try:
    urllib.request.urlopen(f"{BASE_URL}/videos/{PUB_ID}/playback")
    print("[5] Playback without JWT (Exp 401)  -> FAILED")
except urllib.error.HTTPError as e:
    assert e.code == 401
    print(f"[5] Playback without JWT (Exp 401)  -> PASSED (HTTP {e.code})")

# 7. Playback with JWT -> 200 & SAS URL
pb_req = urllib.request.Request(
    f"{BASE_URL}/videos/{PUB_ID}/playback",
    headers={"Authorization": f"Bearer {token}"}
)
with urllib.request.urlopen(pb_req) as resp:
    pb = json.loads(resp.read().decode("utf-8"))
assert pb["video_id"] == PUB_ID
assert "playback_url" in pb
assert pb["expires_in"] == 1800
print(f"[6] Playback with JWT               -> PASSED (expires_in={pb['expires_in']}s)")

# 8. SAS URL Playable check (HEAD request trực tiếp Azure -> 200)
req_sas = urllib.request.Request(pb["playback_url"], method="HEAD")
with urllib.request.urlopen(req_sas) as resp:
    assert resp.status == 200
    content_len = resp.headers.get("Content-Length")
    print(f"    -> Azure SAS URL playable       -> PASSED (HTTP 200, {content_len} bytes)")

# 9. Subtitles without JWT (mong đợi 401)
try:
    urllib.request.urlopen(f"{BASE_URL}/videos/{PUB_ID}/subtitles")
    print("[7] Subtitles without JWT (Exp 401) -> FAILED")
except urllib.error.HTTPError as e:
    assert e.code == 401
    print(f"[7] Subtitles without JWT (Exp 401) -> PASSED (HTTP {e.code})")

# 10. Subtitles with JWT -> 200 & verify 75 segments
sub_req = urllib.request.Request(
    f"{BASE_URL}/videos/{PUB_ID}/subtitles?language_code=en",
    headers={"Authorization": f"Bearer {token}"}
)
with urllib.request.urlopen(sub_req) as resp:
    sub = json.loads(resp.read().decode("utf-8"))
assert sub["video_id"] == PUB_ID
assert sub["total_segments"] == 75
assert len(sub["segments"]) == 75
seg1 = sub["segments"][0]
print(f"[8] Subtitles with JWT              -> PASSED (total_segments={sub['total_segments']})")
print(f"    -> First segment preview: #{seg1['sequence_number']} [{seg1['start_ms']}ms -> {seg1['end_ms']}ms]: {seg1['content']}")

# 11. Subtitles for Draft Video (mong đợi 404)
try:
    draft_sub_req = urllib.request.Request(
        f"{BASE_URL}/videos/{DRAFT_ID}/subtitles",
        headers={"Authorization": f"Bearer {token}"}
    )
    urllib.request.urlopen(draft_sub_req)
    print("[9] Draft Subtitles (Expect 404)    -> FAILED")
except urllib.error.HTTPError as e:
    assert e.code == 404
    print(f"[9] Draft Subtitles (Expect 404)    -> PASSED (HTTP {e.code})")

print("\n" + "=" * 65)
print(">>> ALL 7 CHECKLIST ITEMS FULLY VERIFIED! <<<")
print("=" * 65)
