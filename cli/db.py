"""AI-generated docstring: Flask CLI commands for creating and seeding the database.

Registered commands: ``flask initdb``, ``flask dropdb``, ``flask seeddb``, and
``flask resetdb`` (drop, init, then seed in one step).
"""

import click

from server.models import db
from server import app
from tests.fixtures import seed_db as _seed_db


@app.cli.command('initdb')
def init_db():
    """TA-written docstring:
    Initializes the database

    AI-generated docstring: Create all SQLAlchemy tables for the current app config."""
    click.echo('Creating database...')
    db.create_all()
    db.session.commit()


@app.cli.command('dropdb')
def drop_db():
    """TA-written docstring:
    Drops all tables from the database

    AI-generated docstring: Prompt for confirmation, then drop every table via SQLAlchemy."""
    doit = click.confirm('Are you sure you want to delete all data?')
    if doit:
        click.echo('Dropping database...')
        db.drop_all()


@app.cli.command('seeddb')
def seed_db():
    """TA-written docstring:
    Seeds the database with data
    There is no need to seed even in development, since the database is
    dynamically populated when app launches, see stub.py

    AI-generated docstring: Load fixture JSON from ``tests/fixtures/`` into the database.

    Useful for local development and tests; production data normally comes from
    Canvas and staff imports rather than this command alone.
    """
    click.echo('Seeding database...')
    _seed_db()


@app.cli.command('resetdb')
@click.pass_context
def reset_db(ctx):
    """TA-written docstring: Drops, initializes, then seeds tables with data

    AI-generated docstring: Run ``dropdb``, ``initdb``, and ``seeddb`` in sequence.

    Args:
        ctx: Click context used to invoke the three subcommands in order.
    """
    ctx.invoke(drop_db)
    ctx.invoke(init_db)
    ctx.invoke(seed_db)
