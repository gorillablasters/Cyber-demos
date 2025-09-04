from __future__ import with_statement
from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from alembic import context
import os
import sys

# Ensure app is on path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.db import Base
from app import models  # ensures models are imported so Alembic sees them
from app.config import settings

# Alembic Config object
config = context.config

# Replace sqlalchemy.url in alembic.ini with env DATABASE_URL
section = config.config_ini_section
config.set_section_option(section, "DATABASE_URL", settings.DATABASE_URL)

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata
target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=settings.DATABASE_URL, target_metadata=target_metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = create_engine(settings.DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
