"""Check that bilingual docs and the testing guide stay in sync (AGENTS.md §28 and §31).

Usage: python check_docs_sync.py [--base <commit>] [--skip-sync]

Always checked, on every tracked Markdown file:
- every `name.md` has its `name.fr.md` in the same directory, and the other way round;
- each file has its language switcher near the top.

Checked on the changes since `--base` (the PR base), unless `--skip-sync`:
- an English doc is never changed without its French version, and the other way round;
- a changed test, test fixture or test tool comes with `docs/testing.md` and `docs/testing.fr.md`.

Errors are printed as GitHub Actions annotations; the exit code is 1 when there is one.
Standard library only, so it runs on any runner without installing anything.
"""

import argparse
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

ENGLISH_ONLY = {"AGENTS.md"}
# The PR template is read by GitHub, not by people browsing the docs.
EXCLUDED_DIRS = (".github/",)
# The switcher sits on the first line, or just under the title.
SWITCHER_MAX_LINE = 5
TESTING_GUIDE = ("docs/testing.md", "docs/testing.fr.md")
SKIP_LABEL = "skip-docs-sync"


@dataclass(frozen=True)
class Problem:
    path: str
    message: str


def is_bilingual_doc(path: str) -> bool:
    return path.endswith(".md") and path not in ENGLISH_ONLY and not path.startswith(EXCLUDED_DIRS)


def is_french(path: str) -> bool:
    return path.endswith(".fr.md")


def counterpart(path: str) -> str:
    """`docs/i18n.md` <-> `docs/i18n.fr.md`."""
    if is_french(path):
        return path.removesuffix(".fr.md") + ".md"
    return path.removesuffix(".md") + ".fr.md"


def expected_switcher(path: str) -> str:
    other = Path(counterpart(path)).name
    if is_french(path):
        return f"[English]({other}) | Français"
    return f"English | [Français]({other})"


def find_unpaired_docs(markdown_paths: Iterable[str]) -> list[Problem]:
    docs = {path for path in markdown_paths if is_bilingual_doc(path)}
    return [
        Problem(path, f"Missing translation: add {counterpart(path)}.")
        for path in sorted(docs)
        if counterpart(path) not in docs
    ]


def find_bad_language_switchers(root: Path, markdown_paths: Iterable[str]) -> list[Problem]:
    problems = []
    for path in sorted(p for p in markdown_paths if is_bilingual_doc(p)):
        head = (root / path).read_text(encoding="utf-8").splitlines()[:SWITCHER_MAX_LINE]
        switcher = expected_switcher(path)
        if switcher not in (line.strip() for line in head):
            problems.append(
                Problem(
                    path,
                    f"Missing language switcher: the first {SWITCHER_MAX_LINE} lines "
                    f"must contain `{switcher}`.",
                )
            )
    return problems


def find_one_sided_changes(changed_paths: Iterable[str]) -> list[Problem]:
    changed = {path for path in changed_paths if is_bilingual_doc(path)}
    return [
        Problem(path, f"Only one language changed: update {counterpart(path)} as well.")
        for path in sorted(changed)
        if counterpart(path) not in changed
    ]


def is_test_file(path: str) -> bool:
    """Tests, fixtures and test tools that docs/testing.md describes."""
    return path.startswith(("backend/tests/", "frontend/src/test/", ".github/scripts/test_")) or (
        path.startswith("frontend/src/") and path.endswith((".test.ts", ".test.tsx"))
    )


def find_tests_without_guide(changed_paths: Iterable[str]) -> list[Problem]:
    changed = set(changed_paths)
    if all(guide in changed for guide in TESTING_GUIDE):
        return []
    return [
        Problem(
            path,
            "Test changed without the testing guide: update docs/testing.md "
            "and docs/testing.fr.md.",
        )
        for path in sorted(changed)
        if is_test_file(path)
    ]


def run_checks(
    root: Path,
    markdown_paths: list[str],
    changed_paths: list[str] | None,
) -> list[Problem]:
    """`changed_paths` is None when the sync checks are skipped (no base, or skip label)."""
    problems = find_unpaired_docs(markdown_paths)
    problems += find_bad_language_switchers(root, markdown_paths)
    if changed_paths is not None:
        problems += find_one_sided_changes(changed_paths)
        problems += find_tests_without_guide(changed_paths)
    return problems


def git_lines(root: Path, *args: str) -> list[str]:
    output = subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout
    return [line for line in output.splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", help="commit the changes are compared with (the PR base)")
    parser.add_argument("--skip-sync", action="store_true", help="skip the checks on changes")
    args = parser.parse_args()

    root = Path(git_lines(Path.cwd(), "rev-parse", "--show-toplevel")[0])
    markdown_paths = git_lines(root, "ls-files", "--", "*.md")
    changed_paths = None
    if args.base and not args.skip_sync:
        # --no-renames: a renamed doc counts as deleted + added, so both paths are checked.
        changed_paths = git_lines(
            root, "diff", "--name-only", "--no-renames", f"{args.base}...HEAD"
        )

    problems = run_checks(root, markdown_paths, changed_paths)
    for problem in problems:
        print(f"::error file={problem.path}::{problem.message}")
    if problems:
        print(
            f"{len(problems)} problem(s). For a justified exception (e.g. a typo fixed in one "
            f"language), add the `{SKIP_LABEL}` label to the PR and explain why in its description."
        )
        return 1
    print("Docs are in sync." if changed_paths is not None else "Docs are paired.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
