"""Compare the four restored CHECK constraints with explicit sample values."""
from dotenv import dotenv_values
import psycopg
from psycopg import sql
from urllib.parse import urlsplit

LOCAL = "postgresql://postgres:local_restore_only@127.0.0.1:55432/otp_restore"
CHECKS = {
    ("transcripts", "transcripts_format_check"): ("format", ["srt", "vtt", "bad", "SRT", "", None]),
    ("users", "users_cefr_level_check"): ("cefr_level", ["A1", "A2", "B1", "B2", "C1", "C2", "bad", "", None]),
    ("videos", "videos_cefr_level_check"): ("cefr_level", ["A1", "A2", "B1", "B2", "C1", "C2", "bad", "", None]),
    ("videos", "videos_status_check"): ("status", ["draft", "published", "archived", "bad", "", None]),
}


def expression(conn, table, name):
    with conn.cursor() as c:
        c.execute("SELECT pg_get_expr(con.conbin, con.conrelid) FROM pg_constraint con "
                  "JOIN pg_class r ON r.oid=con.conrelid JOIN pg_namespace n ON n.oid=r.relnamespace "
                  "WHERE n.nspname='public' AND r.relname=%s AND con.conname=%s AND con.contype='c'", (table, name))
        row = c.fetchone()
        if not row:
            raise RuntimeError("Expected constraint is missing")
        return row[0]


def values(conn, expr, column, samples):
    query = sql.SQL("SELECT ({}) FROM (SELECT %s::varchar AS {}) AS sample").format(sql.SQL(expr), sql.Identifier(column))
    with conn.cursor() as c:
        result = []
        for sample in samples:
            c.execute(query, (sample,))
            result.append(c.fetchone()[0])
        return result


def main():
    source = dotenv_values('.env')['DIRECT_DATABASE_URL'].replace('postgresql+psycopg://', 'postgresql://')
    p = urlsplit(source)
    if p.hostname != 'ep-icy-lab-a16xdltv.ap-southeast-1.aws.neon.tech' or p.path != '/english_video_db':
        raise RuntimeError('Unexpected source')
    with psycopg.connect(source, options='-c default_transaction_read_only=on') as prod:
        with psycopg.connect(LOCAL, options='-c default_transaction_read_only=on') as restore:
            for (table, name), (column, samples) in CHECKS.items():
                first = values(prod, expression(prod, table, name), column, samples)
                second = values(restore, expression(restore, table, name), column, samples)
                if first != second:
                    raise RuntimeError('Constraint behavior differs: ' + name)
    print('Four CHECK constraints agree on valid, invalid and NULL sample values.')


if __name__ == '__main__':
    main()
