"""Strict, small SRT parser used by the admin upload endpoint."""
import srt


def parse_srt(raw: bytes) -> list[dict]:
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("Subtitle must be UTF-8 encoded.") from error
    try:
        items = list(srt.parse(text))
    except Exception as error:
        raise ValueError("Invalid SRT syntax.") from error
    if not items:
        raise ValueError("Subtitle contains no segments.")
    segments = []
    previous_end = -1
    for sequence, item in enumerate(items, start=1):
        start_ms = int(item.start.total_seconds() * 1000)
        end_ms = int(item.end.total_seconds() * 1000)
        content = " ".join(item.content.replace("\r", "").splitlines()).strip()
        if not content or start_ms < 0 or end_ms <= start_ms or start_ms < previous_end:
            raise ValueError("Subtitle timestamps must be ordered and have a positive duration.")
        segments.append({"sequence_number": sequence, "start_ms": start_ms, "end_ms": end_ms, "content": content})
        previous_end = end_ms
    return segments
