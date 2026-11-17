import sys
from pathlib import Path

# Thêm thư mục gốc backend vào sys.path
BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app.services.azure_storage import azure_storage

TEST_FILES = [
    (
        "How to effectively use visuals in your presentation.mp4",
        "video",
    ),
    (
        "Is salt the most important ingredient in history_ - Carolyn Beans.mp4",
        "video",
    ),
    (
        "Why is pepper such a popular spice_ - Carolyn Beans.mp4",
        "video",
    ),
    (
        "How to effectively use visuals in your presentation.srt",
        "subtitle",
    ),
    (
        "Is salt the most important ingredient in history.srt",
        "subtitle",
    ),
    (
        "Why is pepper such a popular spice.srt",
        "subtitle",
    ),
]

all_passed = True

try:
    print("=" * 65)
    print("TESTING AZURE BLOB STORAGE CONNECTION & BLOBS EXISTENCE")
    print("=" * 65)

    for blob_name, resource_type in TEST_FILES:
        exists = azure_storage.blob_exists(blob_name, resource_type=resource_type)
        status = "PASSED (Exists: True)" if exists else "FAILED (Exists: False)"
        print(f"[{resource_type.upper():<8}] {blob_name:<68} -> {status}")
        if not exists:
            all_passed = False

    print("\n" + "=" * 65)
    print("TESTING SAS URL GENERATION")
    print("=" * 65)
    test_video = "How to effectively use visuals in your presentation.mp4"
    url = azure_storage.generate_read_url(blob_name=test_video, resource_type="video")
    base_url = url.split("?")[0]
    has_token = "?" in url and "sig=" in url
    print("SAS URL generated successfully!")
    print("Base URL:", base_url)
    print("Has valid SAS token parameter:", has_token)

    if all_passed and has_token:
        print("\n>>> ALL AZURE STORAGE TESTS PASSED! <<<")
    else:
        print("\n>>> SOME TESTS FAILED! <<<")

finally:
    azure_storage.close()
