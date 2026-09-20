import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlmodel import SQLModel

from alembic import context

# backend/ (this file's grandparent) must be on sys.path so `import app...`
# resolves the same way it does when uvicorn runs from backend/ — Alembic
# invokes this file directly, which doesn't automatically get that.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import app.models (not individual model files) so every table is
# registered on SQLModel.metadata before Alembic reads it — the exact same
# concern app/models/__init__.py's own docstring already documents for
# create_all(): a model class that was never imported never registers its
# table, and autogenerate would then silently propose to DROP a real,
# already-migrated table it doesn't know still exists. Reusing that
# existing central-import module rather than re-listing model files here
# separately, per this guide's own "reuse before you build" discipline.
import app.models  # noqa: E402,F401

from app.core.config import settings  # noqa: E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Read DATABASE_URL from the app's own Settings, not alembic.ini's
# sqlalchemy.url or a separately-maintained value — this must always point
# at the exact same database the running app itself uses, per
# WhyPoliceForum_MasterGuide.md M1.1's own explicit requirement. Overrides
# whatever placeholder alembic.ini shipped with.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
