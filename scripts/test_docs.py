"""The plugin IS its markdown. These tests check the markdown.

Everything else in this suite tests Python. But nobody using this runs the
Python directly — they read a skill, follow the format it documents, and let
the tooling read the result. So the contract that actually matters is between
the *documentation* and the *parser*, and nothing was checking it.

The failure this prevents is quiet and total: someone improves a table in a
SKILL.md, the parser now disagrees with the documentation, and every artifact
produced by following the docs is unreadable to `/dashboard` and `/conform` —
which report it as a parse problem, blaming the user for doing what they were
told.

Two contracts are checked here:

1. **Every canonical format example in the docs actually parses.** If the
   skill shows it, the parser must accept it.
2. **Every vocabulary the docs teach matches the vocabulary the code enforces**
   — headers, statuses, results, modes, and the gate prerequisite table.
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import conform  # noqa: E402
from dashboard import parse  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = sorted(
    list(ROOT.glob("skills/*/SKILL.md"))
    + list(ROOT.glob("commands/*.md"))
    + list(ROOT.glob("docs/*.md"))
    + [ROOT / "README.md", ROOT / "AGENTS.md"]
)


def _tables(text: str, header: tuple) -> list:
    """Every markdown table in `text` whose header row is exactly `header`.

    Returned as text blocks ready to hand to the real parser — the point is to
    feed the docs' own examples through the production code path, not through a
    re-implementation that could agree with the docs while the parser does not.
    """
    want = "| " + " | ".join(header) + " |"
    found, lines = [], text.splitlines()
    for index, line in enumerate(lines):
        if " ".join(line.split()) != " ".join(want.split()):
            continue
        block = [line]
        for following in lines[index + 1:]:
            if following.strip().startswith("|"):
                block.append(following)
            else:
                break
        found.append("\n".join(block) + "\n")
    return found


class TestDocumentedExamplesParse(unittest.TestCase):
    """Whatever the docs show, the parser must accept."""

    def _check(self, header, parser, label):
        seen = 0
        for path in DOCS:
            text = path.read_text(encoding="utf-8")
            for block in _tables(text, header):
                seen += 1
                with self.subTest(doc=str(path.relative_to(ROOT)), kind=label):
                    parsed = parser(block)
                    self.assertTrue(parsed.header_ok,
                                    f"{path.name}: documented header is not the canonical one")
                    self.assertEqual(
                        parsed.problems, (),
                        f"{path.name} documents a {label} example the parser rejects: "
                        + "; ".join(p.message for p in parsed.problems),
                    )
        # A silent zero would make this whole class vacuous — if the tables are
        # ever renamed or reformatted, this must fail rather than pass having
        # checked nothing.
        self.assertGreater(seen, 0, f"found no {label} examples in the docs to check")

    def test_tasks_examples(self):
        self._check(parse.TASKS_HEADER, parse.parse_tasks, "tasks.md")

    def test_signoff_examples(self):
        self._check(parse.SIGNOFFS_HEADER, parse.parse_signoffs, "signoffs.md")

    def test_test_case_examples(self):
        self._check(parse.TESTS_HEADER, parse.parse_test_cases, "test-cases.md")


class TestDocumentedVocabularyMatchesTheCode(unittest.TestCase):
    """The words the docs teach must be the words the code accepts."""

    SPINE = (ROOT / "skills" / "greenfield-delivery" / "SKILL.md").read_text(encoding="utf-8")
    CASES = (ROOT / "skills" / "business-test-cases" / "SKILL.md").read_text(encoding="utf-8")

    def test_task_statuses(self):
        # The spine documents these as a backticked list in the column rules.
        for status in parse.TASK_STATUSES:
            self.assertIn(f"`{status}`", self.SPINE,
                          f"parser accepts {status!r} but the spine never mentions it")

    def test_no_status_is_documented_that_the_parser_rejects(self):
        documented = set(re.findall(r"`(todo|in-progress|blocked|done|dropped|complete|wip|open)`",
                                    self.SPINE))
        self.assertTrue(
            documented <= parse.TASK_STATUSES,
            f"the spine documents statuses the parser rejects: {documented - parse.TASK_STATUSES}",
        )

    def test_test_results_and_modes(self):
        for value in parse.TEST_RESULTS:
            self.assertIn(f"`{value}`", self.CASES,
                          f"parser accepts result {value!r} but the skill never mentions it")
        for value in parse.TEST_MODES:
            self.assertIn(f"`{value}`", self.CASES,
                          f"parser accepts mode {value!r} but the skill never mentions it")

    def test_headers_are_quoted_in_the_docs_exactly_as_the_parser_wants(self):
        for header, doc in (
            (parse.TASKS_HEADER, self.SPINE),
            (parse.SIGNOFFS_HEADER, self.SPINE),
            (parse.TESTS_HEADER, self.CASES),
        ):
            row = "| " + " | ".join(header) + " |"
            self.assertIn(row, doc, f"the canonical header is not documented verbatim: {row}")


class TestGatePrerequisitesAgree(unittest.TestCase):
    """`commands/gate.md` states which gate blocks which, in a table a human
    reads. `conform.BLOCKED_BY` states the same thing in code. They were
    written separately and nothing made them agree — so a change to either
    would leave the checker enforcing a rule the command does not describe."""

    def test_the_table_in_gate_md_matches_the_checker(self):
        text = (ROOT / "commands" / "gate.md").read_text(encoding="utf-8")
        documented = {}
        for line in text.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) != 2:
                continue
            gate = cells[0].strip("`").lower()
            if gate not in ("discovery", "requirements", "design", "build", "handoff"):
                continue
            blocker = re.sub(r"[^a-zA-Z ]", "", cells[1]).strip().lower()
            if blocker.startswith("none"):
                continue
            # "**Requirements**" -> "requirements"; "**Design** (build has..." -> "design"
            first = blocker.split()[0] if blocker.split() else ""
            if first in ("discovery", "requirements", "design", "build", "handoff"):
                documented[gate] = first
        self.assertEqual(
            documented, conform.BLOCKED_BY,
            "commands/gate.md and conform.BLOCKED_BY disagree about gate order",
        )


class TestReadmeCountsAreTrue(unittest.TestCase):
    """The README states counts about itself. Counts rot silently — it claimed
    290 tests when there were 314, in the one document whose argument is that
    it is precise about what has been verified."""

    README = (ROOT / "README.md").read_text(encoding="utf-8")

    def _claimed(self, noun):
        m = re.search(r"(\d+)\s+" + noun, self.README)
        self.assertIsNotNone(m, f"the README no longer states a {noun} count")
        return int(m.group(1))

    def test_skill_command_and_agent_counts(self):
        for noun, path, pattern in (
            ("skills", "skills", "*/SKILL.md"),
            ("commands", "commands", "*.md"),
            ("subagents", "agents", "*.md"),
        ):
            with self.subTest(noun=noun):
                self.assertEqual(self._claimed(noun),
                                 len(list((ROOT / path).glob(pattern))))

    def test_the_test_count_is_a_floor_that_holds(self):
        # Stated as a floor ("over N"), not an exact figure. An exact count
        # needs a README edit on every commit that adds a test, and the one
        # that gets forgotten is how it came to claim 290 when there were 314.
        # A floor cannot rot upward — it can only become an understatement,
        # and this fails if the suite ever shrinks below it.
        defined = 0
        for path in (ROOT / "scripts").glob("test_*.py"):
            defined += len(re.findall(r"^\s+def test_", path.read_text(encoding="utf-8"), re.M))
        m = re.search(r"over (\d+) tests", self.README)
        self.assertIsNotNone(m, "the README no longer states a test floor")
        floor = int(m.group(1))
        self.assertGreaterEqual(
            defined, floor,
            f"the README claims over {floor} tests; only {defined} are defined",
        )


class TestPluginMetadata(unittest.TestCase):
    """The two JSON files and the README's install line must agree.

    They drifted: the marketplace was still named `greenfield-dev` from when
    this was a private dev marketplace, so anyone adding
    `Abhisrajput/greenfield-delivery` got a marketplace called "greenfield-dev"
    — and "dev" reads as internal on a public listing. Nothing checked it,
    because nothing reads these files except the plugin system.
    """

    MARKET = json.loads((ROOT / ".claude-plugin" / "marketplace.json")
                        .read_text(encoding="utf-8"))
    PLUGIN = json.loads((ROOT / ".claude-plugin" / "plugin.json")
                        .read_text(encoding="utf-8"))
    README = (ROOT / "README.md").read_text(encoding="utf-8")

    def test_the_two_version_numbers_agree(self):
        # The same version is declared in two files. Bumping one and not the
        # other is silent — the plugin system reads one, humans read the other.
        self.assertEqual(self.MARKET["plugins"][0]["version"], self.PLUGIN["version"])

    def test_the_marketplace_is_named_after_the_repository_users_add(self):
        match = re.search(r"/plugin marketplace add \S+/(\S+)", self.README)
        self.assertIsNotNone(match, "the README does not show an install command")
        self.assertEqual(
            self.MARKET["name"], match.group(1),
            "the marketplace name does not match the repository the README "
            "tells people to add",
        )

    def test_the_readme_installs_the_plugin_that_is_declared(self):
        self.assertIn(f"/plugin install {self.PLUGIN['name']}", self.README)
        self.assertEqual(self.MARKET["plugins"][0]["name"], self.PLUGIN["name"])

    def test_nothing_still_calls_itself_internal_or_dev(self):
        # The exact class of leftover that shipped here.
        for field in (self.MARKET["name"], self.MARKET["description"],
                      self.PLUGIN["name"], self.PLUGIN["description"]):
            self.assertNotRegex(field, r"\b(internal|dev|private|wip|test)\b",
                                f"plugin metadata still reads as unreleased: {field!r}")


class TestEverythingIsDiscoverable(unittest.TestCase):
    """A command nobody can find is a command nobody runs. `/qe` shipped
    without a README entry and nothing noticed — check.sh validates that
    commands are well-formed, not that a reader could ever learn they exist."""

    def test_every_command_appears_in_the_readme_command_table(self):
        # Asserted against the TABLE, not the whole file. The first version
        # searched the README for "`/gate`" anywhere, and passed only because
        # an unrelated sentence elsewhere happened to mention it in backticks.
        # Rewriting that sentence broke the test while the command table — the
        # thing it was meant to check — had not changed at all. A test that
        # passes for a reason it does not name will eventually fail for one
        # too.
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        rows = [line for line in readme.splitlines()
                if line.startswith("| `/")]
        self.assertTrue(rows, "no command table found in the README")
        documented = {row.split("`")[1].split()[0].lstrip("/") for row in rows}
        for path in sorted((ROOT / "commands").glob("*.md")):
            with self.subTest(command=path.stem):
                self.assertIn(
                    path.stem, documented,
                    f"/{path.stem} exists but is not in the README's command table",
                )

    def test_every_skill_is_referenced_from_outside_itself(self):
        # A skill nothing routes to is one the model will rarely load.
        others = [p for p in DOCS if "/skills/" not in str(p)] + list(
            ROOT.glob("skills/*/SKILL.md"))
        for skill_dir in sorted((ROOT / "skills").iterdir()):
            if not skill_dir.is_dir():
                continue
            name = skill_dir.name
            with self.subTest(skill=name):
                refs = [p for p in others
                        if p.parent.name != name
                        and f"`{name}`" in p.read_text(encoding="utf-8")]
                self.assertTrue(refs, f"skill {name!r} is referenced from nowhere")


class TestEveryCommandDocumentsItsRefusal(unittest.TestCase):
    """Every command must say what it refuses to do, and name the artifact it
    refuses on.

    An earlier version of this test demanded one exact phrasing — a bolded
    "**If ... stop**" — and failed four commands that document refusals
    perfectly well in other words. `status-report.md` has a whole heading
    reading "Stop if the target is not fully specified"; `gate.md` says "When
    the predecessor is missing, stop and say so". Asserting a template rather
    than the property would have pushed good prose toward a house style for no
    gain, which is the kind of test that makes people stop writing prose.

    So this checks the two things that actually matter: a refusal exists, and
    it is about something concrete."""

    REFUSAL = re.compile(
        r"stop and (say|ask)|stop if|stop,|must stop|do not (proceed|invent|"
        r"guess|fall back|configure|produce|post|publish|overwrit)",
        re.IGNORECASE,
    )

    def test_every_command_states_a_refusal(self):
        for path in sorted((ROOT / "commands").glob("*.md")):
            with self.subTest(command=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertRegex(
                    text, self.REFUSAL,
                    f"{path.name} never says what it refuses to do",
                )

    def test_every_command_names_an_artifact_or_input_it_depends_on(self):
        # A refusal with nothing concrete attached ("do not guess") tells the
        # reader nothing about when it fires.
        for path in sorted((ROOT / "commands").glob("*.md")):
            with self.subTest(command=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertRegex(
                    text, r"`(docs/engagement/[a-z-]+\.md|engagement\.md|"
                          r"signoffs\.md|requirements\.md|tasks\.md|test-cases\.md)`",
                    f"{path.name} names no engagement artifact, so its guards "
                    "cannot be about anything specific",
                )


if __name__ == "__main__":
    unittest.main()
