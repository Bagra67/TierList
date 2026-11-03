import unittest

from junit_summary import display_name


class DisplayNameTest(unittest.TestCase):
    def test_a_pytest_class_name_becomes_a_file_path(self):
        self.assertEqual(
            display_name("tests.test_main", "test_hello"), "tests/test_main.py::test_hello"
        )

    def test_a_vitest_class_name_is_kept_as_a_file(self):
        self.assertEqual(
            display_name("src/App.test.tsx", "App > shows…"), "src/App.test.tsx › App > shows…"
        )


if __name__ == "__main__":
    unittest.main()
