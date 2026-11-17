import json
import urllib.error
import urllib.request

BASE_URL = "http://127.0.0.1:8000/api/v1"
PUB_VIDEO_ID = "00d98733-a587-48c4-b006-2fb17ba38ab9"
REAL_SEGMENT_ID = 70


def request(method, path, token=None, payload=None, expected=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(
        f"{BASE_URL}{path}",
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            body = json.loads(raw) if raw else None
            if expected is not None and resp.status not in expected:
                raise SystemExit(f"{method} {path} -> {resp.status}, expected {expected}: {body}")
            return resp.status, body
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            body = raw
        if expected is not None and exc.code not in expected:
            raise SystemExit(f"{method} {path} -> {exc.code}, expected {expected}: {body}")
        return exc.code, body


print("=" * 65)
print("TEST SUITE: LEARNING APIs")
print("=" * 65)

login_data = b"username=learner@example.com&password=LearnerPassword123"
login_req = urllib.request.Request(
    f"{BASE_URL}/users/login",
    data=login_data,
    headers={"Content-Type": "application/x-www-form-urlencoded"},
)
with urllib.request.urlopen(login_req) as resp:
    token = json.loads(resp.read().decode("utf-8"))["access_token"]
print("[0] Authentication -> JWT obtained")

_, vocab_list = request("GET", "/vocabulary", expected={200})
salt = next(item for item in vocab_list if item["lemma"] == "salt")
salt_id = salt["id"]

_, saved_before = request("GET", "/users/me/vocabulary", token=token, expected={200})
for item in saved_before:
    if item["vocabulary_id"] == salt_id:
        request("DELETE", f"/users/me/vocabulary/{item['id']}", token=token, expected={204})

status_code, _ = request(
    "POST",
    f"/vocabulary/{salt_id}/save",
    token=token,
    payload={
        "video_id": PUB_VIDEO_ID,
        "transcript_segment_id": 999999,
        "context_sentence": "This segment does not belong to the video.",
    },
    expected={400},
)
print(f"[1] POST save with foreign segment -> PASSED (HTTP {status_code})")

_, saved = request(
    "POST",
    f"/vocabulary/{salt_id}/save",
    token=token,
    payload={
        "video_id": PUB_VIDEO_ID,
        "transcript_segment_id": REAL_SEGMENT_ID,
        "context_sentence": "Salt is one of the most important ingredients in history.",
    },
    expected={201},
)
saved_id = saved["id"]
assert saved["learning_status"] == "new"
assert saved["vocabulary"]["lemma"] == "salt"
print(f"[2] POST save -> PASSED (status={saved['learning_status']}, id={saved_id})")

_, cards = request("GET", "/users/me/flashcards", token=token, expected={200})
assert any(card["id"] == saved_id for card in cards)
print(f"[3] GET /users/me/flashcards -> PASSED ({len(cards)} due)")

_, reviewed = request(
    "POST",
    f"/users/me/flashcards/{saved_id}/review",
    token=token,
    payload={"rating": "good"},
    expected={200},
)
assert reviewed["learning_status"] == "learning"
assert reviewed["interval_days"] == 1
assert reviewed["repetitions"] == 1
assert reviewed["review_count"] == 1
print(
    f"[4] POST review good -> PASSED "
    f"(next interval {reviewed['interval_days']} day)"
)

_, due_after = request("GET", "/users/me/flashcards", token=token, expected={200})
assert all(card["id"] != saved_id for card in due_after)
print("[5] Due queue excludes the reviewed card -> PASSED")

_, learned = request(
    "PATCH",
    f"/users/me/vocabulary/{saved_id}/status",
    token=token,
    payload={"learning_status": "learned"},
    expected={200},
)
assert learned["learning_status"] == "learned"
assert learned["interval_days"] >= 21
print(f"[6] PATCH status learned -> PASSED (interval {learned['interval_days']} days)")

_, progress = request(
    "PUT",
    f"/users/me/progress/{PUB_VIDEO_ID}",
    token=token,
    payload={"position_ms": 12500, "is_completed": False},
    expected={200},
)
assert progress["position_ms"] == 12500
assert progress["is_completed"] is False
assert progress["video_title"]

_, loaded = request(
    "GET",
    f"/users/me/progress/{PUB_VIDEO_ID}",
    token=token,
    expected={200},
)
assert loaded["position_ms"] == 12500
print(f"[7] PUT/GET progress -> PASSED ({loaded['video_title']}, 12500 ms)")

_, stats = request("GET", "/users/me/statistics", token=token, expected={200})
assert stats["saved_words"] >= 1
assert stats["learned_words"] >= 1
assert stats["videos_in_progress"] >= 1
assert stats["total_reviews"] >= 1
print(
    "[8] GET /users/me/statistics -> PASSED "
    f"(saved={stats['saved_words']}, learned={stats['learned_words']}, "
    f"in_progress={stats['videos_in_progress']})"
)

request("DELETE", f"/users/me/vocabulary/{saved_id}", token=token, expected={204})
_, remaining = request("GET", "/users/me/vocabulary", token=token, expected={200})
assert all(item["id"] != saved_id for item in remaining)
print("[9] DELETE saved word -> PASSED")

print("\n" + "=" * 65)
print(">>> ALL LEARNING API TEST CASES PASSED <<<")
print("=" * 65)
