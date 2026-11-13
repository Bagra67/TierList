import ast
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from check_docs_sync import (
    find_bad_language_switchers,
    find_one_sided_changes,
    find_unpaired_docs,
    run_checks,
)


SCRIPT = Path(__file__).with_name("check_docs_sync.py")


def paths_of(problems):
    return [problem.path for problem in problems]


class UnpairedDocsTest(unittest.TestCase):
    def test_a_complete_pair_is_accepted(self):
        self.assertEqual(find_unpaired_docs(["backend/README.md", "backend/README.fr.md"]), [])

    def test_an_english_readme_without_french_is_reported(self):
        problems = find_unpaired_docs(["frontend/README.md"])
        self.assertEqual(paths_of(problems), ["frontend/README.md"])
        self.assertIn("frontend/README.fr.md", problems[0].message)

    def test_a_french_doc_without_english_is_reported(self):
        problems = find_unpaired_docs(["README.fr.md"])
        self.assertEqual(paths_of(problems), ["README.fr.md"])
        self.assertIn("README.md", problems[0].message)

    def test_english_only_files_are_ignored(self):
        self.assertEqual(
            find_unpaired_docs(
                [
                    "AGENTS.md",
                    "TODO.md",
                    "docs/technical/i18n.md",
                    "docs/product/milestone-1/README.md",
                    ".github/pull_request_template.md",
                    ".claude/skills/api-sync/SKILL.md",
                ]
            ),
            [],
        )


class LanguageSwitcherTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def write(self, path, text):
        (self.root / path).write_text(text, encoding="utf-8")

    def test_switchers_on_the_first_line_or_under_the_title_are_accepted(self):
        self.write("README.md", "English | [Français](README.fr.md)\n\n# TierList\n")
        self.write("README.fr.md", "# TierList\n\n[English](README.md) | Français\n")
        self.assertEqual(find_bad_language_switchers(self.root, ["README.md", "README.fr.md"]), [])

    def test_a_missing_or_wrong_switcher_is_reported(self):
        self.write("README.md", "# TierList\n\nNo switcher here.\n")
        self.write("README.fr.md", "# TierList\n\n[English](other.md) | Français\n")
        problems = find_bad_language_switchers(self.root, ["README.md", "README.fr.md"])
        self.assertEqual(paths_of(problems), ["README.fr.md", "README.md"])
        self.assertIn("English | [Français](README.fr.md)", problems[1].message)

    def test_a_switcher_too_far_down_is_reported(self):
        self.write("README.md", "# TierList\n" + "\n" * 10 + "English | [Français](README.fr.md)\n")
        self.assertEqual(
            paths_of(find_bad_language_switchers(self.root, ["README.md"])), ["README.md"]
        )


class OneSidedChangesTest(unittest.TestCase):
    def test_both_languages_changed_is_accepted(self):
        self.assertEqual(find_one_sided_changes(["README.md", "README.fr.md", "app.py"]), [])

    def test_a_single_language_changed_is_reported(self):
        problems = find_one_sided_changes(["CHANGELOG.fr.md", "app.py"])
        self.assertEqual(paths_of(problems), ["CHANGELOG.fr.md"])
        self.assertIn("CHANGELOG.md", problems[0].message)

    def test_english_only_files_are_ignored(self):
        self.assertEqual(
            find_one_sided_changes(
                [
                    "AGENTS.md",
                    "docs/technical/i18n.md",
                    ".github/pull_request_template.md",
                    ".claude/agents/security-reviewer.md",
                ]
            ),
            [],
        )


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
        self.assertEqual(paths_of(problems), ["README.md"])

    def test_skipped_sync_checks_keep_the_pairing_checks(self):
        self.assertEqual(run_checks(self.root, self.markdown, None), [])
        problems = run_checks(self.root, ["README.md"], None)
        self.assertEqual(paths_of(problems), ["README.md"])


class CommandLineTest(unittest.TestCase):
    def run_in_a_repository_with_an_unpaired_doc(self):
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run(["git", "init", "--quiet"], cwd=directory, check=True)
            (Path(directory) / "README.md").write_text("English | [Français](README.fr.md)\n")
            subprocess.run(["git", "add", "README.md"], cwd=directory, check=True)
            return subprocess.run(
                [sys.executable, str(SCRIPT)],
                cwd=directory,
                capture_output=True,
                text=True,
            )

    def test_a_problem_is_a_github_annotation_and_fails_the_run(self):
        completed = self.run_in_a_repository_with_an_unpaired_doc()
        self.assertEqual(completed.returncode, 1)
        self.assertIn("::error file=README.md::", completed.stdout)

    def test_the_script_only_imports_the_standard_library(self):
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        imported_modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported_modules.add((node.module or "").split(".")[0])
        self.assertLessEqual(imported_modules, set(sys.stdlib_module_names))


if __name__ == "__main__":
    unittest.main()
