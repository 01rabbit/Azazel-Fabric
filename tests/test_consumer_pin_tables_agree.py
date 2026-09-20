"""`README.md` and `docs/release-compatibility.md` must name the same pins.

Fabric states each consumer's observed Fabric pin in two places: the
"Consumer status" table in `README.md`, and the consumer pin table in
`docs/release-compatibility.md`. Neither can be checked against the consumer
repositories -- Fabric's CI cannot see them -- so both rest on somebody having
read the source and written down what they saw.

That part stays manual. What does not have to stay manual is the two tables
agreeing with each other, and they had drifted: `release-compatibility.md`
carried a verification note dated 2026-09-20 naming four consumers on a
`v0.9.0` candidate, while `README.md` said `v0.8.0` for all four and described
Azazel-Nexus as a documentation-only repository it had already stopped being.
The Gadget row was stale in both, by four releases, with the note in one of
them explicitly disclaiming it.

Two tables of the same facts, each updated by hand, is one more thing to
forget. This test is what makes forgetting visible: it does not know which
table is right, only that a disagreement is a bug in one of them.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
COMPAT = REPO_ROOT / "docs" / "release-compatibility.md"

#: Written out rather than derived from either table, so a consumer dropped
#: from both still fails here. `Azazel-Gadget` is included deliberately: its
#: row is the one that went four releases stale.
EXPECTED_CONSUMERS = {
    "Azazel-Edge",
    "Azazel-Gadget",
    "Azazel-Knowledge",
    "Azazel-Deception",
    "Azazel-Boot",
    "Azazel-Nexus",
}

#: A pin is a backticked tag, or the explicit absence of one. Nexus declares
#: nothing on purpose, and "no declaration" is a claim this test checks like
#: any other -- an absence that quietly became a version would be drift too.
NO_DECLARATION = "—none—"

_TAG = re.compile(r"`(v\d+\.\d+\.\d+(?:rc\d+)?)`")


def _rows(path: Path, heading: str) -> dict[str, str]:
    """Map consumer -> first tag named in its row, under the given heading."""

    text = path.read_text(encoding="utf-8")
    assert heading in text, f"{path.name} lost the heading {heading!r}"
    section = text.split(heading, 1)[1]

    found: dict[str, str] = {}
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if found:
                break  # the table ended; do not fall into the next one
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        name = re.sub(r"\s*\(AZ-\d+\)\s*$", "", cells[0]).strip()
        if name not in EXPECTED_CONSUMERS:
            continue
        rest = " ".join(cells[1:])
        match = _TAG.search(rest)
        found[name] = match.group(1) if match else NO_DECLARATION
    return found


@pytest.fixture(scope="module")
def readme_pins() -> dict[str, str]:
    return _rows(README, "## Consumer status")


@pytest.fixture(scope="module")
def compat_pins() -> dict[str, str]:
    return _rows(COMPAT, "| Consumer | Observed declaration | Interpretation |")


def test_both_tables_cover_every_consumer(readme_pins, compat_pins):
    """Fails if a consumer is dropped from either table, or from this file.

    Parsing a table and comparing whatever it yielded is how two empty
    findings come out equal. The set is pinned here so an emptied table is a
    failure rather than a vacuous pass.
    """

    assert set(readme_pins) == EXPECTED_CONSUMERS, sorted(EXPECTED_CONSUMERS ^ set(readme_pins))
    assert set(compat_pins) == EXPECTED_CONSUMERS, sorted(EXPECTED_CONSUMERS ^ set(compat_pins))


@pytest.mark.parametrize("consumer", sorted(EXPECTED_CONSUMERS))
def test_the_two_tables_name_the_same_pin(consumer, readme_pins, compat_pins):
    assert readme_pins[consumer] == compat_pins[consumer], (
        f"{consumer}: README says {readme_pins[consumer]}, "
        f"release-compatibility.md says {compat_pins[consumer]}. "
        "One of them was not updated. Neither table is checkable against the "
        "consumer repository from here, so fix it by reading that "
        "repository's dependency declaration, not by copying the other table."
    )


def test_the_declared_absence_is_still_an_absence(readme_pins, compat_pins):
    """Nexus's empty row is a design statement, not a gap to be filled.

    `dependencies = []` is deliberate there. If a tag ever appears in that
    row, it is either a real adoption that both tables and the adoption
    matrix must record, or somebody filled a blank because it looked unfinished.
    """

    assert readme_pins["Azazel-Nexus"] == NO_DECLARATION
    assert compat_pins["Azazel-Nexus"] == NO_DECLARATION


#: The tag inside the install command, which is a bare `@vX.Y.Z` in a fenced
#: shell line rather than a backticked tag in prose. Written as its own
#: pattern because the first version of this test reused the prose pattern,
#: found a backticked tag further down the file, and passed while the command
#: itself said something else entirely.
_PIP_TAG = re.compile(r"Azazel-Fabric\.git@(v\d+\.\d+\.\d+(?:rc\d+)?)")


def test_the_install_example_offers_the_latest_stable_not_a_candidate():
    """`## Install` must not hand a release candidate to a stable consumer.

    The README tells stable consumers to pin "the latest compatible exact
    tag" and then shows a command. A candidate reaching that command would
    put unstable contracts into the path of every reader who copies it,
    which is the opposite of what the sentence promises.
    """

    text = README.read_text(encoding="utf-8")
    assert "## Install" in text
    install = text.split("## Install", 1)[1].split("\n## ", 1)[0]

    tags = _PIP_TAG.findall(install)
    assert tags, "the install section no longer shows an installable tag"
    for tag in tags:
        assert "rc" not in tag, (
            f"the install example offers the candidate {tag}; the sentence "
            "above it promises the latest compatible *stable* tag"
        )
