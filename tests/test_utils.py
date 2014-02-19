from StringIO import StringIO
from tests import FileObjMatcher
import unittest2 as unittest


class TestFileObjMatcher(unittest.TestCase):
    def test_matcher_eq_works(self):
        self.assertTrue(FileObjMatcher('hello world') == StringIO('hello world'))
        self.assertFalse(FileObjMatcher('hello world') == StringIO('goodbye world'))

    def test_rollback_to_stream(self):
        source_data = StringIO('hello world')
        source_data.seek(1)
        other_data = StringIO('hello world')
        other_data.seek(2)

        self.assertFalse(FileObjMatcher(source_data) == other_data)
        self.assertEqual(source_data.tell(), 1)
        self.assertEqual(other_data.tell(), 2)


if __name__ == '__main__':
    unittest.main()
