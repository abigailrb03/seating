"""AI-generated docstring: WTForms classes for staff workflows in the seating web UI.

Covers offerings, exams, rooms, student import strategies, assignment, email, and dev login.
"""

import re

from flask_wtf import FlaskForm
from wtforms import FieldList, FormField, SelectField, ValidationError, BooleanField, FileField, SelectMultipleField, StringField, \
    SubmitField, TextAreaField, DateTimeField, IntegerField, widgets
from wtforms import Form as NoCsrfForm
from flask_wtf.file import FileRequired, FileAllowed
from wtforms.validators import Email, InputRequired, URL, Optional, DataRequired
from server.controllers import exam_regex
from server.typings.enum import AssignmentImportStrategy, NewRowImportStrategy, UpdatedRowImportStrategy, MissingRowImportStrategy


class MultiCheckboxField(SelectMultipleField):
    """AI-generated docstring: Multi-select field rendered as a list of checkboxes."""
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class ChooseCourseOfferingForm(FlaskForm):
    """AI-generated docstring: Pick Canvas offerings to import into the seating database."""
    submit = SubmitField('import')
    offerings = MultiCheckboxField('select_offerings')

    def __init__(self, offering_list=None, *args, **kwargs):
        super(ChooseCourseOfferingForm, self).__init__(*args, **kwargs)
        if offering_list is not None:
            self.offerings.choices = [(o.canvas_id, str(o)) for o in offering_list]  # (value, label)


class ExamFormBase(FlaskForm):
    """AI-generated docstring: Shared fields for creating or editing an exam."""
    display_name = StringField('display_name', [InputRequired()], render_kw={
                               "placeholder": "Midterm 1"})
    active = BooleanField('active', default=True)

    cancel = SubmitField('cancel')


class ExamForm(ExamFormBase):
    """AI-generated docstring: Create a new exam with a URL-safe ``name`` slug."""
    name = StringField('name', [InputRequired()], render_kw={"placeholder": "midterm1"})
    submit = SubmitField('create')

    def validate_name(form, field):
        pattern = '^{}$'.format(exam_regex)
        if not re.match(pattern, field.data):
            raise ValidationError('Exam name must be match pattern {}'.format(pattern))


class EditExamForm(ExamFormBase):
    """AI-generated docstring: Update an existing exam's display name and active flag."""
    submit = SubmitField('make edits')


class RoomFormBase(FlaskForm):
    """AI-generated docstring: Shared optional start time and duration for a room."""
    start_at = DateTimeField('start_at', [Optional()], format='%Y-%m-%dT%H:%M')
    duration_minutes = IntegerField('duration_minutes', [Optional()])


class RoomForm(RoomFormBase):
    """AI-generated docstring: Import a new room from a custom Google Sheet URL and range."""
    display_name = StringField('display_name', [InputRequired()])
    sheet_url = StringField('sheet_url', [URL(), InputRequired()])
    sheet_range = StringField('sheet_range', [InputRequired()])
    preview_room = SubmitField('preview')
    create_room = SubmitField('create')


class ChooseRoomForm(RoomFormBase):
    """AI-generated docstring: Import one or more rooms from tabs on the master room sheet."""
    submit = SubmitField('import')
    rooms = MultiCheckboxField('select_rooms')

    def __init__(self, room_list=None, *args, **kwargs):
        super(ChooseRoomForm, self).__init__(*args, **kwargs)
        if room_list is not None:
            self.rooms.choices = [(item, item) for item in room_list]  # (value, label)


class UploadRoomForm(RoomFormBase):
    """AI-generated docstring: Upload a CSV file to create a room and its seats."""
    submit = SubmitField('upload')
    file = FileField('Choose File', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV files only!')
    ])
    display_name = StringField('display_name', [InputRequired()])


class MovableSeatSubForm(NoCsrfForm):
    """AI-generated docstring: One row of movable-seat attributes and a count (no CSRF)."""
    attributes = StringField('attributes', default='', render_kw={"placeholder": "Righty, Aisle"})
    count = IntegerField('count', [InputRequired()], default=1, render_kw={"placeholder": "1"})


class EditRoomForm(RoomFormBase):
    """AI-generated docstring: Edit room metadata and movable seat counts by attribute set."""
    display_name = StringField('display_name', [InputRequired()])
    movable_seats = FieldList(FormField(MovableSeatSubForm), min_entries=0)
    submit = SubmitField('make edits')
    cancel = SubmitField('cancel')


