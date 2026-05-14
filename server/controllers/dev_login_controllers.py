"""Development-only routes that emulate Canvas OAuth when ``MOCK_CANVAS`` is enabled in configuration.

This module exposes a simple HTML form for picking a fake user id, minimal ``/oauth2/auth``
and ``/oauth2/token`` endpoints that behave enough like Canvas for local testing without
real API keys, and glue that reuses the same ``auth.authorized`` callback as production so
student and staff flows stay aligned across environments.

These endpoints must never be relied on in production deployments where ``MOCK_CANVAS`` is
false, because unauthenticated visitors are immediately redirected back to the public index.
"""

from flask import request, jsonify, abort, redirect, url_for, render_template
import server.services.canvas as canvas_client

from server.controllers import dev_login_module
from server.services.auth import oauth_provider
from server.services.canvas.fake_data import FAKE_USERS


@dev_login_module.route('/', methods=['GET', 'POST'])
def dev_login_page():
    """Renders the mock user picker form or redirects visitors away when Canvas is not mocked.

    Returns:
        An HTML page with ``DevLoginForm`` when ``MOCK_CANVAS`` is true, an HTTP redirect
        into the fake OAuth authorize step after a valid POST, an HTTP 500 if the submitted
        user id is empty, or a redirect to the main index when mock mode is disabled so the
        URL cannot be abused on production-like servers.
    """
    if canvas_client.is_mock_canvas():
        available_mock_users = [(id, user['name']) for id, user in FAKE_USERS.items()]
        from server.forms import DevLoginForm
        form = DevLoginForm()
        if form.validate_on_submit():
            if form.user_id.data:
                return oauth_provider.authorize(
                    callback=url_for('auth.authorized'),
                    state=None,
                    user_id=form.user_id.data,
                    _external=True, _scheme="http")
            else:
                abort(500, 'Invalid dev user')
        return render_template('dev_login.html.j2', available_mock_users=available_mock_users, form=form, title="Dev Login")
    return redirect(url_for('index'))


@dev_login_module.route('/oauth2/auth/', methods=['GET'])
def mock_authorize():
    """Imitates Canvas's authorization redirect by appending a fake ``code`` and ``state`` query pair.

    Returns:
        An HTTP 302 redirect whose ``Location`` header points at the ``redirect_uri`` query
        parameter supplied by Flask-OAuthlib, with ``code`` set to the chosen mock user id.

    Raises:
        werkzeug.exceptions.BadRequest: When ``redirect_uri`` is missing from the query string
            so the OAuth client cannot complete its state machine safely.
    """
    redirect_uri = request.args.get('redirect_uri', None)
    state = request.args.get('state', '')
    user_id = request.args.get('user_id', None)
    if redirect_uri:
        sep = '&' if '?' in redirect_uri else '?'
        full_redirect_uri = \
            f"{redirect_uri}{sep}code={user_id}&state={state}"
        return redirect(full_redirect_uri)
    else:
        abort(400, 'Invalid redirect_uri: {}'.format(redirect_uri))


@dev_login_module.route('/oauth2/token/', methods=['POST'])
def mock_token():
    """Returns a canned JSON access-token payload that mirrors Canvas's token endpoint shape for tests.

    Returns:
        A Flask ``jsonify`` response whose body includes ``access_token``, ``user`` metadata
        from ``FAKE_USERS``, and dummy refresh fields so ``oauth_provider.authorized_response``
        can deserialize the structure exactly like a real Canvas response.

    Raises:
        werkzeug.exceptions.BadRequest: When the ``code`` form field is missing, because the
            mock authorization step did not supply a user id to embed in the token response.
    """
    user_id = request.form.get('code')
    if not user_id:
        abort(400, 'Invalid dev user')

    mock_response = {
        'access_token': 'dev_access_token',
        'token_type': 'Bearer',
        'user': FAKE_USERS[str(user_id)],
        'canvas_region': 'us-east-1',
        'refresh_token': 'dev_refresh_token',
        'expires_in': 3600
    }
    return jsonify(mock_response)
