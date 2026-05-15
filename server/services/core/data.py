"""AI-generated docstring: Load rooms and student rosters from Canvas, CSV, sheets, or forms."""

from server.forms import ImportStudentFormBase
from server.services.canvas import get_student_roster_for_offering
from server.services.csv import parse_csv, parse_csv_str
from server.services.google import get_spreadsheet_tab_content

from server.services.core.room import prepare_room, prepare_seat
from server.services.core.student import StudentImportConfig, prepare_students
from server.typings.enum import AssignmentImportStrategy


def get_room_from_google_spreadsheet(exam, room_form):
    """AI-generated docstring: Build a room and seats from a Google Sheet tab.

    Args:
        exam: Exam the new room belongs to.
        room_form: Form with room metadata plus ``sheet_url`` and ``sheet_range``.

    Returns:
        ``Room`` with ``seats`` populated from the spreadsheet (not yet committed).
    """
    room = prepare_room(exam, room_form)
    headers, rows = get_spreadsheet_tab_content(room_form.sheet_url.data,
                                                room_form.sheet_range.data)
    seats = prepare_seat(headers, rows)
    room.seats = seats
    return room


def get_room_from_csv(exam, room_form):
    """AI-generated docstring: Build a room and seats from an uploaded CSV file.

    Args:
        exam: Exam the new room belongs to.
        room_form: Form with room metadata and a CSV ``file`` upload field.

    Returns:
        ``Room`` with ``seats`` populated from the CSV (not yet committed).
    """
    room = prepare_room(exam, room_form)
    headers, rows = parse_csv(room_form.file.data)
    seats = prepare_seat(headers, rows)
    room.seats = seats
    return room


def get_room_from_manual_input(exam, room_form, manual_input_dict):
    """AI-generated docstring: Build a room and movable seats from manual attribute counts.

    Args:
        exam: Exam the new room belongs to.
        room_form: Form with room metadata (display name, times, etc.).
        manual_input_dict: Maps attribute sets to seat counts for movable seats.

    Returns:
        ``Room`` with movable ``seats`` derived from ``manual_input_dict``.
    """
    room = prepare_room(exam, room_form)
    headers, rows = _get_seats_from_manual_input(manual_input_dict)
    seats = prepare_seat(headers, rows)
    room.seats = seats
    return room


def update_room_from_manual_input(room, manual_input_dict):
    """AI-generated docstring: Replace movable seats on an existing room from manual input.

    Args:
        room: Existing ``Room`` whose movable seats are updated in place.
        manual_input_dict: Maps attribute sets to counts for new movable seats.
    """
    headers, rows = _get_seats_from_manual_input(manual_input_dict)
    seats = prepare_seat(headers, rows)
    room.update_movable_seats(seats)  # manual input only handles movable seats


def _get_seats_from_manual_input(manual_input_dict):
    """AI-generated docstring: Convert manual seat-attribute counts to sheet headers and rows.

    Args:
        manual_input_dict: Keys are sets of attribute names; values are seat counts.

    Returns:
        Tuple ``(headers, rows)`` in the same shape ``prepare_seat`` expects.
    """
    headers = set(['row', 'seat', 'x', 'y'])
    for attr_set in manual_input_dict:
        headers.union(attr_set)
    headers = list(headers)
    rows = []
    for attr_set, count in manual_input_dict.items():
        row_dic = {
            k.lower(): 'true' for k in attr_set
        }
        row_dic['count'] = count
        rows.append(row_dic)
    return headers, rows


def _get_config_from_form(student_form: ImportStudentFormBase):
    """AI-generated docstring: Build a ``StudentImportConfig`` from import form checkboxes."""
    return StudentImportConfig(
        revalidate_existing_assignments=student_form.revalidate_existing_assignments.data,
        assignment_import_strategy=student_form.assignment_import_strategy.data,
        updated_student_info_import_strategy=student_form.updated_student_info_import_strategy.data,
        updated_preference_import_strategy=student_form.updated_preference_import_strategy.data,
        new_student_import_strategy=student_form.new_student_import_strategy.data,
        missing_student_import_strategy=student_form.missing_student_import_strategy.data
    )


def get_students_from_google_spreadsheet(exam, student_form):
    """AI-generated docstring: Import students from a Google Sheet using form import options.

    Args:
        exam: Exam students are imported into.
        student_form: Form with sheet URL, range, and import strategy fields.

    Returns:
        Result tuple from ``prepare_students`` (new, updated, invalid, ids to remove).
    """
    headers, rows = get_spreadsheet_tab_content(student_form.sheet_url.data,
                                                student_form.sheet_range.data)
    return prepare_students(exam, headers, rows, config=_get_config_from_form(student_form))


def get_students_from_csv(exam, student_form):
    """AI-generated docstring: Import students from an uploaded CSV using form import options.

    Args:
        exam: Exam students are imported into.
        student_form: Form with CSV file and import strategy fields.

    Returns:
        Result tuple from ``prepare_students``.
    """
    headers, rows = parse_csv(student_form.file.data)
    return prepare_students(exam, headers, rows, config=_get_config_from_form(student_form))


def get_students_from_manual_input(exam, student_form):
    """AI-generated docstring: Import students from pasted CSV text in a form field.

    Args:
        exam: Exam students are imported into.
        student_form: Form with ``text`` CSV body and import strategy fields.

    Returns:
        Result tuple from ``prepare_students``.
    """
    headers, rows = parse_csv_str(student_form.text.data)
    return prepare_students(exam, headers, rows, config=_get_config_from_form(student_form))


def get_students_from_canvas(exam, student_form):
    """AI-generated docstring: Import students from the Canvas roster API for the offering.

    Args:
        exam: Exam students are imported into (uses ``offering_canvas_id``).
        student_form: Form supplying import strategy options (no file upload).

    Returns:
        Result tuple from ``prepare_students``.
    """
    headers, rows = get_student_roster_for_offering(exam.offering_canvas_id)
    return prepare_students(exam, headers, rows, config=_get_config_from_form(student_form))
