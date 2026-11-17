from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from app.models.user import User
from app.models.video_summary import VideoSummary


def test_email_index_uses_column_expression():
    index = next(i for i in User.__table__.indexes if i.name == 'uq_users_email_lower')
    sql = str(CreateIndex(index).compile(dialect=postgresql.dialect()))
    assert 'lower(email)' in sql
    assert "lower('email')" not in sql


def test_video_summary_json_default_is_sql_expression():
    sql = str(CreateTable(VideoSummary.__table__).compile(dialect=postgresql.dialect()))
    assert "DEFAULT '[]'::jsonb" in sql
