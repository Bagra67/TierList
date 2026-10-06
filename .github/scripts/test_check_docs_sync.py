"""Tests of check_docs_sync.py.

Usage (from the repo root): python -m unittest discover -s .github/scripts
"""

import tempfile
import unittest
from pathlib import Path

from check_docs_sync import (
    find_bad_language_switchers,
    find_one_sided_changes,
    find_tests_without_guide,
    find_unpaired_docs,
    run_checks,
)


def paths_of(problems):
    return [problem.path for problem in problems]


class UnpairedDocsTest(unittest.TestCase):
    def test_a_complete_pair_is_accepted(self):
        self.assertEqual(find_unpaired_docs(["docs/i18n.md", "docs/i18n.fr.md"]), [])

    def test_an_english_doc_without_french_is_reported(self):
        problems = find_unpaired_docs(["docs/new.md"])
        self.assertEqual(paths_of(problems), ["docs/new.md"])
        self.assertIn("docs/new.fr.md", problems[0].message)

    def test_a_french_doc_without_english_is_reported(self):
        problems = find_unpaired_docs(["README.fr.md"])
        self.assertEqual(paths_of(problems), ["README.fr.md"])
        self.assertIn("README.md", problems[0].message)

    def test_english_only_files_are_ignored(self):
        self.assertEqual(find_unpaired_docs(["AGENTS.md", ".github/pull_request_template.md"]), [])


class LanguageSwitcherTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def write(self, path, text):
        (self.root / path).write_text(text, encoding="utf-8")

    def test_switchers_on_the_first_line_or_under_the_title_are_accepted(self):
        self.write("guide.md", "English | [Français](guide.fr.md)\n\n# Guide\n")
        self.write("guide.fr.md", "# Guide\n\n[English](guide.md) | Français\n")
        self.assertEqual(find_bad_language_switchers(self.root, ["guide.md", "guide.fr.md"]), [])

    def test_a_missing_or_wrong_switcher_is_reported(self):
        self.write("guide.md", "# Guide\n\nNo switcher here.\n")
        self.write("guide.fr.md", "# Guide\n\n[English](other.md) | Français\n")
        problems = find_bad_language_switchers(self.root, ["guide.md", "guide.fr.md"])
        self.assertEqual(paths_of(problems), ["guide.fr.md", "guide.md"])
        self.assertIn("English | [Français](guide.fr.md)", problems[1].message)

    def test_a_switcher_too_far_down_is_reported(self):
        self.write("guide.md", "# Guide\n" + "\n" * 10 + "English | [Français](guide.fr.md)\n")
        self.assertEqual(
            paths_of(find_bad_language_switchers(self.root, ["guide.md"])), ["guide.md"]
        )


class OneSidedChangesTest(unittest.TestCase):
    def test_both_languages_changed_is_accepted(self):
        self.assertEqual(find_one_sided_changes(["README.md", "README.fr.md", "app.py"]), [])

    def test_a_single_language_changed_is_reported(self):
        problems = find_one_sided_changes(["docs/i18n.fr.md", "app.py"])
        self.assertEqual(paths_of(problems), ["docs/i18n.fr.md"])
        self.assertIn("docs/i18n.md", problems[0].message)

    def test_english_only_files_are_ignored(self):
        self.assertEqual(
            find_one_sided_changes(["AGENTS.md", ".github/pull_request_template.md"]), []
        )


class TestsWithoutGuideTest(unittest.TestCase):
    GUIDE = ["docs/testing.md", "docs/testing.fr.md"]

    def test_every_kind_of_test_file_requires_the_guide(self):
        tests = [
            ".github/scripts/test_check_docs_sync.py",
            "backend/tests/integration/conftest.py",
            "backend/tests/test_main.py",
            "frontend/src/App.test.tsx",
            "frontend/src/api/client.test.ts",
            "frontend/src/test/setup.ts",
        ]
        self.assertEqual(paths_of(find_tests_without_guide(tests)), tests)

    def test_tests_with_both_guides_are_accepted(self):
        self.assertEqual(find_tests_without_guide(["backend/tests/test_main.py", *self.GUIDE]), [])

    def test_tests_with_a_single_guide_are_reported(self):
        changed = ["frontend/src/App.test.tsx", "docs/testing.md"]
        self.assertEqual(paths_of(find_tests_without_guide(changed)), ["frontend/src/App.test.tsx"])

    def test_non_test_files_do_not_require_the_guide(self):
        changed = ["backend/app/main.py", "frontend/src/App.tsx", "frontend/src/testing.ts"]
        self.assertEqual(find_tests_without_guide(changed), [])


class RunChecksTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        (self.root / "README.md").write_text(
            "English | [Français](README.fr.md)\n", encoding="utf-8"
        )
        (self.root / "README.fr.md").write_text(
            "[English](README.md) | Français\n", encoding="utf-8"
        )
        self.markdown = ["README.md", "README.fr.md"]

    def tearDown(self):
        self.directory.cleanup()

    def test_sync_checks_run_on_changes(self):
        problems = run_checks(self.root, self.markdown, ["README.md", "backend/tests/test_main.py"])
        self.assertEqual(paths_of(problems), ["README.md", "backend/tests/test_main.py"])

    def test_skipped_sync_checks_keep_the_pairing_checks(self):
        self.assertEqual(run_checks(self.root, self.markdown, None), [])
        problems = run_checks(self.root, ["README.md"], None)
        self.assertEqual(paths_of(problems), ["README.md"])


if __name__ == "__main__":
    unittest.main()
