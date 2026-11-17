"""Read-only aggregate queue status; never prints addresses or payloads."""
import argparse
from datetime import datetime, timezone
from sqlalchemy import func, select
from app.db.database import SessionLocal
from app.models.email_outbox import EmailOutbox


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit 2 when attention is needed")
    parser.add_argument("--max-pending-seconds", type=int, default=120)
    parser.add_argument("--max-sending-seconds", type=int, default=60)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        rows=db.execute(select(EmailOutbox.status,func.count()).group_by(EmailOutbox.status)).all()
        oldest=db.scalar(select(func.min(EmailOutbox.created_at)).where(EmailOutbox.status=="pending"))
        oldest_sending=db.scalar(select(func.min(EmailOutbox.claimed_at)).where(EmailOutbox.status=="sending"))
        print("Queue counts:", ", ".join(f"{status}={count}" for status,count in rows) or "empty")
        pending_age = max(0, int((now-oldest).total_seconds())) if oldest else 0
        sending_age = max(0, int((now-oldest_sending).total_seconds())) if oldest_sending else 0
        if oldest:
            print("Oldest pending seconds:", pending_age)
        if oldest_sending:
            print("Oldest sending seconds:", sending_age)
        counts = dict(rows)
        needs_attention = (pending_age >= args.max_pending_seconds or
                           sending_age >= args.max_sending_seconds or
                           counts.get("uncertain", 0) > 0 or counts.get("failed", 0) > 0)
        if args.check and needs_attention:
            raise SystemExit(2)


if __name__ == "__main__":
    main()
