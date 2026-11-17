import os
import sys
from pathlib import Path
from datetime import timedelta
import srt
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ============================================================
# 1. CONFIGURATION
# ============================================================
BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Missing DATABASE_URL configuration.")

ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "engvideoapp2026")
ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER", "subtitles")

LOCAL_SRT_DIR = BASE_DIR.parent / "Resouces" / "Video"

# Expected subtitle counts from local SRT verification.
EXPECTED_FILES = {
    "How to effectively use visuals in your presentation.srt": 69,
    "Is salt the most important ingredient in history.srt": 75,
    "Why is pepper such a popular spice.srt": 73,
}

# ============================================================
# 2. DATABASE CONNECTION
# ============================================================
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
)

# ============================================================
# 3. HELPER FUNCTIONS
# ============================================================
def timedelta_to_ms(td: timedelta) -> int:
    """Chuyển timedelta thành milliseconds (int)."""
    return int(td.total_seconds() * 1000)


def get_srt_content(filename: str) -> str:
    """
    Tải nội dung SRT từ Azure Blob nếu có account_key,
    nếu không thì fallback sang thư mục Resouces/Video cục bộ.
    """
    if ACCOUNT_KEY:
        from azure.storage.blob import BlobServiceClient
        account_url = f"https://{ACCOUNT_NAME}.blob.core.windows.net"
        blob_service_client = BlobServiceClient(account_url=account_url, credential=ACCOUNT_KEY)
        blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=filename)
        print(f"Downloading from Azure ({CONTAINER_NAME}/{filename})...")
        return blob_client.download_blob().readall().decode("utf-8")
    else:
        local_path = LOCAL_SRT_DIR / filename
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")
        print(f"Reading local source: {filename}")
        return local_path.read_text(encoding="utf-8")


# ============================================================
# 4. MAIN SYNC LOGIC
# ============================================================
def main():
    print("=" * 60)
    print("AZURE / LOCAL SRT -> NEON TRANSCRIPT SEGMENTS SYNC")
    print("=" * 60)

    parsed_data = {}
    for filename, expected_count in EXPECTED_FILES.items():
        raw_text = get_srt_content(filename)
        segments = list(srt.parse(raw_text))
        actual_count = len(segments)
        print(f"Parsed successfully: {actual_count} segments")

        if actual_count != expected_count:
            raise ValueError(
                f"Count mismatch for {filename}: expected {expected_count}, got {actual_count}"
            )
        parsed_data[filename] = segments

    total_inserted = 0
    total_verified = 0

    with engine.begin() as conn:
        # Lấy danh sách transcript_id từ Neon theo blob_name
        stmt = text("SELECT id, blob_name FROM transcripts WHERE blob_name = ANY(:names)")
        rows = conn.execute(stmt, {"names": list(EXPECTED_FILES.keys())}).fetchall()
        transcript_map = {r.blob_name: r.id for r in rows}

        for filename in EXPECTED_FILES.keys():
            if filename not in transcript_map:
                raise RuntimeError(f"Transcript record for {filename} not found in database.")

        for filename, segments in parsed_data.items():
            print(f"\nProcessing: {filename}")
            transcript_id = transcript_map[filename]

            # Kiểm tra các segment hiện có để đối soát tính toàn vẹn
            check_stmt = text("""
                SELECT sequence_number, start_ms, end_ms, content
                FROM transcript_segments
                WHERE transcript_id = :tid
            """)
            existing_rows = {
                r.sequence_number: r
                for r in conn.execute(check_stmt, {"tid": transcript_id}).fetchall()
            }

            inserted_for_file = 0
            for sub in segments:
                start_ms = timedelta_to_ms(sub.start)
                end_ms = timedelta_to_ms(sub.end)
                content = sub.content.strip()

                if sub.index in existing_rows:
                    ex = existing_rows[sub.index]
                    if ex.start_ms != start_ms or ex.end_ms != end_ms or ex.content != content:
                        raise ValueError(
                            f"Data integrity error in {filename} seq {sub.index}: "
                            f"existing ({ex.start_ms}-{ex.end_ms}) vs new ({start_ms}-{end_ms})"
                        )
                else:
                    insert_stmt = text("""
                        INSERT INTO transcript_segments (
                            transcript_id,
                            sequence_number,
                            start_ms,
                            end_ms,
                            content,
                            translation
                        ) VALUES (
                            :transcript_id,
                            :sequence_number,
                            :start_ms,
                            :end_ms,
                            :content,
                            NULL
                        )
                        ON CONFLICT ON CONSTRAINT transcript_segments_transcript_id_sequence_number_key
                        DO NOTHING
                    """)
                    res = conn.execute(insert_stmt, {
                        "transcript_id": transcript_id,
                        "sequence_number": sub.index,
                        "start_ms": start_ms,
                        "end_ms": end_ms,
                        "content": content,
                    })
                    if res.rowcount > 0:
                        inserted_for_file += 1

            # Xác thực lại số lượng bản ghi trong database sau insert
            verify_stmt = text("""
                SELECT COUNT(*) FROM transcript_segments WHERE transcript_id = :tid
            """)
            verified_count = conn.scalar(verify_stmt, {"tid": transcript_id})

            print(f"Inserted: {inserted_for_file}")
            print(f"Verified: {verified_count}")

            total_inserted += inserted_for_file
            total_verified += verified_count

    print("\n" + "=" * 60)
    print("SYNC COMPLETED SUCCESSFULLY")
    print("=" * 60)
    print(f"New records inserted: {total_inserted}")
    print(f"Records verified: {total_verified}")
    print("Database transaction: COMMITTED")


if __name__ == "__main__":
    main()
