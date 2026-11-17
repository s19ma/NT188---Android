"""Compare aggregate data fingerprints; never print row data or credentials."""
from urllib.parse import urlsplit
from dotenv import dotenv_values
import psycopg
from psycopg import sql

LOCAL = "postgresql://postgres:local_restore_only@127.0.0.1:55432/otp_restore"
SOURCE_HOST = "ep-icy-lab-a16xdltv.ap-southeast-1.aws.neon.tech"


def inspect(conn):
    with conn.cursor() as cur:
        cur.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
        cur.execute("SELECT current_database(), current_setting('transaction_read_only')")
        db, readonly = cur.fetchone()
        if readonly != "on":
            raise RuntimeError("Read-only transaction is required")
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        tables = [row[0] for row in cur.fetchall()]
        data = {}
        for table in tables:
            cur.execute(sql.SQL("SELECT count(*), md5(coalesce(string_agg(h, '' ORDER BY h), '')) "
                                "FROM (SELECT md5(row_to_json(t)::text) AS h FROM public.{} t) s")
                        .format(sql.Identifier(table)))
            data[table] = cur.fetchone()
        cur.execute("SELECT table_name,column_name,data_type,udt_name,is_nullable,column_default "
                    "FROM information_schema.columns WHERE table_schema='public' ORDER BY table_name,ordinal_position")
        columns = cur.fetchall()
        cur.execute("SELECT tablename,indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY tablename,indexname")
        indexes = cur.fetchall()
        cur.execute("SELECT rel.relname, con.conname, pg_get_constraintdef(con.oid) "
                    "FROM pg_constraint con JOIN pg_class rel ON rel.oid=con.conrelid "
                    "JOIN pg_namespace n ON n.oid=rel.relnamespace WHERE n.nspname='public' "
                    "ORDER BY rel.relname,con.conname")
        constraints = cur.fetchall()
        cur.execute("SELECT version_num FROM alembic_version")
        return db, data, columns, indexes, constraints, cur.fetchone()[0]


def constraints_equivalent(prod, restored, original, clone):
    """Prove the known array-cast rewrites; reject any other difference."""
    old = {(table, name): definition for table, name, definition in original}
    new = {(table, name): definition for table, name, definition in clone}
    if old.keys() != new.keys():
        return False
    known = {
        ("transcripts", "transcripts_format_check"): ("format", ["srt", "vtt"]),
        ("users", "users_cefr_level_check"): ("cefr_level", ["A1", "A2", "B1", "B2", "C1", "C2"]),
        ("videos", "videos_cefr_level_check"): ("cefr_level", ["A1", "A2", "B1", "B2", "C1", "C2"]),
        ("videos", "videos_status_check"): ("status", ["draft", "published", "archived"]),
    }
    for identity in old:
        if old[identity] == new[identity]:
            continue
        if identity not in known:
            return False
        column, values = known[identity]
        source_items = ", ".join("'%s'::character varying" % v for v in values)
        restore_items = ", ".join("('%s'::character varying)::text" % v for v in values)
        source_expression = f"CHECK ((({column})::text = ANY ((ARRAY[{source_items}])::text[])))"
        restore_expression = f"CHECK ((({column})::text = ANY (ARRAY[{restore_items}])))"
        if old[identity] != source_expression or new[identity] != restore_expression:
            return False
        # Both predicates have the same left side; establish equality of their
        # constant arrays on both servers, which also preserves ANY/NULL results.
        for conn in (prod, restored):
            with conn.cursor() as cur:
                cur.execute(f"SELECT ((ARRAY[{source_items}])::text[]) IS NOT DISTINCT FROM ARRAY[{restore_items}]")
                if not cur.fetchone()[0]:
                    return False
    return True


def main():
    source = dotenv_values(".env")["DIRECT_DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://")
    url = urlsplit(source)
    if url.hostname != SOURCE_HOST or url.path != "/english_video_db":
        raise RuntimeError("Unexpected production source")
    with psycopg.connect(source, connect_timeout=10, options="-c default_transaction_read_only=on") as prod:
        with psycopg.connect(LOCAL, connect_timeout=10, options="-c default_transaction_read_only=on") as restored:
            source_db, original, original_columns, original_indexes, original_constraints, original_rev = inspect(prod)
            target_db, clone, clone_columns, clone_indexes, clone_constraints, clone_rev = inspect(restored)
            constraints_match = constraints_equivalent(prod, restored, original_constraints, clone_constraints)
    if source_db != "english_video_db" or target_db != "otp_restore":
        raise RuntimeError("Unexpected database identity")
    mismatches = [table for table in set(original) | set(clone) if original.get(table) != clone.get(table)]
    print("Tables compared:", len(original), "data mismatches:", len(mismatches))
    print("Column metadata matches:", original_columns == clone_columns)
    print("Indexes match:", original_indexes == clone_indexes, "constraints equivalent:", constraints_match)
    print("Revisions:", original_rev, clone_rev)
    print("Accounts:", original.get("users", (None,))[0], clone.get("users", (None,))[0])
    if (mismatches or original_columns != clone_columns or original_indexes != clone_indexes
            or not constraints_match or original_rev != clone_rev):
        raise RuntimeError("Restore does not match the current source snapshot")


if __name__ == "__main__":
    main()
