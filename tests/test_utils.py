from StringIO import StringIO
import unittest
from tests import FileObjMatcher, CallableMatcher


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


class TestCallableMatcher(unittest.TestCase):
    def test_ok_callable(self):
        self.assertTrue(CallableMatcher(lambda x: True).__eq__(None))

    def test_false_callable(self):
        self.assertFalse(CallableMatcher(lambda x: False).__eq__(None))

    def test_raises(self):
        with self.assertRaises(Exception):
            self.assertFalse(CallableMatcher(lambda x: x.foo).__eq__(None))

    def test_gets_arg(self):
        self.assertEqual(12345, CallableMatcher(lambda x: x).__eq__(12345))

if __name__ == '__main__':
    unittest.main()
