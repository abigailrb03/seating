"""HTTP routes for real Canvas OAuth login, the OAuth callback, and logging out of the seating app.

This module registers view functions on the ``auth`` blueprint: ``/login/`` starts the
Canvas authorization flow (or redirects to the mock dev login page when ``MOCK_CANVAS`` is
true), ``/authorized/`` exchanges the authorization code for tokens and syncs the local
``User`` row, and ``/logout/`` clears the session for staff and students who share browsers
in instructional labs.

These routes are the production path for authentication; local HTTPS callback URLs must
match the redirect URI registered with your Canvas API developer key.
"""

from flask import redirect, request, session, url_for
from flask_login import login_user, logout_user, login_required
import server.services.canvas as canvas_client

from server.models import db, User

from server.controllers import auth_module
from server.services.auth import oauth_provider


@auth_module.route('/login/')
def login():
    """Starts Canvas OAuth for signed-out visitors, or sends mock-mode users to the dev login screen.

    Returns:
        A werkzeug ``Response`` that is either an HTTP redirect to the development login
        blueprint when ``MOCK_CANVAS`` is enabled, or the redirect produced by
        ``oauth_provider.authorize`` toward Canvas's authorization endpoint when using
        the real integration.
    """
    if canvas_client.is_mock_canvas():
        return redirect(url_for('dev_login.dev_login_page'))
    return oauth_provider.authorize(
        callback=url_for('auth.authorized', state=None, _external=True, _scheme="https"))


@auth_module.route('/authorized/')
def authorized():
    """Completes the OAuth handshake, persists Canvas-derived course lists, and logs the user in.

    Canvas redirects the browser here after the user approves access. This view reads the
    token response, fetches the Canvas user and active course enrollments, updates or
    inserts the matching ``User`` row in SQLite or Postgres, and finally issues a Flask-Login
    session cookie before redirecting back to the originally requested page or the home index.

    Returns:
        On success, an HTTP redirect to ``session['after_login']`` if it was set earlier,
        otherwise a redirect to the application index. On denial, a short plain-text error
        body describing Canvas's error parameter.
    """
    resp = oauth_provider.authorized_response()
    if resp is None:
        return 'Access denied: {}'.format(request.args.get('error', 'unknown error'))
    session['access_token'] = resp['access_token']
    user_info = resp['user']

    user = canvas_client.get_user(user_info['id'])
    staff_course_dics, student_course_dics, _, _ = canvas_client.get_user_courses_categorized(user)
    staff_offerings = [str(c.id) for c in staff_course_dics]
    student_offerings = [str(c.id) for c in student_course_dics]

    user_model = User.query.filter_by(canvas_id=str(user_info['id'])).one_or_none()
    if not user_model:
        user_model = User(
            name=user_info['name'],
            canvas_id=str(user_info['id']),
            staff_offerings=staff_offerings,
            student_offerings=student_offerings)
        db.session.add(user_model)
    else:
        user_model.staff_offerings = staff_offerings
        user_model.student_offerings = student_offerings
    db.session.commit()

    login_user(user_model, remember=True)
    after_login = session.pop('after_login', None) or url_for('index')
    return redirect(after_login)


@auth_module.route('/logout/')
@login_required
def logout():
    """Clears the Flask session and Flask-Login state so the current browser is fully signed out.

    Returns:
        An HTTP redirect response to the public index route after ``session.clear()`` and
        ``logout_user()`` run successfully for an authenticated user.
    """
    session.clear()
    logout_user()
    return redirect(url_for('index'))
