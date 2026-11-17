"""Run separately from the API; no automatic retry of ambiguous SMTP sends."""
import time
from datetime import datetime, timezone
from app.db.database import SessionLocal
from app.services.email_outbox import mark_abandoned, process_one


def main():
    while True:
        try:
            with SessionLocal() as db:
                mark_abandoned(db, datetime.now(timezone.utc))
                processed = process_one(db)
            if not processed: time.sleep(3)
        except Exception:
            # Do not log provider exceptions, payloads, or credentials.
            print("Email worker error; retrying database operation later", flush=True)
            time.sleep(10)


if __name__ == "__main__":
    main()
