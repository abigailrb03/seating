"""AI-generated docstring: Cal1Card (C1C) API client for student ID photos.

When ``MOCK_C1C`` is enabled outside production, ``get_student_photo`` reads from
local fake data instead of the Cal1Card HTTP API.
"""

from server import app
from server.services.c1c import fake_data


def is_mock_c1c() -> bool:
    """AI-generated docstring: Return True when fake C1C photos should be used."""
    return app.config['MOCK_C1C'] and \
        app.config['FLASK_ENV'].lower() != 'production'


class C1C:
    """AI-generated docstring: HTTP client for the Cal1Card photo API.

    Attributes:
        proxy_dict: Optional ``requests`` proxy mapping, or ``None`` when direct.
        api_domain: Base URL for Cal1Card API requests.
        username: Basic-auth username for the API.
        password: Basic-auth password for the API.
    """

    def __init__(self, proxy_url, api_domain, username, password):
        """AI-generated docstring: Store connection settings for Cal1Card requests.

        Args:
            proxy_url: HTTP/HTTPS proxy URL, or empty/None for no proxy.
            api_domain: Host and path prefix for the C1C API.
            username: API basic-auth username from app config.
            password: API basic-auth password from app config.
        """
        self.proxy_dict = {
            'http': proxy_url,
            'https': proxy_url
        } if proxy_url else None
        self.api_domain = api_domain
        self.username = username
        self.password = password

    def _make_request(self, path, method='GET'):
        """AI-generated docstring: Send an authenticated HTTP request to the C1C API.

        Args:
            path: Path appended to ``api_domain`` (e.g. ``/c1c-api/v1/photo/<sid>``).
            method: HTTP verb, default ``GET``.

        Returns:
            ``requests.Response`` from the Cal1Card server.
        """
        import requests
        url = f'{self.api_domain}{path}'
        if self.proxy_dict:
            return requests.request(method, url, proxies=self.proxy_dict,
                                    auth=(self.username, self.password))
        else:
            return requests.request(method, url, auth=(self.username, self.password))

    def get_student_photo(self, sid):
        """AI-generated docstring: Fetch a student's Cal1Card photo bytes by SID.

        Uses fake local photos when ``MOCK_C1C`` is on; otherwise calls the real API.
        Returns ``None`` on non-200 responses or network errors (same as a missing photo).

        Args:
            sid: Student identifier string passed to the photo endpoint.

        Returns:
            Raw JPEG (or other) bytes on success, or ``None`` when unavailable.
        """
        if is_mock_c1c():
            return fake_data.get_fake_photo(sid)
        try:
            r = self._make_request(f'/c1c-api/v1/photo/{sid}')
            if r.status_code == 200:
                return r.content
            else:
                return None
        except:
            return None


c1c_client = C1C(app.config['C1C_PROXY_URL'], app.config['C1C_API_DOMAIN'],
                 app.config['C1C_API_USERNAME'], app.config['C1C_API_PASSWORD'])
