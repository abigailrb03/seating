"""AI-generated docstring: Seat assignment helpers that match students to seats by preference.

Groups students and seats by seat/room preferences, runs a greedy assignment strategy for
bulk assigns, and supports assigning one student at a time with optional overrides.
"""

import random

from server.models import Seat, SeatAssignment, Student
from server.typings.exception import NotEnoughSeatError, SeatOverrideError
from server.utils.misc import arr_to_dict


class Preference:
    """AI-generated docstring: Hashable bundle of seat and room wants/avoids for one student.

    Used as a dictionary key when grouping students and seats during bulk assignment.

    Attributes:
        wants: Seat attribute names the student prefers (all must match).
        avoids: Seat attribute names the student refuses.
        room_wants: Room ids the student prefers; empty means any room is acceptable.
        room_avoids: Room ids the student refuses.
    """

    def __init__(self, wants: set[str], avoids: set[str], room_wants: set[str], room_avoids: set[str]):
        """AI-generated docstring: Store the four preference sets used for seat matching.

        Args:
            wants: Seat attributes the student requires on their seat.
            avoids: Seat attributes the student will not accept.
            room_wants: Preferred room ids; an empty set means no room preference.
            room_avoids: Room ids the student will not sit in.
        """
        self.wants = wants
        self.avoids = avoids
        self.room_wants = room_wants
        self.room_avoids = room_avoids

    def __hash__(self):
        """AI-generated docstring: Hash preference sets so ``Preference`` can be dict keys."""
        return hash((frozenset(self.wants), frozenset(self.avoids), frozenset(self.room_wants), frozenset(self.room_avoids)))

    def __eq__(self, other):
        """AI-generated docstring: Compare all four preference sets for equality."""
        return (self.wants, self.avoids, self.room_wants, self.room_avoids) == (other.wants, other.avoids, other.room_wants, other.room_avoids)  # noqa

    def __ne__(self, other):
        """AI-generated docstring: Return whether this preference differs from ``other``."""
        return not (self == other)

    def __repr__(self):
        """AI-generated docstring: Return a developer-friendly representation of the preference."""
        return f'Preference(wants={self.wants}, avoids={self.avoids}, room_wants={self.room_wants}, room_avoids={self.room_avoids})'  # noqa

    def __str__(self):
        """AI-generated docstring: Return a human-readable representation of the preference."""
        return f'Preference(wants={self.wants}, avoids={self.avoids}, room_wants={self.room_wants}, room_avoids={self.room_avoids})'  # noqa


def is_seat_valid_for_preference(seat: Seat, preference: Preference):
    """TA-written docstring:
    Check if a seat is valid for a given preference.
    Comparison of attributes is case-insensitive.

    AI-generated docstring: Return whether a seat satisfies a student's preferences.

    Seat attributes are compared case-insensitively. Room wants and avoids use numeric
    room ids compared against ``seat.room.id``.

    Args:
        seat: Candidate seat with attributes and an associated room.
        preference: Student wants, avoids, and room preferences to check.

    Returns:
        True if the seat meets all wants, avoids no avoided attributes, and satisfies
        room wants/avoids; False otherwise.
    """
    wants, avoids, room_wants, room_avoids = preference.wants, preference.avoids, preference.room_wants, preference.room_avoids
    return (all(want.lower() in {attr.lower() for attr in seat.attributes} for want in wants) and  # noqa
            all(avoid.lower() not in {attr.lower() for attr in seat.attributes} for avoid in avoids) and  # noqa
            (not room_wants or any(int(a) == seat.room.id for a in room_wants)) and  # noqa
            all(int(a) != seat.room.id for a in room_avoids)  # noqa
            )


def filter_seats_by_preference(seats, preference: Preference):
    """TA-written docstring:
    Return seats available for a given preference.
    Comparison of attributes is case-insensitive.

    AI-generated docstring: Filter a seat list to those matching a preference.

    Args:
        seats: Iterable of ``Seat`` objects to consider (typically unassigned seats).
        preference: Wants, avoids, and room rules used by ``is_seat_valid_for_preference``.

    Returns:
        List of seats from ``seats`` that satisfy the preference.
    """
    return [seat for seat in seats if is_seat_valid_for_preference(seat, preference)]


def get_preference_from_student(student):
    """AI-generated docstring: Build a ``Preference`` from a student's stored preference fields."""
    return Preference(student.wants, student.avoids, student.room_wants, student.room_avoids)


