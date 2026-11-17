"""Rehearse only against the loopback PostgreSQL restore container."""
import os
import subprocess
import sys
import time
import psycopg
from psycopg import sql

TARGET='postgresql://postgres:local_restore_only@127.0.0.1:55432/otp_restore'


def snapshot(db):
    with db.cursor() as c:
        c.execute('select current_database(), version_num from alembic_version')
        name,revision=c.fetchone()
        if name!='otp_restore': raise RuntimeError('Wrong destination')
        c.execute("select tablename from pg_tables where schemaname='public' and tablename not in ('alembic_version','flashcard_review_requests') order by tablename")
        values={}
        for (table,) in c.fetchall():
            c.execute(sql.SQL("select count(*),md5(coalesce(string_agg(h,'' order by h),'')) from (select md5(row_to_json(t)::text) h from public.{} t) s").format(sql.Identifier(table)))
            values[table]=c.fetchone()
        return revision,values


def upgrade(timeout):
    env=os.environ.copy()
    env.update(DATABASE_URL=TARGET,DIRECT_DATABASE_URL=TARGET,APP_ENVIRONMENT='development',EMAIL_DELIVERY_MODE='disabled',
               JWT_SECRET_KEY='local-only',AZURE_STORAGE_ACCOUNT_NAME='local-only',AZURE_STORAGE_ACCOUNT_KEY='local-only',
               PGOPTIONS=f'-c lock_timeout={timeout}s -c statement_timeout=60s')
    start=time.monotonic()
    r=subprocess.run([sys.executable,'-m','alembic','upgrade','d4e9b137c802'],env=env,capture_output=True,timeout=90)
    return r, round(time.monotonic()-start,2)


def main():
    with psycopg.connect(TARGET,connect_timeout=8) as db:
        rev,before=snapshot(db); db.rollback()
        if rev!='c693a17e4d08': raise RuntimeError('Wrong source revision')
        db.execute('LOCK TABLE users IN ACCESS EXCLUSIVE MODE')
        failed,elapsed=upgrade(2); db.rollback()
        if failed.returncode==0 or b'lock timeout' not in failed.stderr.lower(): raise RuntimeError('Expected lock timeout did not occur')
        after_failure,unchanged=snapshot(db); db.rollback()
        if after_failure!=rev or unchanged!=before: raise RuntimeError('Timeout changed baseline')
        done,duration=upgrade(5)
        if done.returncode: raise RuntimeError('Migration failed')
        after,values=snapshot(db)
        if after!='d4e9b137c802' or values!=before: raise RuntimeError('Existing data changed')
        with db.cursor() as c:
            c.execute("select count(*) from pg_constraint c join pg_class r on r.oid=c.conrelid where r.relname='flashcard_review_requests'")
            print('New table constraints:',c.fetchone()[0])
            c.execute("select indexname from pg_indexes where schemaname='public' and tablename='flashcard_review_requests'")
            print('New table indexes:',[x[0] for x in c.fetchall()])
    print('Lock timeout preserved revision and data:',elapsed,'seconds')
    print('Migration succeeded:',duration,'seconds; existing tables unchanged:',len(before))
    print('Revision:',rev,'->',after)


if __name__=='__main__': main()
