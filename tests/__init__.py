from StringIO import StringIO


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


from datetime import tzinfo, timedelta, datetime


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