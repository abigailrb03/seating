"""AI-generated docstring: Read Google Sheets data for room and student imports.

Uses a service-account-backed Sheets API client built at import time from
``GCP_SA_CRED_TYPE`` (file or env) and exposes tab listing and row parsing helpers.
"""

import re
import itertools
import json
import base64

from apiclient import errors
from server import app
from server.typings.enum import GcpSaCredType
from server.typings.exception import GcpError

from google.oauth2 import service_account
from googleapiclient.discovery import build


def _get_spreadsheet_service():
    """TA-written docstring:
    Returns an authorized API client service for Google Sheets API.

    AI-generated docstring: Build a Google Sheets v4 client from service account config.

    Credentials come from a JSON file when ``GCP_SA_CRED_TYPE`` is ``file``, or from a
    base64-encoded JSON string in ``GCP_SA_CRED_VALUE`` when type is ``env``.

    Returns:
        Authorized ``googleapiclient`` Sheets API service object.

    Raises:
        GcpError: When credential type is invalid or credentials cannot be loaded.
    """
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    cred_type = app.config.get('GCP_SA_CRED_TYPE')
    credentials = None
    if cred_type == GcpSaCredType.FILE.value:
        credentials = service_account.Credentials.from_service_account_file(
            app.config.get('GCP_SA_CRED_FILE'), scopes=SCOPES)
    elif cred_type == GcpSaCredType.ENV.value:
        decoded_credentials = base64.b64decode(app.config.get('GCP_SA_CRED_VALUE'))
        service_account_info = json.loads(decoded_credentials)
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=SCOPES)
    else:
        raise GcpError('Invalid GCP_SA_CRED_TYPE')
    if not credentials:
        raise GcpError('Invalid GCP credentials')
    return build('sheets', 'v4', credentials=credentials)


service = _get_spreadsheet_service()


def _get_spreadsheet_id(sheet_url):
    """AI-generated docstring: Extract the spreadsheet id from a Google Sheets share URL.

    Args:
        sheet_url: Full URL containing ``/spreadsheets/d/<id>/``.

    Returns:
        Spreadsheet id string.

    Raises:
        GcpError: When the URL does not match the expected pattern.
    """
    m = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', sheet_url)
    if not m or not m.group(1):
        raise GcpError('Enter a Google Sheets URL')
    return m.group(1)


def get_spreadsheet_tabs(sheet_url):
    """AI-generated docstring: List tab (sheet) titles in a Google Spreadsheet.

    Args:
        sheet_url: Google Sheets URL used to resolve the spreadsheet id.

    Returns:
        List of tab name strings.

    Raises:
        GcpError: When the API request fails or the URL is invalid.
    """
    spreadsheet_id = _get_spreadsheet_id(sheet_url)
    try:
        sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        sheets = sheet_metadata.get('sheets', '')
        return [sheet['properties']['title'] for sheet in sheets]
    except errors.HttpError as e:
        raise GcpError(e._get_reason())


def get_spreadsheet_tab_content(sheet_url, tab_name):
    """AI-generated docstring: Read one tab as lowercase headers and row dicts for import.

    First row becomes column headers (lowercased). Each following row is a dict keyed by
    header. Headers must be unique and alphanumeric.

    Args:
        sheet_url: Google Sheets URL used to resolve the spreadsheet id.
        tab_name: Tab title or A1 range name passed to the Sheets API.

    Returns:
        Tuple ``(headers, rows)`` where ``headers`` is a list of strings and ``rows`` is a
        list of dicts mapping header to cell value.

    Raises:
        GcpError: When the sheet is empty, headers are invalid, or the API call fails.
    """
    spreadsheet_id = _get_spreadsheet_id(sheet_url)
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=tab_name).execute()
    except errors.HttpError as e:
        raise GcpError(e._get_reason())
    values = result.get('values', [])

    if not values:
        raise GcpError('Sheet is empty')
    headers = [h.lower() for h in values[0]]
    rows = [
        {k: v for k, v in itertools.zip_longest(headers, row, fillvalue='')}
        for row in values[1:]
    ]
    if len(set(headers)) != len(headers):
        raise GcpError('Headers must be unique')
    elif not all(re.match(r'[a-z0-9]+', h) for h in headers):
        raise GcpError('Headers must consist of digits and numbers')
    return headers, rows
