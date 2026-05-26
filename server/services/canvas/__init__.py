"""AI-generated docstring: Canvas API helpers with optional mock mode for local development.

Selects ``FakeCanvas`` or the real ``canvasapi`` client based on ``MOCK_CANVAS``,
fetches users and courses, categorizes enrollments for staff vs student views, and
builds roster rows for student import.
"""

from flask import session, request, url_for
from canvasapi import Canvas
from canvasapi.user import User
from canvasapi.course import Course

from server import app
from server.models import Offering
from server.services.canvas.fake_canvas import FakeCanvas, FakeCourse, FakeUser
from server.typings.exception import Redirect


def is_mock_canvas() -> bool:
    """AI-generated docstring: Return True when fake Canvas data should be used."""
    return app.config['MOCK_CANVAS'] and \
        app.config['FLASK_ENV'].lower() != 'production'


def _get_client(key=None) -> FakeCanvas | Canvas:
    """AI-generated docstring: Return a Canvas or fake client for the current session.

    Args:
        key: OAuth access token; defaults to ``session['access_token']``.

    Returns:
        ``FakeCanvas`` in mock mode, otherwise a ``canvasapi.Canvas`` instance.

    Raises:
        Redirect: When not in mock mode and no access token is in the session.
    """
    if is_mock_canvas():
        return FakeCanvas()
    if not key:
        key = session.get('access_token', None)
    if not key:
        session['after_login'] = request.url
        raise Redirect(url_for('auth.login'))
    return Canvas(app.config['CANVAS_SERVER_URL'], key)


def get_user(canvas_id, key=None) -> FakeUser | User:
    """AI-generated docstring: Fetch a Canvas user by id through the active client."""
    return _get_client(key).get_user(canvas_id)


def get_course(canvas_id, key=None) -> FakeCourse | Course:
    """AI-generated docstring: Fetch a Canvas course by id through the active client."""
    return _get_client(key).get_course(canvas_id)


def is_staff_enrollment(enrollment_type: str):
    """AI-generated docstring: Return True when enrollment type is TA or teacher."""
    return enrollment_type.lower() in ('ta', 'teacher')


def is_course_valid(c) -> bool:
    """AI-generated docstring: Return True when a course has id, name, and course_code."""
    # A valid course has a name, id and course code
    # TODO: TBD if we should filter on published
    return not (not c) and \
        hasattr(c, 'id') and \
        hasattr(c, 'name') and \
        hasattr(c, 'course_code')


def normalize_course_start_date(course: FakeCourse | Course) -> None:
    """AI-generated docstring: Ensure ``start_at`` and ``start_at_date`` are set on a course.

    Prefers term start dates when present; otherwise falls back to course or
    ``created_at`` fields so sorting and display have a consistent date.

    Args:
        course: Canvas or fake course object mutated in place.

    Returns:
        True when ``course.start_at`` is non-null after normalization.
    """
    # Ensure a valid start_at date for a course.
    # return the term start_at_date if present
    # created_at is assumed to be at least always present
    # TODO: does Course ever has `term` attribute? (This is added by Michael's PR)
    # I know there is a `enrollment_term_id` attribute
    if hasattr(course, 'term') and course.term and course.term['start_at']:
        start_at = course.term['start_at']
        start_at_date = course.term['start_at_date']
    else:
        start_at = course.start_at if (hasattr(course, 'start_at') and course.start_at) else course.created_at
        start_at_date = course.start_at_date if (hasattr(course, 'start_at_date')
                                                 and course.start_at_date) else course.created_at_date
    course.start_at = start_at
    course.start_at_date = start_at_date
    return course.start_at is not None


def get_user_courses_categorized(user: FakeUser | User) \
        -> tuple[list[FakeCourse | Course], list[FakeCourse | Course], list[FakeCourse | Course]]:
    """AI-generated docstring: Split a user's active courses into staff, student, and other lists.

    Skips invalid courses, normalizes start dates, deduplicates categories (staff wins
    over student), and sorts each list by ``start_at_date`` descending then name ascending.

    Args:
        user: Canvas or fake user whose enrollments are fetched.

    Returns:
        Tuple ``(staff_courses, student_courses, other_courses, skipped_courses)`` as lists.
    """
    courses_raw = user.get_courses(enrollment_status='active', include=['term'], per_page=100)
    # TODO: Refactor to a dict { staff:, student:, other: }
    staff_courses, student_courses, other, skipped = set(), set(), set(), set()
    for c in courses_raw:
        if not is_course_valid(c) or not normalize_course_start_date(c):
            skipped.add(c)
            continue
        # TODO: refactor to function `find_course_enrollment_type`
        for e in c.enrollments:
            if is_staff_enrollment(e["type"]):
                staff_courses.add(c)
            elif e["type"] == 'student':
                student_courses.add(c)
            else:
                other.add(c)

    # a course should not appear in more than one category
    student_courses -= set(staff_courses)
    other = other - set(staff_courses) - set(student_courses)

    # convert to list because order matters
    staff_courses: list[FakeCourse | Course] = list(staff_courses)
    student_courses: list[FakeCourse | Course] = list(student_courses)
    other: list[FakeCourse | Course] = list(other)

    # sorted by start_at_date DESC and then by name ASC
    def _sort_courses(courses: list[FakeCourse | Course]):
        # Cannot do courses.sort(key=lambda c: (c.start_at_date, c.name))
        # String or Datetime object cannot be negated to reverse the order
        courses.sort(key=lambda c: c.name)
        courses.sort(key=lambda c: c.start_at_date, reverse=True)

    _sort_courses(staff_courses)
    _sort_courses(student_courses)
    _sort_courses(other)

    return list(staff_courses), list(student_courses), list(other), list(skipped)


def get_student_roster_for_offering(offering_canvas_id, key=None):
    """AI-generated docstring: Build import-ready roster rows from a Canvas course.

    Args:
        offering_canvas_id: Canvas course id for the offering.
        key: Optional OAuth token; uses session token when omitted.

    Returns:
        Tuple ``(headers, rows)`` where ``headers`` is a fixed column list and each row
        is a dict with canvas id, email, name, and student id when available.
    """
    course = _get_client(key).get_course(offering_canvas_id)
    students = course.get_users(enrollment_type='student')
    headers = ['canvas id', 'email', 'name', 'student id']
    rows = []
    for student in students:
        stu_dict = {}
        if hasattr(student, 'id'):
            stu_dict['canvas id'] = student.id
        if hasattr(student, 'email'):
            stu_dict['email'] = student.email
        if hasattr(student, 'short_name'):
            stu_dict['name'] = student.short_name
        if hasattr(student, 'sis_user_id'):
            stu_dict['student id'] = student.sis_user_id
        rows.append(stu_dict)
    return headers, rows


def api_course_to_model(course: Course | FakeCourse) -> Offering:
    """AI-generated docstring: Map a Canvas course object to an unsaved ``Offering`` model."""
    return Offering(
        canvas_id=str(course.id),
        name=course.name,
        code=course.course_code,
        start_at=course.start_at,
    )
