
"""AI-generated docstring: SQLAlchemy models for offerings, exams, rooms, seats, and assignments."""

import itertools
from natsort import natsorted
import re

from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import PrimaryKeyConstraint, types
from sqlalchemy.orm import backref
from sqlalchemy import UniqueConstraint, desc, text
from sqlalchemy.ext.associationproxy import association_proxy

from server import app
from server.utils.date import parse_ISO8601
from server.utils.misc import arr_to_dict, set_to_str

db = SQLAlchemy(app=app)


class StringSet(types.TypeDecorator):
    """AI-generated docstring: Store a Python ``set`` of strings as a comma-separated TEXT column."""

    impl = types.Text

    def process_bind_param(self, value, engine):
        """AI-generated docstring: Serialize a set to comma-separated text for the database."""
        return ','.join(set(value))

    def process_result_value(self, value, engine):
        """AI-generated docstring: Deserialize comma-separated text back into a set of strings."""
        if not value:
            return set()
        else:
            return set(value.split(','))


class User(db.Model, UserMixin):
    """AI-generated docstring: Logged-in Canvas user with staff and student offering lists.

    Attributes:
        id: Primary key.
        name: Display name from Canvas.
        canvas_id: Unique Canvas user id.
        staff_offerings: Set of offering canvas ids where user is staff.
        student_offerings: Set of offering canvas ids where user is a student.
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), index=True, nullable=False)
    canvas_id = db.Column(db.String(255), nullable=False, index=True, unique=True)
    staff_offerings = db.Column(StringSet, nullable=False)
    student_offerings = db.Column(StringSet, nullable=False)


class Offering(db.Model):
    """AI-generated docstring: A course offering imported from Canvas.

    Attributes:
        canvas_id: Unique Canvas course id.
        name: Course title.
        code: Course code string.
        start_at: ISO8601 start date string.
        exams: Related exams for this offering.
    """
    __tablename__ = 'offerings'
    id = db.Column(db.Integer, primary_key=True)
    canvas_id = db.Column(db.String(255), nullable=False, index=True, unique=True)
    name = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(255), nullable=False)
    start_at = db.Column(db.String(255), nullable=False)

    exams = db.relationship('Exam', uselist=True, cascade='all, delete-orphan',
                            order_by='Exam.display_name',
                            backref=backref('offering', uselist=False, single_parent=True))

    @property
    def start_at_date(self):
        """AI-generated docstring: Parse ``start_at`` into a ``datetime`` for display."""
        return parse_ISO8601(self.start_at)

    @property
    def active_exam(self):
        """AI-generated docstring: Return the exam marked active, or ``None`` if none."""
        return next((exam for exam in self.exams if exam.is_active), None)

    def __str__(self):
        return f"{self.start_at_date.strftime('%Y-%m')} | {self.code} | {self.name}"

    def __repr__(self):
        return '<Offering {}>'.format(self.name)

    def mark_all_exams_as_inactive(self):
        """AI-generated docstring: Set ``is_active`` False on every exam in this offering."""
        Exam.query.filter_by(offering_canvas_id=self.canvas_id).update({"is_active": False})

    def ensure_one_exam_is_active(self):
        """AI-generated docstring: Activate the first exam if none are currently active.

        Returns:
            True if an exam was activated, else False or None when there are no exams.
        """
        if not self.exams:
            return
        if not any(exam.is_active for exam in self.exams):
            self.exams[0].is_active = True
            return True
        return False


class Exam(db.Model):
    """AI-generated docstring: One exam session under an offering (rooms, students, seats).

    Attributes:
        offering_canvas_id: Parent offering Canvas id (foreign key).
        name: URL slug for the exam.
        display_name: Human-readable exam title.
        is_active: Whether this is the offering's active exam for students.
    """
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    offering_canvas_id = db.Column(db.ForeignKey(
        'offerings.canvas_id', ondelete='CASCADE'), index=True, nullable=False)
    name = db.Column(db.String(255), nullable=False, index=True)
    display_name = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.BOOLEAN, nullable=False)

    rooms = db.relationship('Room', uselist=True, cascade='all, delete-orphan',
                            order_by=[desc(text('rooms.start_at')), desc(text('rooms.display_name'))],
                            backref=backref('exam', uselist=False, single_parent=True))
    students = db.relationship('Student', uselist=True, cascade='all, delete-orphan',
                               order_by='Student.name',
                               backref=backref('exam', uselist=False, single_parent=True))
    seats = association_proxy('rooms', 'seats')

    __table_args__ = (
        UniqueConstraint('offering_canvas_id', 'name', name='uq_offering_canvas_id_name'),
    )

    @property
    def unassigned_seats(self):
        """AI-generated docstring: Seats in this exam with no ``SeatAssignment`` yet."""
        return [seat for seat in itertools.chain(*self.seats) if seat.assignment == None]  # noqa

    @property
    def unassigned_students(self):
        """AI-generated docstring: Students in this exam without a seat assignment."""
        return [student for student in self.students if student.assignment == None]  # noqa

    def get_assignments(self, emailed=None, limit=None, offset=None):
        """AI-generated docstring: Query seat assignments for this exam with optional filters.

        Args:
            emailed: If set, filter by ``SeatAssignment.emailed``.
            limit: Maximum rows to return.
            offset: Number of rows to skip.

        Returns:
            List of ``SeatAssignment`` rows joined through seat and room.
        """
        query = SeatAssignment.query.join(SeatAssignment.seat).join(Seat.room).filter(
            Room.exam_id == self.id,
        )
        if emailed is not None:
            query = query.filter(SeatAssignment.emailed == emailed)
        if limit is not None:
            query = query.limit(limit)
        if offset is not None:
            query = query.offset(offset)
        return query.all()

    def get_room(self, room_id):
        """AI-generated docstring: Fetch a room belonging to this exam by primary key."""
        return Room.query.filter_by(id=room_id, exam_id=self.id).first()

    def __repr__(self):
        return '<Exam {}>'.format(self.name)


class Room(db.Model):
    """AI-generated docstring: Exam room with schedule metadata and seats.

    Attributes:
        name: URL slug derived from display name.
        display_name: Staff-facing room label.
        start_at: Optional ISO8601 start time string.
        duration_minutes: Optional exam duration in minutes.
        seats: Fixed and movable seats in this room.
    """
    __tablename__ = 'rooms'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.ForeignKey('exams.id', ondelete='CASCADE'), index=True, nullable=False)
    name = db.Column(db.String(255), nullable=False, index=True)
    display_name = db.Column(db.String(255), nullable=False)
    start_at = db.Column(db.String(255))
    duration_minutes = db.Column(db.Integer)

    @property
    def start_at_time(self):
        """AI-generated docstring: Parse ``start_at`` to ``datetime``, or ``None`` if unset."""
        return parse_ISO8601(self.start_at) if self.start_at else None

    def start_at_time_display(self, short=False):
        """AI-generated docstring: Format start time for templates (short or long)."""
        t_format = '%H:%M-%b %d' if short else '%I:%M %p - %b %d, %Y'
        placeholder = "TBA" if short else "Start Time TBA"
        return self.start_at_time.strftime(t_format) if self.start_at else placeholder

    def name_and_start_at_time_display(self, short=False):
        """AI-generated docstring: Combine display name and formatted start time."""
        return f"{self.display_name} ({self.start_at_time_display(short)})"

    @property
    def duration_display(self):
        """AI-generated docstring: Human-readable duration string for templates."""
        return f"{self.duration_minutes} mins" if self.duration_minutes else "Duration TBA"

    seats = db.relationship('Seat', uselist=True, cascade='all, delete-orphan',
                            order_by='Seat.name',
                            backref=backref('room', uselist=False, single_parent=True))

    __table_args__ = (
        UniqueConstraint('exam_id', 'name', 'start_at', name='uq_exam_id_name_start_at'),
    )

    @property
    def fixed_seats(self):
        """AI-generated docstring: Seats with fixed row/column coordinates."""
        return [seat for seat in self.seats if seat.fixed]

    @property
    def movable_seats(self):
        """AI-generated docstring: Seats without fixed coordinates (attribute pools)."""
        return [seat for seat in self.seats if not seat.fixed]

    @property
    def movable_seats_by_attribute(self):
        """AI-generated docstring: Group movable seats by their attribute set."""
        return arr_to_dict(self.movable_seats, key_getter=lambda seat: frozenset(seat.attributes))

    @property
    def rows(self):
        """AI-generated docstring: Fixed seats grouped by row, sorted for room diagram display."""
        seats = natsorted(self.fixed_seats, key=lambda seat: seat.row)
        return [
            natsorted(g, key=lambda seat: seat.x)
            for _, g in itertools.groupby(seats, lambda seat: seat.row)
        ]

    def update_movable_seats(self, new_movable_seats):
        """AI-generated docstring: Replace movable seats while keeping fixed seats unchanged."""
        self.seats = self.fixed_seats + new_movable_seats

    def __repr__(self):
        return '<Room {}>'.format(self.name)


class Seat(db.Model):
    """AI-generated docstring: A seat in a room (fixed layout or movable attribute pool).

    Attributes:
        fixed: True when row/seat coordinates define a named fixed seat.
        name: Seat label (row+seat for fixed seats).
        attributes: Set of preference tags (e.g. Lefty, Aisle).
        assignment: Optional ``SeatAssignment`` for the current exam.
    """
    __tablename__ = 'seats'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.ForeignKey('rooms.id', ondelete='CASCADE'), index=True, nullable=False)
    fixed = db.Column(db.Boolean, default=True, nullable=False)
    name = db.Column(db.String(255))
    row = db.Column(db.String(255))
    seat = db.Column(db.String(255), index=True)
    x = db.Column(db.Float)
    y = db.Column(db.Float)
    attributes = db.Column(StringSet, nullable=False)

    assignment = db.relationship('SeatAssignment', uselist=False, cascade='all, delete-orphan',
                                 backref=backref('seat', uselist=False, single_parent=True))

    @property
    def display_name(self):
        """AI-generated docstring: Fixed seat name or a label for movable attribute seats."""
        return self.name if self.name else f"Movable Seat ({set_to_str(self.attributes)})"

    def __repr__(self):
        return '<Seat {}>'.format(self.display_name)


class Student(db.Model):
    """AI-generated docstring: Student roster row for an exam with seat preferences.

    Attributes:
        canvas_id: Canvas user id (unique per exam).
        wants, avoids: Seat attribute preferences.
        room_wants, room_avoids: Preferred or avoided room ids as strings.
        assignment: Optional seat assignment for this exam.
    """
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.ForeignKey('exams.id', ondelete='CASCADE'), index=True, nullable=False)
    canvas_id = db.Column(db.String(255), nullable=False, index=True)
    email = db.Column(db.String(255), index=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    sid = db.Column(db.String(255))
    wants = db.Column(StringSet, nullable=False)
    avoids = db.Column(StringSet, nullable=False)
    room_wants = db.Column(StringSet, nullable=False)
    room_avoids = db.Column(StringSet, nullable=False)

    assignment = db.relationship('SeatAssignment', uselist=False, cascade='all, delete-orphan',
                                 backref=backref('student', uselist=False, single_parent=True))

    @property
    def first_name(self):
        """AI-generated docstring: Parse first name from ``Last, First`` style ``name`` field."""
        return self.name.rsplit(',', 1)[-1].strip().title()

    def __repr__(self):
        return '<Student {} ({})>'.format(self.name, self.canvas_id)


class SeatAssignment(db.Model):
    """AI-generated docstring: Links one student to one seat for an exam.

    Attributes:
        student_id: Foreign key to ``students``.
        seat_id: Foreign key to ``seats``.
        emailed: Whether the student was notified about this assignment.
    """
    __tablename__ = 'seat_assignments'
    __table_args__ = (
        PrimaryKeyConstraint('student_id', 'seat_id'),
    )
    student_id = db.Column(db.ForeignKey('students.id', ondelete='CASCADE'), index=True, nullable=False)
    seat_id = db.Column(db.ForeignKey('seats.id', ondelete='CASCADE'), index=True, nullable=False)
    emailed = db.Column(db.Boolean, default=False, index=True, nullable=False)


def slug(display_name):
    """AI-generated docstring: Build a URL-safe room or exam slug from a display name.

    Args:
        display_name: Human-readable label from a form.

    Returns:
        Lowercased string with non-alphanumeric characters removed.
    """
    return re.sub(r'[^A-Za-z0-9._-]', '', display_name.lower())
