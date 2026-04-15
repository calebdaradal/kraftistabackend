"""add categories tags and featured product support

Revision ID: 20260415_0005
Revises: 20260414_0004
Create Date: 2026-04-15 10:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260415_0005"
down_revision: Union[str, None] = "20260414_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_categories_name"),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )
    op.create_index("ix_categories_name", "categories", ["name"], unique=False)
    op.create_index("ix_categories_slug", "categories", ["slug"], unique=False)

    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_tags_name"),
        sa.UniqueConstraint("slug", name="uq_tags_slug"),
    )
    op.create_index("ix_tags_name", "tags", ["name"], unique=False)
    op.create_index("ix_tags_slug", "tags", ["slug"], unique=False)

    op.add_column("products", sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("products", sa.Column("featured", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_index("ix_products_featured", "products", ["featured"], unique=False)
    op.create_foreign_key("fk_products_category_id_categories", "products", "categories", ["category_id"], ["id"])
    op.create_index("ix_products_category_id", "products", ["category_id"], unique=False)

    op.create_table(
        "product_tags",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("product_id", "tag_id"),
    )

    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute(
        """
        INSERT INTO categories (id, name, slug)
        SELECT gen_random_uuid(), src.name, lower(regexp_replace(trim(src.name), '[^a-zA-Z0-9]+', '-', 'g'))
        FROM (
            SELECT DISTINCT trim(category) AS name
            FROM products
            WHERE category IS NOT NULL AND trim(category) <> ''
        ) AS src
        """
    )
    op.execute(
        """
        UPDATE products p
        SET category_id = c.id
        FROM categories c
        WHERE p.category IS NOT NULL
          AND trim(p.category) <> ''
          AND c.name = trim(p.category)
        """
    )
    op.execute(
        """
        INSERT INTO tags (id, name, slug)
        SELECT gen_random_uuid(), src.name, lower(regexp_replace(trim(src.name), '[^a-zA-Z0-9]+', '-', 'g'))
        FROM (
            SELECT DISTINCT trim(value::text, '"') AS name
            FROM products, jsonb_array_elements_text(coalesce(tags, '[]'::jsonb)) AS value
            WHERE trim(value::text, '"') <> ''
        ) AS src
        ON CONFLICT (name) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO product_tags (product_id, tag_id)
        SELECT DISTINCT p.id, t.id
        FROM products p
        JOIN LATERAL jsonb_array_elements_text(coalesce(p.tags, '[]'::jsonb)) AS tag_value(raw_name) ON true
        JOIN tags t ON t.name = trim(tag_value.raw_name)
        ON CONFLICT DO NOTHING
        """
    )

    op.drop_index("ix_products_category", table_name="products")
    op.drop_column("products", "category")
    op.drop_column("products", "tags")
    op.alter_column("products", "featured", server_default=None)


def downgrade() -> None:
    op.add_column("products", sa.Column("category", sa.String(length=120), nullable=True))
    op.add_column("products", sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.create_index("ix_products_category", "products", ["category"], unique=False)

    op.execute(
        """
        UPDATE products p
        SET category = c.name
        FROM categories c
        WHERE p.category_id = c.id
        """
    )
    op.execute(
        """
        UPDATE products p
        SET tags = sub.tags
        FROM (
            SELECT pt.product_id, jsonb_agg(t.name ORDER BY t.name) AS tags
            FROM product_tags pt
            JOIN tags t ON t.id = pt.tag_id
            GROUP BY pt.product_id
        ) AS sub
        WHERE p.id = sub.product_id
        """
    )

    op.drop_table("product_tags")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_constraint("fk_products_category_id_categories", "products", type_="foreignkey")
    op.drop_index("ix_products_featured", table_name="products")
    op.drop_column("products", "featured")
    op.drop_column("products", "category_id")

    op.drop_index("ix_tags_slug", table_name="tags")
    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_table("tags")

    op.drop_index("ix_categories_slug", table_name="categories")
    op.drop_index("ix_categories_name", table_name="categories")
    op.drop_table("categories")
