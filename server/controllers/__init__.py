"""Registers Flask blueprints and custom URL converters used across the seating application.

This module defines small helper functions that build URL path patterns, three
Werkzeug ``BaseConverter`` subclasses that turn URL segments into database objects
(or redirects) while checking staff versus student permissions, and the blueprint
objects that group related HTTP routes for authentication, development-only login,
and health checks. Importing this module also loads the controller modules so their
routes attach to those blueprints when the application starts.

Attributes:
    GENERAL_STUDENT_HINT: Message appended to HTTP 403 responses when a student hits
        a URL they are not allowed to use, pointing them to course staff for help.
    ban_words, offering_regex, exam_regex, student_regex: Regular expression pieces
        used together to match course, exam, and student segments in pretty URLs
        without colliding with reserved path prefixes like ``new`` or ``exams``.
    auth_module: Blueprint mounted at ``/`` for Canvas login, OAuth callback, and logout.
    dev_login_module: Blueprint under ``/dev_login`` used only when mock Canvas is enabled.
    health_module: Blueprint under ``/health`` for load balancer and monitoring probes.
"""

from server.typings.exception import Redirect
from server.models import SeatAssignment, Student, db, Offering, Exam
from werkzeug.routing import BaseConverter
from flask_login import current_user
from flask import abort, request, session, url_for
from flask import Blueprint


GENERAL_STUDENT_HINT = "If you think this is a mistake, please contact your course staff."

ban_words = r'(?!((new)|(offerings)|(exams)|(student)))'
offering_regex = ban_words + r'\d+'
exam_regex = ban_words + r'\w+'
student_regex = r'\d+'


def format_student_url(offering_canvas_id, exam_name, student_canvas_id):
    """Builds the canonical URL path segment for a single student under a specific exam.

    Args:
        offering_canvas_id: Canvas course identifier (string) for the offering.
        exam_name: Short exam name as stored in the database, used in the URL.
        student_canvas_id: Canvas user id for the student whose profile URL we build.

    Returns:
        A relative path string of the form ``offerings/.../exams/.../students/...``
        with no leading slash, suitable for use inside Flask URL rules.
    """
    return 'offerings/{}/exams/{}/students/{}'.format(offering_canvas_id, exam_name, student_canvas_id)


class StudentConverter(BaseConverter):
    """Converts a pretty student URL into an ``(Exam, Student)`` pair after permission checks.

    Staff may open any student in an exam they manage. Students may only open URLs
    for offerings they are enrolled in; if they are not on the roster for that exam
    the converter aborts with HTTP errors instead of returning a value.

    Attributes:
        regex: Combined regular expression string that ``werkzeug`` uses to decide
            whether a path segment matches this converter before ``to_python`` runs.
    """

    regex = format_student_url(offering_regex, exam_regex, student_regex)

    def to_python(self, value):
        """Parses a matched URL path into the exam and student database rows used by HTML view functions.

        Args:
            value: Full path segment produced by the router, such as
                ``offerings/123/exams/midterm/students/456``.

        Returns:
            A tuple ``(exam, exam_student)`` where ``exam`` is an ``Exam`` model
            instance and ``exam_student`` is the ``Student`` row for that exam.

        Raises:
            Redirect: When the visitor is not logged in; Flask should follow the
                redirect to the login page after storing ``after_login`` in session.
            werkzeug.exceptions.Forbidden: When the user is not staff for this offering
                and not a student enrolled in the offering (HTTP 403).
            werkzeug.exceptions.NotFound: When the student id is not on the exam roster
                or the exam row cannot be resolved (HTTP 404).
        """
        if not current_user.is_authenticated:
            session['after_login'] = request.url
            raise Redirect(url_for('auth.login'))
        _, offering_canvas_id, _, exam_name, _, student_canvas_id = value.split('/', 5)
        exam = Exam.query.filter_by(
            offering_canvas_id=offering_canvas_id, name=exam_name
        ).one_or_none()

        if str(offering_canvas_id) in current_user.staff_offerings:
            pass
        elif str(offering_canvas_id) in current_user.student_offerings:
            abort(403, "You are not authorized to view this page. " + GENERAL_STUDENT_HINT)
        else:
            abort(403, "You are not authorized to view this page. " + GENERAL_STUDENT_HINT)
        exam_student = Student.query.filter_by(
            canvas_id=student_canvas_id, exam_id=exam.id).one_or_none()
        if not exam_student:
            abort(404, "This student is not in this exam. ")
        return exam, exam_student

    def to_url(self, value):
        """Builds the path segment for ``url_for`` when the route argument is ``(Exam, Student)``.

        Args:
            value: Tuple ``(exam, exam_student)`` as returned by ``to_python``.

        Returns:
            Relative path string for that student under the given exam.
        """
        exam, exam_student = value
        rlt = format_student_url(exam.offering_canvas_id, exam.name, exam_student.canvas_id)
        return rlt


def format_exam_url(offering_canvas_id, exam_name):
    """Builds the canonical URL path segment for an exam under a course offering in the seating app.

    Args:
        offering_canvas_id: Canvas course identifier string for the offering.
        exam_name: Exam name as stored in the database, used as the final path piece.

    Returns:
        Relative path of the form ``offerings/<id>/exams/<name>`` without a leading slash.
    """
    return 'offerings/{}/exams/{}'.format(offering_canvas_id, exam_name)


