"""AI-generated docstring: Lightweight JSON endpoints under ``/health`` used by operators to confirm uptime and observability.

This module exposes three read-only routes: a trivial process heartbeat, a database ``SELECT 1``
smoke test that catches connection or migration issues early, and a logging probe that emits
sample messages at every standard log level so centralized log pipelines can be validated
without authenticating as a Canvas user.

These routes are intentionally simple so load balancers, Kubernetes probes, and on-call
engineers can curl them quickly without understanding the rest of the seating domain model.
"""

from flask import jsonify, current_app

from server.controllers import health_module


@health_module.route('/')
def check():
    """AI-generated docstring: Reports that the Python process is running and able to answer HTTP requests on this prefix.

    Returns:
        A tuple ``(json_response, status_code)`` where the JSON body is ``{"status": "UP"}``
        and the HTTP status code is ``200`` for success.
    """
    return jsonify(status="UP"), 200


@health_module.route('/db')
def check_db():
    """AI-generated docstring: Runs a trivial SQL statement through SQLAlchemy to verify the application database is reachable.

    Returns:
        ``(jsonify({"status": "UP"}), 200)`` when ``SELECT 1`` executes without error, or
        ``(jsonify({"status": "DOWN", "error": ...}), 500)`` when any exception is raised so
        operators can see the driver message in JSON form.
    """
    from server.models import db
    try:
        db.session.execute("SELECT 1")
        return jsonify(status="UP"), 200
    except Exception as e:
        return jsonify(status="DOWN", error=str(e)), 500


@health_module.route('/log')
def check_logging():
    """AI-generated docstring: Emits one log record at each built-in severity level to prove logging configuration works.

    Returns:
        A tuple ``(jsonify({"status": "SEE LOGS"}), 200)`` after ``debug``, ``info``,
        ``warning``, and ``error`` messages are written through ``current_app.logger``.
    """
    current_app.logger.debug("Debug logging is working")
    current_app.logger.info("Info logging is working")
    current_app.logger.warning("Warning logging is working")
    current_app.logger.error("Error logging is working")
    return jsonify(status="SEE LOGS"), 200