class ImportStudentFormBase(FlaskForm):
    """AI-generated docstring: Import strategy options shared by all student import forms."""
    revalidate_existing_assignments = BooleanField('revalidate_existing_assignments', default=True)
    assignment_import_strategy = SelectField('assignment_import_strategy', choices=[
        (e.value, e.name) for e in AssignmentImportStrategy],
        default=AssignmentImportStrategy.REVALIDATE.value,
        validators=[DataRequired()])
    updated_student_info_import_strategy = SelectField('updated_student_info_import_strategy', choices=[
        (e.value, e.name) for e in UpdatedRowImportStrategy],
        default=UpdatedRowImportStrategy.MERGE.value,
        validators=[DataRequired()])
    updated_preference_import_strategy = SelectField('updated_preference_import_strategy', choices=[
        (e.value, e.name) for e in UpdatedRowImportStrategy],
        default=UpdatedRowImportStrategy.OVERWRITE.value,
        validators=[DataRequired()])
    new_student_import_strategy = SelectField('new_student_import_strategy', choices=[
        (e.value, e.name) for e in NewRowImportStrategy],
        default=NewRowImportStrategy.APPEND.value,
        validators=[DataRequired()])
    missing_student_import_strategy = SelectField('missing_student_import_strategy', choices=[
        (e.value, e.name) for e in MissingRowImportStrategy],
        default=MissingRowImportStrategy.IGNORE.value,
        validators=[DataRequired()])
    submit = SubmitField('import')


class ImportStudentFromSheetForm(ImportStudentFormBase):
    """AI-generated docstring: Import students from a Google Sheet URL and tab range."""
    sheet_url = StringField('sheet_url', [URL()])
    sheet_range = StringField('sheet_range', [InputRequired()])


class ImportStudentFromCanvasRosterForm(ImportStudentFormBase):
    """AI-generated docstring: Import students from the Canvas roster API for the offering."""
    pass


class ImportStudentFromCsvUploadForm(ImportStudentFormBase):
    """AI-generated docstring: Import students from an uploaded CSV file."""
    file = FileField('Choose File', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV files only!')
    ])


class ImportStudentFromManualInputForm(ImportStudentFormBase):
    """AI-generated docstring: Import students from pasted CSV text in a textarea."""
    text = TextAreaField('text', [InputRequired()], render_kw={
                         "placeholder": "canvas id,email,name\n123456,x@y.z,John\n..."})


class EditStudentsFormBase(FlaskForm):
    """AI-generated docstring: Bulk or single-student preference fields (wants, avoids, rooms)."""
    wants = StringField('wants')
    avoids = StringField('avoids')
    room_wants = MultiCheckboxField('room_wants')
    room_avoids = MultiCheckboxField('room_avoids')
    submit = SubmitField('make edits')
    cancel = SubmitField('cancel')

    def __init__(self, room_list=None, *args, **kwargs):
        super(EditStudentsFormBase, self).__init__(*args, **kwargs)
        if room_list is not None:
            self.room_wants.choices = [(str(item.id), item.name_and_start_at_time_display()) for item in room_list]
            self.room_avoids.choices = [(str(item.id), item.name_and_start_at_time_display()) for item in room_list]


class EditStudentForm(EditStudentsFormBase):
    """AI-generated docstring: Edit one student's email and seat/room preferences."""
    new_email = StringField('email', [Email()])

    def __init__(self, room_list=None, *args, **kwargs):
        super(EditStudentForm, self).__init__(room_list=room_list, *args, **kwargs)


class EditStudentsForm(EditStudentsFormBase):
    """AI-generated docstring: Apply preference changes to many students selected by email."""
    emails = TextAreaField('emails')
    use_all_emails = BooleanField('use_all_emails')

    def __init__(self, room_list=None, *args, **kwargs):
        super(EditStudentsForm, self).__init__(room_list=room_list, *args, **kwargs)


class DeleteStudentForm(FlaskForm):
    """AI-generated docstring: Delete students from an exam by email list or all at once."""
    emails = TextAreaField('emails')
    use_all_emails = BooleanField('use_all_emails')
    submit = SubmitField('delete by emails')


class AssignForm(FlaskForm):
    """AI-generated docstring: Bulk assign, delete all assignments, or reassign an exam."""
    submit = SubmitField('assign')
    delete_all = SubmitField('delete all assignments')
    reassign_all = SubmitField('reassign all assignments')


class AssignSingleForm(FlaskForm):
    """AI-generated docstring: Assign or remove one student's seat, with optional overrides."""
    ignore_restrictions = BooleanField('ignore restrictions')
    seat_id = StringField('seat_id')
    just_delete = SubmitField('just delete')
    submit = SubmitField('assign')


class EmailForm(FlaskForm):
    """AI-generated docstring: Compose and send assignment notification emails."""
    from_addr = StringField('from_addr', [Email(), InputRequired()])
    to_addr = StringField('to_addr', [InputRequired()])
    cc_addr = StringField('cc_addr', [])
    bcc_addr = StringField('bcc_addr', [])
    subject = StringField('subject', [InputRequired()])
    body = TextAreaField('body', [InputRequired()])
    body_html = BooleanField('body_html', default=True)
    submit = SubmitField('send')


class DevLoginForm(FlaskForm):
    """AI-generated docstring: Pick a mock Canvas user id when ``MOCK_CANVAS`` is enabled."""
    user_id = StringField('user_id', [InputRequired()], render_kw={"placeholder": "123456"})
    submit = SubmitField('login')