class ExamConverter(BaseConverter):
    """Converts an exam URL into an ``Exam`` model, with special handling for student viewers.

    Staff who manage the offering get the ``Exam`` object directly. Students who visit
    an exam URL are redirected to their own seat page when they are on the roster and
    already have a seat assignment, or receive clear HTTP errors when data is missing.

    Attributes:
        regex: Combined pattern string used by the router to match exam-only URLs
            (paths that do not continue with ``/students/...``).
    """

    regex = format_exam_url(offering_regex, exam_regex + r'(?!/students/\d+)')

    def to_python(self, value):
        """Parses an exam URL path into an ``Exam`` instance or redirects students to their seat.

        Args:
            value: Path segment such as ``offerings/123/exams/final`` produced by the router.

        Returns:
            The ``Exam`` row when the current user is course staff for that offering.

        Raises:
            Redirect: If the user is not logged in (to login), or if the user is a
                student with a valid seat assignment (to their single-seat page).
            werkzeug.exceptions.Forbidden: When the user lacks access or has no assignment.
            werkzeug.exceptions.NotFound: When a student visits an exam that does not exist
                in the seating database yet.
        """
        if not current_user.is_authenticated:
            session['after_login'] = request.url
            raise Redirect(url_for('auth.login'))
        _, canvas_id, _, exam_name = value.split('/', 3)
        exam = Exam.query.filter_by(
            offering_canvas_id=canvas_id, name=exam_name
        ).one_or_none()

        if str(canvas_id) in current_user.staff_offerings:
            pass
        elif str(canvas_id) in current_user.student_offerings:
            if not exam:
                abort(404, "This exam is not initialized for seating. " + GENERAL_STUDENT_HINT)
            exam_student = Student.query.filter_by(
                canvas_id=str(current_user.canvas_id), exam_id=exam.id).one_or_none()
            if not exam_student:
                abort(
                    403, "You are not added as a student in this exam. " + GENERAL_STUDENT_HINT)
            exam_student_seat = SeatAssignment.query.filter_by(
                student_id=exam_student.id).one_or_none()
            if not exam_student_seat:
                abort(403,
                      "You have not been assigned a seat for this exam. " + GENERAL_STUDENT_HINT)
            raise Redirect(url_for('student_single_seat', seat_id=exam_student_seat.seat.id))
        else:
            abort(403, "You are not authorized to view this page. " + GENERAL_STUDENT_HINT)

        return exam

    def to_url(self, exam):
        """Builds the path segment for ``url_for`` from an ``Exam`` model instance for reverse URL lookup.

        Args:
            exam: ``Exam`` object whose offering id and name are encoded into the path.

        Returns:
            Relative URL path string for that exam.
        """
        return format_exam_url(exam.offering_canvas_id, exam.name)


def format_offering_url(canvas_id):
    """Builds the canonical URL path segment for a single course offering by Canvas id.

    Args:
        canvas_id: Canvas course identifier as a string.

    Returns:
        Relative path of the form ``offerings/<canvas_id>`` without a leading slash.
    """
    return "offerings/{}".format(canvas_id)


class OfferingConverter(BaseConverter):
    """Converts an offering URL into an ``Offering`` model after authentication and lookup.

    Attributes:
        regex: Pattern string the router uses to recognize valid offering paths.
    """

    regex = format_offering_url(offering_regex)

    def to_python(self, value):
        """Parses an offering URL into the ``Offering`` row used by list views and staff editing workflows.

        Args:
            value: Path segment such as ``offerings/12345`` from the incoming request.

        Returns:
            The ``Offering`` instance for that Canvas course id.

        Raises:
            Redirect: When the visitor is not logged in, sending them to the login page.
            werkzeug.exceptions.NotFound: When no offering row exists yet for that course.
        """
        if not current_user.is_authenticated:
            session['after_login'] = request.url
            raise Redirect(url_for('auth.login'))
        canvas_id = value.rsplit('/', 1)[-1]

        offering = Offering.query.filter_by(
            canvas_id=canvas_id).one_or_none()
        if not offering:
            abort(404, "This course offering is not initialized for seating. " + GENERAL_STUDENT_HINT)
        return offering

    def to_url(self, offering):
        """Builds the path segment for ``url_for`` from an ``Offering`` model instance for reverse URL lookup.

        Args:
            offering: ``Offering`` whose ``canvas_id`` is turned into a URL segment.

        Returns:
            Relative path string for that offering.
        """
        return format_offering_url(offering.canvas_id)


auth_module = Blueprint('auth', 'auth', url_prefix='/')
dev_login_module = Blueprint('dev_login', 'dev_login', url_prefix='/dev_login')
health_module = Blueprint('health', 'health', url_prefix='/health')
c1c_module = Blueprint('c1c', 'c1c', url_prefix='/c1c')

import server.controllers.auth_controllers  # noqa
import server.controllers.dev_login_controllers  # noqa
import server.controllers.health_controllers  # noqa
