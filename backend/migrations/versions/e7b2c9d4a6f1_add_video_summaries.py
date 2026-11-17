"""add video summaries

Revision ID: e7b2c9d4a6f1
Revises: d1e4f8a9b2c3
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e7b2c9d4a6f1"
down_revision = "d1e4f8a9b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_summaries",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("video_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("summary_text", sa.Text(), nullable=True),
        sa.Column("key_points", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("source", sa.Text(), server_default="manual", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id"),
    )
    # Seed only the three existing public lessons. New videos receive their own summary via the admin endpoint.
    op.execute("""
        INSERT INTO video_summaries (video_id, summary_text, key_points, source)
        SELECT id,
          'Muối là một khoáng chất thiết yếu đã ảnh hưởng đến sức khỏe, bảo quản thực phẩm, thương mại và môi trường.',
          '["Vai trò thiết yếu: Muối cung cấp sodium cần cho cơ thể và từng là một tài nguyên rất quý.", "Dấu ấn trong lịch sử: Việc khai thác, bảo quản thực phẩm và buôn bán muối đã tác động đến nhiều xã hội.", "Tác động ngày nay: Khi muối xuất hiện quá nhiều trong tự nhiên, nó cũng có thể làm thay đổi hệ sinh thái."]'::jsonb,
          'manual'
        FROM videos WHERE lower(title) LIKE '%salt%'
        ON CONFLICT (video_id) DO NOTHING;
    """)
    op.execute("""
        INSERT INTO video_summaries (video_id, summary_text, key_points, source)
        SELECT id,
          'Hạt tiêu đi từ một loại gia vị quý ở Nam Á thành sản phẩm phổ biến nhờ các tuyến thương mại toàn cầu.',
          '["Nguồn gốc của hạt tiêu: Hạt tiêu từng được trồng chủ yếu ở Nam Á và trở thành một loại gia vị được săn đón.", "Hành trình thương mại: Nhu cầu về tiêu đã kết nối các tuyến thương mại xa xôi và ảnh hưởng đến lịch sử thế giới.", "Gia vị quen thuộc: Từ món ăn sang trọng trong quá khứ, tiêu dần trở thành gia vị phổ biến trên bàn ăn hiện nay."]'::jsonb,
          'manual'
        FROM videos WHERE lower(title) LIKE '%pepper%'
        ON CONFLICT (video_id) DO NOTHING;
    """)
    op.execute("""
        INSERT INTO video_summaries (video_id, summary_text, key_points, source)
        SELECT id,
          'Visual hiệu quả làm rõ thông điệp, giảm chi tiết gây nhiễu và hướng sự chú ý của khán giả.',
          '["Hình ảnh cần có mục đích: Visual tốt giúp người xem hiểu thông điệp, thay vì chỉ làm slide trông đẹp hơn.", "Giảm phần gây nhiễu: Chọn hình ảnh rõ ràng, ít chi tiết thừa và để nội dung nói hỗ trợ lẫn nhau.", "Dẫn dắt sự chú ý: Đặt visual đúng lúc để khán giả tập trung vào ý chính mà người nói đang trình bày."]'::jsonb,
          'manual'
        FROM videos WHERE lower(title) LIKE '%visual%' OR lower(title) LIKE '%presentation%'
        ON CONFLICT (video_id) DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_table("video_summaries")
