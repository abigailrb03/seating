"""AI-generated docstring: Flask-Login and Canvas OAuth wiring for the seating app.

Configures ``login_manager`` and ``oauth_provider`` for real Canvas or mock dev OAuth
(when ``MOCK_CANVAS`` is true). Registers token and user session callbacks used on
every authenticated request.
"""

from flask import redirect, request, session, url_for

import server.services.canvas as canvas_client
from flask_login import LoginManager
from flask_oauthlib.client import OAuth
from .scope import scopes

from server import app

login_manager = LoginManager(app=app)

oauth = OAuth()

canvas_server_url = app.config.get('CANVAS_SERVER_URL')
consumer_key = app.config.get('CANVAS_CLIENT_ID')
consumer_secret = app.config.get('CANVAS_CLIENT_SECRET')
dev_oauth_server_url = app.config.get('SERVER_BASE_URL')

oauth_provider = None

if not canvas_client.is_mock_canvas():
    oauth_provider = oauth.remote_app(
        'seating',
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        base_url=canvas_server_url,
        request_token_url=None,
        access_token_method='POST',
        access_token_url=canvas_server_url + 'login/oauth2/token',
        authorize_url=canvas_server_url + 'login/oauth2/auth',
        request_token_params={'scope': ' '.join(scopes)},
    )
else:
    # dev login uses HTTP so we need to allow that for OAuth2
    import os
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    oauth_provider = oauth.remote_app(
        'seating_dev',
        consumer_key='development_key',
        consumer_secret='development_secret',
        base_url=dev_oauth_server_url,
        request_token_url=None,
        access_token_method='POST',
        access_token_url=dev_oauth_server_url + 'dev_login/oauth2/token/',
        authorize_url=dev_oauth_server_url + 'dev_login/oauth2/auth/',
    )


@oauth_provider.tokengetter
def get_access_token(token=None):
    """AI-generated docstring: Return the Canvas access token stored in the Flask session."""
    return session.get('access_token')


@login_manager.user_loader
def load_user(user_id):
    """AI-generated docstring: Load a ``User`` row by primary key for Flask-Login.

    Args:
        user_id: String user id from the session cookie.

    Returns:
        ``User`` model instance, or ``None`` if the id is invalid.
    """
    from server.models import User
    return User.query.get(user_id)


@login_manager.unauthorized_handler
def unauthorized():
    """AI-generated docstring: Redirect anonymous users to login and save the target URL.

    Stores ``request.url`` in ``session['after_login']`` so OAuth can return the user
    to the page they originally requested.

    Returns:
        werkzeug Response redirecting to ``auth.login``.
    """
    session['after_login'] = request.url
    return redirect(url_for('auth.login'))
