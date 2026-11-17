import json
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000/api/v1"
PUB_VIDEO_ID = "00d98733-a587-48c4-b006-2fb17ba38ab9"
REAL_SEGMENT_ID = 70  # Segment #1 của video salt

print("=" * 65)
print("TEST SUITE: VOCABULARY API")
print("=" * 65)

# 1. Login lấy JWT cho user
login_data = b"username=learner@example.com&password=LearnerPassword123"
login_req = urllib.request.Request(
    f"{BASE_URL}/users/login",
    data=login_data,
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
with urllib.request.urlopen(login_req) as resp:
    token = json.loads(resp.read().decode("utf-8"))["access_token"]
auth_header = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
print("[0] Authentication -> JWT obtained")

# Test 1: GET /api/v1/vocabulary
with urllib.request.urlopen(f"{BASE_URL}/vocabulary") as resp:
    assert resp.status == 200
    vocab_list = json.loads(resp.read().decode("utf-8"))
    assert any(v["lemma"] == "salt" for v in vocab_list)
    salt_item = next(v for v in vocab_list if v["lemma"] == "salt")
    salt_id = salt_item["id"]
print(f"[1] GET /vocabulary -> PASSED (Found salt, id={salt_id})")

# Test 2: GET /api/v1/vocabulary/search?q=salt
with urllib.request.urlopen(f"{BASE_URL}/vocabulary/search?q=salt") as resp:
    assert resp.status == 200
    search_list = json.loads(resp.read().decode("utf-8"))
    assert any(v["lemma"] == "salt" for v in search_list)
print(f"[2] GET /vocabulary/search?q=salt -> PASSED (Found {len(search_list)} results)")

# Test 3: GET /api/v1/vocabulary/{id}
with urllib.request.urlopen(f"{BASE_URL}/vocabulary/{salt_id}") as resp:
    assert resp.status == 200
    detail = json.loads(resp.read().decode("utf-8"))
    assert detail["lemma"] == "salt"
    assert detail["part_of_speech"] == "noun"
print(f"[3] GET /vocabulary/{salt_id} -> PASSED (Phonetic: {detail['phonetic']})")

# Test 4: POST /api/v1/vocabulary/{id}/save
save_payload = json.dumps({
    "video_id": PUB_VIDEO_ID,
    "transcript_segment_id": REAL_SEGMENT_ID,
    "context_sentence": "Salt is one of the most important ingredients in history."
}).encode("utf-8")
save_req = urllib.request.Request(
    f"{BASE_URL}/vocabulary/{salt_id}/save",
    data=save_payload,
    headers=auth_header,
    method="POST"
)
with urllib.request.urlopen(save_req) as resp:
    assert resp.status == 201
    saved_res = json.loads(resp.read().decode("utf-8"))
    saved_id = saved_res["id"]
    assert saved_res["vocabulary"]["lemma"] == "salt"
    assert saved_res["video_id"] == PUB_VIDEO_ID
    assert saved_res["transcript_segment_id"] == REAL_SEGMENT_ID
print(f"[4] POST /vocabulary/{salt_id}/save -> PASSED (HTTP 201, saved_id={saved_id})")

# Test 5: POST lưu lại cùng từ (mong đợi 409 Conflict)
try:
    urllib.request.urlopen(save_req)
    print("[5] Duplicate save (Expect 409) -> FAILED")
except urllib.error.HTTPError as e:
    assert e.code == 409
    print(f"[5] Duplicate save (Expect 409) -> PASSED (HTTP {e.code})")

# Test 6: GET /api/v1/users/me/vocabulary
me_vocab_req = urllib.request.Request(
    f"{BASE_URL}/users/me/vocabulary",
    headers={"Authorization": f"Bearer {token}"}
)
with urllib.request.urlopen(me_vocab_req) as resp:
    assert resp.status == 200
    my_vocab = json.loads(resp.read().decode("utf-8"))
    assert len(my_vocab) == 1
    assert my_vocab[0]["vocabulary"]["lemma"] == "salt"
print(f"[6] GET /users/me/vocabulary -> PASSED ({len(my_vocab)} saved word)")

# Test 7: DELETE /api/v1/users/me/vocabulary/{saved_id}
del_req = urllib.request.Request(
    f"{BASE_URL}/users/me/vocabulary/{saved_id}",
    headers={"Authorization": f"Bearer {token}"},
    method="DELETE"
)
with urllib.request.urlopen(del_req) as resp:
    assert resp.status == 204
print(f"[7] DELETE /users/me/vocabulary/{saved_id} -> PASSED (HTTP 204)")

# Test 8: GET danh sách cá nhân sau khi xóa (mong đợi rỗng)
with urllib.request.urlopen(me_vocab_req) as resp:
    assert resp.status == 200
    my_vocab_after = json.loads(resp.read().decode("utf-8"))
    assert len(my_vocab_after) == 0
print(f"[8] GET /users/me/vocabulary after deletion -> PASSED (Empty list: {my_vocab_after})")

print("\n" + "=" * 65)
print(">>> ALL 8 VOCABULARY TEST CASES PASSED SUCCESSFULLY! <<<")
print("=" * 65)
