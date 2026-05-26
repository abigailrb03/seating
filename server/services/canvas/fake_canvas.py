"""AI-generated docstring: Stand-in Canvas API classes backed by local JSON fake data.

``FakeCanvas``, ``FakeUser``, and ``FakeCourse`` mirror the ``canvasapi`` surface the
seating app calls when ``MOCK_CANVAS`` is enabled.
"""

from __future__ import annotations
from datetime import datetime

from server.services.canvas.fake_data import FAKE_USERS, FAKE_COURSES, FAKE_ENROLLMENTS


class FakeCanvas:
    """AI-generated docstring: Minimal Canvas client that loads users and courses from JSON."""

    def __init__(self) -> None:
        """AI-generated docstring: No-op initializer; fake data is loaded at import time."""
        pass

    def get_user(self, canvas_id) -> FakeUser:
        """AI-generated docstring: Return a ``FakeUser`` for the given Canvas user id."""
        return FakeUser(canvas_id)

    def get_course(self, canvas_id) -> FakeCourse:
        """AI-generated docstring: Return a ``FakeCourse`` with enrollments from fake data."""
        return FakeCourse(canvas_id)


class FakeUser:
    """AI-generated docstring: Canvas user fields read from ``FAKE_USERS`` JSON."""

    def __init__(self, canvas_id):
        """AI-generated docstring: Populate identity fields from ``FAKE_USERS`` for ``canvas_id``.

        Args:
            canvas_id: Canvas user id key into ``FAKE_USERS``.
        """
        self.id = canvas_id
        self.name = FAKE_USERS[str(canvas_id)]['name']
        self.short_name = FAKE_USERS[str(canvas_id)]['short_name']
        self.email = FAKE_USERS[str(canvas_id)]['email']
        self.sis_user_id = FAKE_USERS[str(canvas_id)]['sis_user_id']
        self.login_id = FAKE_USERS[str(canvas_id)]['login_id']

    def get_courses(self, *, enrollment_status="active", include=[], per_page=100) -> list[FakeCourse]:
        """AI-generated docstring: List courses the user is enrolled in from fake enrollments.

        Args:
            enrollment_status: Filter enrollments by ``enrollment_state`` (e.g. ``active``).
            include: Ignored; kept for compatibility with ``canvasapi`` signature.
            per_page: Ignored; kept for compatibility with ``canvasapi`` signature.

        Returns:
            List of ``FakeCourse`` objects with enrollment metadata attached.
        """
        dic = FAKE_ENROLLMENTS[str(self.id)]
        return [FakeCourse(course_id, course["enrollments"]) for course_id, course in dic.items() if (
            not enrollment_status or any(
                [e["enrollment_state"] == enrollment_status for e in course["enrollments"]])
        )]


class FakeCourse:
    """AI-generated docstring: Canvas course fields and roster helpers from fake JSON."""

    def __init__(self, canvas_id, enrollments=[]):
        """AI-generated docstring: Load course metadata and optional enrollment list.

        Args:
            canvas_id: Canvas course id key into ``FAKE_COURSES``.
            enrollments: Enrollment dicts attached to this course instance.
        """
        self.id = canvas_id
        self.name = FAKE_COURSES[str(canvas_id)]['name']
        self.course_code = FAKE_COURSES[str(canvas_id)]['course_code']
        self.sis_course_id = FAKE_COURSES[str(canvas_id)]['sis_course_id']
        self.enrollments = enrollments
        # canvasapi.course.Course.start_at is a n ISO8601 date string
        # canvasapi.course.Course.start_at_date is a datetime.datetime object
        # so, we do the same here
        self.start_at = FAKE_COURSES[str(canvas_id)]['start_at']
        self.start_at_date = datetime.strptime(self.start_at, '%Y-%m-%dT%H:%M:%SZ')

    def get_users(self, *, enrollment_type) -> list[FakeUser]:
        """AI-generated docstring: List users enrolled in this course with a given role.

        Scans ``FAKE_ENROLLMENTS`` for users whose enrollment ``type`` matches
        (for example ``student``).

        Args:
            enrollment_type: Canvas enrollment type string to filter on.

        Returns:
            List of ``FakeUser`` instances enrolled in this course with that type.
        """
        users = []
        for user, dic in FAKE_ENROLLMENTS.items():
            if str(self.id) in dic:
                for enrollment in dic[str(self.id)]["enrollments"]:
                    if enrollment["type"] == enrollment_type:
                        users.append(FakeUser(user))
                        break
        return users
