"""Import up to ten licensed English-learning videos from the VM inbox.

Each lesson is one directory under VIDEO_IMPORT_INBOX:

    lesson-name/
      video.mp4
      subtitle.srt
      metadata.json
      thumbnail.jpg       # optional; generated with ffmpeg when omitted

The importer runs on the backend VM, so Azure credentials never leave the
server. Successful folders are moved to VIDEO_IMPORT_ARCHIVE. Failed folders
are deliberately left in the inbox for correction and retry.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

from app.core.config import settings
from app.db.database import SessionLocal
from app.models.transcript import Transcript
from app.models.transcript_segment import TranscriptSegment
from app.models.video import Video
from app.models.video_summary import VideoSummary
from app.services.azure_storage import azure_storage
from app.services.srt_parser import parse_srt

logger = logging.getLogger(__name__)
VIDEO_EXTENSIONS = {".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime"}
IMAGE_EXTENSIONS = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
CEFR_LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}


def _single_file(folder: Path, stem: str, allowed: dict[str, str]) -> tuple[Path, str]:
    files = [path for path in folder.iterdir() if path.is_file() and path.stem == stem and path.suffix.lower() in allowed]
    if len(files) != 1:
        raise ValueError(f"Expected exactly one {stem} file with extension: {', '.join(allowed)}")
    return files[0], allowed[files[0].suffix.lower()]


def _duration_seconds(video_path: Path) -> int:
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return max(0, round(float(completed.stdout.strip())))


def _create_thumbnail(video_path: Path, target: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-ss", "00:00:05", "-i", str(video_path), "-frames:v", "1", "-q:v", "3", str(target)],
        check=True, capture_output=True, text=True, timeout=120,
    )


def _metadata(folder: Path) -> dict:
    metadata_path = folder / "metadata.json"
    try:
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError("metadata.json is required") from error
    except json.JSONDecodeError as error:
        raise ValueError("metadata.json is not valid JSON") from error
    for field in ("title", "source_url", "license"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError(f"metadata.{field} is required")
    if data.get("rights_confirmed") is not True:
        raise ValueError("metadata.rights_confirmed must be true before import")
    level = data.get("cefr_level")
    if level is not None and level not in CEFR_LEVELS:
        raise ValueError("metadata.cefr_level must be A1, A2, B1, B2, C1, or C2")
    if not isinstance(data.get("summary", {}), dict):
        raise ValueError("metadata.summary must be an object when supplied")
    return data


def _append_attribution(description: str | None, metadata: dict) -> str:
    attribution = f"Nguồn: {metadata['source_url']}\nGiấy phép: {metadata['license']}"
    return f"{description.strip()}\n\n{attribution}" if isinstance(description, str) and description.strip() else attribution


def import_folder(folder: Path, *, dry_run: bool = False) -> str:
    metadata = _metadata(folder)
    video_path, video_mime = _single_file(folder, "video", VIDEO_EXTENSIONS)
    subtitle_path = folder / "subtitle.srt"
    if not subtitle_path.is_file():
        raise ValueError("subtitle.srt is required")
    subtitle_raw = subtitle_path.read_bytes()
    segments = parse_srt(subtitle_raw)
    thumbnail_candidates = [p for p in folder.iterdir() if p.is_file() and p.stem == "thumbnail" and p.suffix.lower() in IMAGE_EXTENSIONS]
    if len(thumbnail_candidates) > 1:
        raise ValueError("Only one optional thumbnail file is allowed")
    duration = _duration_seconds(video_path)
    if dry_run:
        return f"validated {folder.name}: {duration}s, {len(segments)} subtitle segments"

    video_id = uuid.uuid4()
    video_blob = f"videos/{video_id}/{uuid.uuid4().hex}{video_path.suffix.lower()}"
    subtitle_blob = f"subtitles/{video_id}/en/{uuid.uuid4().hex}.srt"
    temporary_thumbnail: Path | None = None
    if thumbnail_candidates:
        thumbnail_path = thumbnail_candidates[0]
        thumbnail_mime = IMAGE_EXTENSIONS[thumbnail_path.suffix.lower()]
    else:
        descriptor, temporary_name = tempfile.mkstemp(prefix="english-video-thumb-", suffix=".jpg")
        os.close(descriptor)
        temporary_thumbnail = Path(temporary_name)
        thumbnail_path = temporary_thumbnail
        thumbnail_mime = "image/jpeg"
        _create_thumbnail(video_path, thumbnail_path)
    thumbnail_blob = f"thumbnails/{video_id}/{uuid.uuid4().hex}{thumbnail_path.suffix.lower()}"
    uploaded: list[tuple[str, str]] = []
    db = SessionLocal()
    try:
        with video_path.open("rb") as handle:
            azure_storage.upload_stream(video_blob, handle, "video", video_mime)
        uploaded.append((video_blob, "video"))
        with thumbnail_path.open("rb") as handle:
            azure_storage.upload_stream(thumbnail_blob, handle, "thumbnail", thumbnail_mime)
        uploaded.append((thumbnail_blob, "thumbnail"))
        azure_storage.upload_stream(subtitle_blob, subtitle_raw, "subtitle", "application/x-subrip")
        uploaded.append((subtitle_blob, "subtitle"))

        video = Video(
            id=video_id, title=metadata["title"].strip(), description=_append_attribution(metadata.get("description"), metadata),
            category=metadata.get("category"), cefr_level=metadata.get("cefr_level"), duration_seconds=duration,
            blob_name=video_blob, thumbnail_blob_name=thumbnail_blob, status="published",
        )
        db.add(video)
        transcript = Transcript(video_id=video_id, language_code="en", format="srt", blob_name=subtitle_blob, is_default=True)
        db.add(transcript)
        db.flush()
        for segment in segments:
            db.add(TranscriptSegment(transcript_id=transcript.id, **segment))
        summary = metadata.get("summary") or {}
        key_points = summary.get("key_points") or []
        if key_points:
            db.add(VideoSummary(video_id=video_id, summary_text=summary.get("summary_text"), key_points=key_points, source="manual"))
        db.commit()
        return f"published {video.id} ({folder.name})"
    except Exception:
        db.rollback()
        for blob_name, resource_type in reversed(uploaded):
            try:
                azure_storage.delete_blob(blob_name, resource_type)  # type: ignore[arg-type]
            except Exception:
                logger.exception("Could not clean up failed import blob: %s", blob_name)
        raise
    finally:
        db.close()
        if temporary_thumbnail:
            temporary_thumbnail.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Import licensed video lessons from the VM inbox")
    parser.add_argument("--limit", type=int, default=settings.video_import_daily_limit)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    limit = min(max(args.limit, 1), settings.video_import_daily_limit)
    inbox = Path(settings.video_import_inbox)
    archive = Path(settings.video_import_archive)
    inbox.mkdir(parents=True, exist_ok=True)
    archive.mkdir(parents=True, exist_ok=True)
    folders = sorted(path for path in inbox.iterdir() if path.is_dir())[:limit]
    if not folders:
        print("No import folders found.")
        return 0
    failures = 0
    for folder in folders:
        try:
            destination = archive / folder.name
            if not args.dry_run and destination.exists():
                raise RuntimeError(f"Archive destination already exists: {destination}")
            print(import_folder(folder, dry_run=args.dry_run))
            if not args.dry_run:
                shutil.move(str(folder), str(destination))
        except Exception as error:
            failures += 1
            logger.exception("Import failed for %s", folder.name)
            print(f"FAILED {folder.name}: {error}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
