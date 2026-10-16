"""Turn a JUnit XML test report (pytest, Vitest) into a Markdown summary for GitHub Actions.

Usage: python junit_summary.py <title> <junit.xml>
The Markdown is printed on stdout; the CI appends it to $GITHUB_STEP_SUMMARY.
Standard library only, so it runs on any runner without installing anything.
"""

import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

STATUS_ICONS = {"passed": "✅", "failed": "❌", "skipped": "⏭️"}
SLOWEST_COUNT = 5
TRACE_MAX_LINES = 40
MESSAGE_MAX_CHARS = 300
# ANSI color codes, raw or XML-escaped (`#x1B[33m`), that test tools may leave in their output.
ANSI_CODES = re.compile(r"(?:\x1b|#x1B)\[[0-9;]*m")


@dataclass
class TestResult:
    name: str
    status: str
    seconds: float
    message: str = ""
    details: str = ""


def display_name(classname: str, name: str) -> str:
    """`tests.test_main` + `test_hello` -> `tests/test_main.py::test_hello` (pytest);
    `src/App.test.tsx` + `App > shows…` -> `src/App.test.tsx › App > shows…` (Vitest)."""
    if not classname:
        return name
    if "/" in classname or classname.endswith((".ts", ".tsx", ".js", ".jsx")):
        return f"{classname} › {name}"
    return f"{classname.replace('.', '/')}.py::{name}"


def clean(text: str | None) -> str:
    return ANSI_CODES.sub("", text or "").strip()


def parse_report(path: Path) -> list[TestResult]:
    results: list[TestResult] = []
    for case in ET.parse(path).getroot().iter("testcase"):
        problem = case.find("failure")
        if problem is None:
            problem = case.find("error")
        skipped = case.find("skipped")
        if problem is not None:
            status, node = "failed", problem
        elif skipped is not None:
            status, node = "skipped", skipped
        else:
            status, node = "passed", None
        results.append(
            TestResult(
                name=display_name(case.get("classname", ""), case.get("name", "")),
                status=status,
                seconds=float(case.get("time") or 0),
                message=clean(node.get("message")) if node is not None else "",
                details=clean(node.text) if node is not None else "",
            )
        )
    return results


def cell(text: str) -> str:
    """Make a value safe for a Markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ")


def guide_link() -> str:
    server = os.environ.get("GITHUB_SERVER_URL")
    repository = os.environ.get("GITHUB_REPOSITORY")
    ref = os.environ.get("GITHUB_SHA")
    if server and repository and ref:
        return f"{server}/{repository}/blob/{ref}/docs/testing.md"
    return "docs/technical/testing.md"


def render(title: str, results: list[TestResult]) -> str:
    counts = {status: sum(r.status == status for r in results) for status in STATUS_ICONS}
    total_seconds = sum(r.seconds for r in results)
    verdict = "❌ Failed" if counts["failed"] else "✅ Passed"

    lines = [
        f"## {title} tests — {verdict}",
        "",
        f"**{len(results)} tests** in {total_seconds:.2f}s: "
        f"✅ {counts['passed']} passed · ❌ {counts['failed']} failed · "
        f"⏭️ {counts['skipped']} skipped",
        "",
    ]

    failed = [r for r in results if r.status == "failed"]
    if failed:
        lines += ["### ❌ Failures", ""]
        for result in failed:
            trace = "\n".join(result.details.splitlines()[:TRACE_MAX_LINES])
            lines += [
                f"**`{result.name}`**",
                "",
                f"> {cell(result.message[:MESSAGE_MAX_CHARS]) or 'No message'}",
                "",
                "<details><summary>Details</summary>",
                "",
                "```text",
                trace or "(no details)",
                "```",
                "",
                "</details>",
                "",
            ]

    skipped = [r for r in results if r.status == "skipped"]
    if skipped:
        lines += ["### ⏭️ Skipped", "", "| Test | Reason |", "| --- | --- |"]
        lines += [f"| `{cell(r.name)}` | {cell(r.message) or '—'} |" for r in skipped]
        lines.append("")

    lines += ["### All tests", "", "| | Test | Duration |", "| --- | --- | ---: |"]
    lines += [
        f"| {STATUS_ICONS[r.status]} | `{cell(r.name)}` | {r.seconds:.3f}s |" for r in results
    ]
    lines.append("")

    if len(results) > SLOWEST_COUNT:
        slowest = sorted(results, key=lambda r: r.seconds, reverse=True)[:SLOWEST_COUNT]
        lines += [f"### 🐢 {SLOWEST_COUNT} slowest tests", ""]
        lines += ["| Test | Duration |", "| --- | ---: |"]
        lines += [f"| `{cell(r.name)}` | {r.seconds:.3f}s |" for r in slowest]
        lines.append("")

    lines += [f"What each test checks: [testing guide]({guide_link()}).", ""]
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python junit_summary.py <title> <junit.xml>", file=sys.stderr)
        return 2
    title, report = sys.argv[1], Path(sys.argv[2])
    if not report.is_file():
        # Tests crashed before writing the report: say so instead of failing silently.
        print(f"## {title} tests — ⚠️ no report\n\n`{report}` was not generated.\n")
        return 0
    print(render(title, parse_report(report)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