def assign_students(exam):
    """TA-written docstring:
    Optimized Strategy:
    1. (One-Time) Group all students by preference into lists.
    2. (One-Time) Group all seats by preference into sets for fast removal.
    3. Loop N times (once per student):
     a. Find the "most restrictive" preference by checking group lengths.
     b. Pick a random student and seat from those groups.
     c. Remove the student from their list.
     d. Remove the seat from *all* seat sets it belongs to so it can't be assigned again.

    AI-generated docstring: Assign every unassigned student in an exam to a valid seat.

    Uses a greedy strategy: each round picks the preference with the fewest remaining
    eligible seats, then randomly pairs one student and one seat from that group.

    Args:
        exam: Exam whose ``unassigned_students`` and ``unassigned_seats`` are assigned.

    Returns:
        List of new ``SeatAssignment`` objects (not yet committed to the database).

    Raises:
        NotEnoughSeatError: When no seat remains for the most restrictive preference
            still waiting for assignment.
    """
    students = set(exam.unassigned_students)
    all_seats = set(exam.unassigned_seats)
    assignments = []

    if not students:
        return []

    # Step 1. Pre-calculate Student Groups
    students_by_pref: dict[Preference, list[Student]] = \
        arr_to_dict(students, key_getter=get_preference_from_student)

    all_preferences = students_by_pref.keys()

    # Step 2. Pre-calculate Seat Groups 
    seats_by_pref: dict[Preference, set[Seat]] = {
        preference: set(filter_seats_by_preference(all_seats, preference))
        for preference in all_preferences
    }

    # Step 3. Run the Loop N times
    for i in range(len(students)):
        # Find preferences that still have students
        active_preferences = [p for p, s_list in students_by_pref.items() if s_list]

        if not active_preferences:
            # Should not happen, but good to check
            break

        # a. Find the most restrictive preference (least seats avaialable)
        min_preference: Preference = min(
            active_preferences,
            key=lambda k: len(seats_by_pref[k])
        )

        min_students: list[Student] = students_by_pref[min_preference]
        min_seats: set[Seat] = seats_by_pref[min_preference]

        if not min_seats:
            # Need to get the *original* full list of students for the error
            original_students_for_pref = arr_to_dict(
                exam.unassigned_students, get_preference_from_student
            )[min_preference]
            raise NotEnoughSeatError(exam, original_students_for_pref, min_preference)

        # b. Pick a random student and seat
        # Always convert to list in a consistent way to ensure predictable mock calls
        min_students_list = list(min_students)
        min_seats_list = list(min_seats)
        
        student = random.choice(min_students_list)
        seat = random.choice(min_seats_list)

        assignments.append(SeatAssignment(student=student, seat=seat))

        # c. Remove the student
        min_students.remove(student)

        # d. Remove the seat from *all* preference sets
        for pref_set in seats_by_pref.values():
            pref_set.discard(seat)

    return assignments


def assign_single_student(exam, student, seat=None, ignore_restrictions=False):
    """TA-written docstring: Assign a single student to a seat.
    If a seat is not provided, try to find a seat that meets the student's requirements (if ignore_restrictions is False),
    or just any seat that is available (if ignore_restrictions is True).
    If a seat is provided, check if the seat is available and meets the student's requirements (if ignore_restrictions is False),
    or only check if the seat is available (if ignore_restrictions is True).
    Then, the chosen seat is assigned to the student.

    The original assignment will NOT be removed! It is the caller's responsibility to remove the original assignment if needed.

    AI-generated docstring: Assign a student to a seat in an exam, with optional seat and restriction overrides.

    Args:
        exam: The exam object containing unassigned seats.
        student: The student to be assigned a seat.
        seat: A specific seat to assign to the student. If None, a seat is
            selected automatically.
        ignore_restrictions: If True, skips preference-based seat filtering
            and only checks availability.

    Returns:
        A SeatAssignment object pairing the student with the chosen seat.

    Raises:
        SeatOverrideError: If the provided seat is unavailable or does not
            meet the student's requirements (when ignore_restrictions is False).
        NotEnoughSeatError: If no seat is provided and no eligible seats are
            available.
    """
    preference: Preference = get_preference_from_student(student)
    seats: list[Seat] = filter_seats_by_preference(exam.unassigned_seats, preference) \
        if not ignore_restrictions else exam.unassigned_seats

    # if a seat is provided, check it
    if seat and seat not in seats:
        raise SeatOverrideError(student, seat,
                                "Seat is already taken or does exist in the exam, or does not meet the student's requirements.")

    # if seat is not provided, try getting a seat that meets the student's requirements
    if not seat:
        if not seats:
            raise NotEnoughSeatError(exam, [student], preference)
        seat = random.choice(seats)

    # create and return a new assignment
    return SeatAssignment(student=student, seat=seat)
