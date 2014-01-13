from StringIO import StringIO
from datetime import tzinfo, timedelta
from flexmock import flexmock
try:
    import json as json
except:
    import simplejson as json

class FileObjMatcher(object):
    """
    verifies the the passed fileobj matches the one received from the mock
    """

    def __init__(self, expected):
        if isinstance(expected, str):
            expected = StringIO(expected)

        self._expected = expected

    def __eq__(self, other):
        original_other_position = other.tell()
        original_expected_position = self._expected.tell()
        result = self._expected.read() == other.read()

        self._expected.seek(original_expected_position)
        other.seek(original_other_position)

        return result


# A UTC class.
class UTC(tzinfo):
    """UTC"""
    ZERO = timedelta(0)
    HOUR = timedelta(hours=1)

    def utcoffset(self, dt):
        return self.ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return self.ZERO

utc = UTC()


def mocked_response(content=None, status_code=200, headers=None):
    if isinstance(content, dict):
        content = json.dumps(content)

    return flexmock(ok=status_code < 400, status_code=status_code, json=lambda: json.loads(content), raw=content, text=content, headers=headers)
