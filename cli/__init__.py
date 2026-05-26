"""AI-generated docstring: Entry point that registers Flask CLI command modules.

Always loads database commands from ``cli.db``. When ``FLASK_ENV`` is
``development`` or ``testing``, also loads test, lint, and audit commands
from ``cli.qa``.
"""

import cli.db

from config import ConfigBase  # noqa
from server.typings.enum import AppEnvironment

env_value = ConfigBase.getenv('FLASK_ENV').lower()

if env_value == AppEnvironment.DEVELOPMENT.value or \
        env_value == AppEnvironment.TESTING.value:
    import cli.qa
