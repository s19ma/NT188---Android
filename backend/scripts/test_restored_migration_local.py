"""Test migration and lock timeout exclusively against the local restored DB."""
import os
import subprocess
import sys
import time
import psycopg
from psycopg import sql

LOCAL = "postgresql://postgres:local_restore_only@127.0.0.1:55432/otp_restore"


def snapshot(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(), version_num FROM alembic_version")
        database, revision = cur.fetchone()
        if database != "otp_restore":
            raise RuntimeError("Wrong migration target")
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        data = {}
        for (table,) in cur.fetchall():
            if table in ("alembic_version", "email_verification_otps", "email_outbox"):
                continue
            cur.execute(sql.SQL("SELECT count(*), md5(coalesce(string_agg(h,'' ORDER BY h),'')) FROM "
                                "(SELECT md5((to_jsonb(t)-'email_verified'-'window_started_at'-'send_count')::text) h "
                                "FROM public.{} t) s").format(sql.Identifier(table)))
            data[table] = cur.fetchone()
        return revision, data


def migrate(lock_seconds):
    env = os.environ.copy()
    env.update(DATABASE_URL=LOCAL, DIRECT_DATABASE_URL=LOCAL, APP_ENVIRONMENT="development",
               EMAIL_DELIVERY_MODE="mock", JWT_SECRET_KEY="local-restore-only",
               AZURE_STORAGE_ACCOUNT_NAME="local-restore", AZURE_STORAGE_ACCOUNT_KEY="local-restore",
               PGOPTIONS=f"-c lock_timeout={lock_seconds}s -c statement_timeout=60s")
    started = time.monotonic()
    result = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "c693a17e4d08"],
                            env=env, capture_output=True, timeout=90)
    return result, time.monotonic() - started


def main():
    with psycopg.connect(LOCAL, connect_timeout=5) as db:
        before_rev, before_data = snapshot(db)
        db.rollback()
        if before_rev != "f31a7c4d2e01":
            raise RuntimeError("Unexpected starting revision")
        db.execute("LOCK TABLE users IN ACCESS SHARE MODE")
        blocked, blocked_time = migrate(2)
        db.rollback()
        if blocked.returncode == 0 or b"lock timeout" not in blocked.stderr.lower():
            raise RuntimeError("Expected lock-timeout test did not behave as expected")
        rev, data = snapshot(db)
        db.rollback()
        if rev != before_rev or data != before_data:
            raise RuntimeError("Lock timeout did not preserve the pre-migration state")
        succeeded, duration = migrate(5)
        if succeeded.returncode:
            raise RuntimeError("Local migration failed")
        after_rev, after_data = snapshot(db)
        if after_rev != "c693a17e4d08" or before_data != after_data:
            raise RuntimeError("Migration changed existing data or revision is wrong")
        with db.cursor() as cur:
            cur.execute("SELECT count(*), count(*) FILTER (WHERE email_verified) FROM users")
            count, verified = cur.fetchone()
            if count != verified:
                raise RuntimeError("Existing accounts are not all marked verified")
            cur.execute("SELECT to_regclass('public.email_outbox') IS NOT NULL, "
                        "to_regclass('public.email_verification_otps') IS NOT NULL")
            if not all(cur.fetchone()):
                raise RuntimeError("Expected new tables are missing")
    print("Lock timeout: expected failure after", round(blocked_time, 2), "seconds; revision and data unchanged")
    print("Migration: success in", round(duration, 2), "seconds; existing table fingerprints unchanged")
    print("Revision:", before_rev, "->", after_rev, "accounts verified:", count)


if __name__ == "__main__":
    main()
