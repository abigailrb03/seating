"""AI-generated docstring: Flask application factory and startup wiring for the seating app.

Creates the ``app`` instance, loads config from ``FLASK_ENV``, registers URL converters,
blueprints, CLI commands, Sentry, and side-effect imports for auth, cache, and routes.
"""

from flask import Flask, redirect
import logging
import flask.ctx
from werkzeug.exceptions import HTTPException
from canvasapi.exceptions import InvalidAccessToken

from server.typings.enum import AppEnvironment
from server.typings.exception import EnvironmentalVariableMissingError


class UrlRequestContext(flask.ctx.RequestContext):
    """AI-generated docstring: Request context that matches URLs without dispatching a view."""

    def match_request(self):
        """AI-generated docstring: Skip default view matching (used for URL generation only)."""
        pass

    def push(self):
        """AI-generated docstring: Match the URL rule and store ``view_args`` on the request."""
        super().push()
        try:
            url_rule, self.request.view_args = \
                self.url_adapter.match(return_rule=True)
            self.request.url_rule = url_rule
        except HTTPException as e:
            self.request.routing_exception = e


class App(Flask):
    """AI-generated docstring: Flask subclass that uses ``UrlRequestContext`` for ``url_for``."""

    def request_context(self, environ):
        """AI-generated docstring: Build a ``UrlRequestContext`` instead of the default context."""
        return UrlRequestContext(self, environ)


import sentry_sdk  # noqa

sentry_sdk.init(
    dsn="https://bb1482ed49f0807ee6a49accafe927f9@o4506322522734592.ingest.sentry.io/4506322540953600",
    # Set traces_sample_rate to 1.0 to capture 100%
    # of transactions for performance monitoring.
    traces_sample_rate=1.0,
    # Set profiles_sample_rate to 1.0 to profile 100%
    # of sampled transactions.
    # We recommend adjusting this value in production.
    profiles_sample_rate=1.0,
)

app = App(__name__)


if __name__ != '__main__':
    # Only configure logging if running on a WSGI server, like gunicorn on Heroku
    app.logger.addHandler(logging.StreamHandler())
    app.logger.setLevel(logging.INFO)


from config import ConfigBase, ProductionConfig, StagingConfig, DevelopmentConfig, TestingConfig  # noqa
env_value = ConfigBase.getenv('FLASK_ENV').lower()

config_mapping = {
    AppEnvironment.PRODUCTION.value: ProductionConfig,
    AppEnvironment.TESTING.value: TestingConfig,
    AppEnvironment.STAGING.value: StagingConfig,
    AppEnvironment.DEVELOPMENT.value: DevelopmentConfig,
}

selected_config_class = config_mapping.get(env_value, None)

if selected_config_class:
    app.config.from_object(selected_config_class())
else:
    raise EnvironmentalVariableMissingError('FLASK_ENV')


@app.errorhandler(InvalidAccessToken)
def handle_invalid_access_token(e):
    """TA-written docstring:
    Redirects to login page if the Canvas access token is invalid or expired.

    AI-generated docstring: Send the user back to login when Canvas rejects the token.

    Args:
        e: ``InvalidAccessToken`` from the Canvas API client.

    Returns:
        werkzeug Response redirecting to ``/login``.
    """
    return redirect('/login')


app.jinja_env.filters.update(
    min=min,
    max=max,
)


# These must be done after `app`` is created as they depend on `app`

# prepare server cache
import server.cache  # noqa

# prepares all auth clients
import server.services.auth  # noqa

# prepares mock canvas db
import server.services.canvas.fake_data  # noqa

# registers controller converters
from server.controllers import ExamConverter, OfferingConverter, StudentConverter  # noqa
app.url_map.converters['exam_student'] = StudentConverter
app.url_map.converters['exam'] = ExamConverter
app.url_map.converters['offering'] = OfferingConverter

# registers base controllers (depends on converters, so must be done after)
import server.views  # noqa

# registers blueprint controllers
from server.controllers import auth_module, dev_login_module, health_module  # noqa
app.register_blueprint(dev_login_module)
app.register_blueprint(auth_module)
app.register_blueprint(health_module)

# registers flask cli commands
import cli  # noqa
