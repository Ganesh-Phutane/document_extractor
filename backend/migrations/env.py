"""
migrations/env.py
──────────────────
Alembic environment — wired to our SQLAlchemy models and config.
Reads DATABASE_URL from backend/.env via core/config.py
"""
import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Make sure backend/ is on sys.path ────────────────────────
# So Alembic can import core.config, models, etc.
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# ── Import our settings + Base + all ORM models ──────────────
from core.config import settings
from core.database import Base
import models  # noqa — This import populates Base.metadata with all tables

# Alembic config object
config = context.config

# Set DB URL from our .env (overrides any value in alembic.ini)
# Escape % to %% because Alembic's ConfigParser uses % for interpolation
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))


# Set up logging as configured in alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL only, no live connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (live DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,          # Detect column type changes
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
