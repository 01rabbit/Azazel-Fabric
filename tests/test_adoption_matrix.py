"""The R1c adoption matrix in `docs/release-compatibility.md` is not decorative.

R1c — the stable `v0.9.0` — waits on "at least one real producer and two real
consumers" per contract family. That gate is only as good as the record of who
adopted what, and a record kept by hand goes stale silently: the consumer pin
table in the same document said every product was on `v0.8.0` for a day after
four of them had moved.

Fabric's CI cannot see the consumer repositories, so this file deliberately
does **not** try to verify that a cited file produces or consumes anything.
What it enforces is that the table stays a complete, self-consistent set of
citations -- which is the part that rots without anyone noticing.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from azazel_fabric.version import __version__

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "src" / "azazel_fabric"
DOC_PATH = REPO_ROOT / "docs" / "release-compatibility.md"

MATRIX_HEADING = "## Contract family adoption and the R1c gate"

#: A citation names a repository and a path inside it, so a reader can go look.
#: A bare product name ("Azazel-Edge") would assert adoption without saying
#: where, which is the shape of claim this whole file exists to refuse.
CITATION = re.compile(r"^Azazel(?:-[A-Za-z]+)?:`[^`]+`$")

#: The verdicts a row may carry. Anything else is a row nobody has decided.
VERDICTS = {"**met**", "not met"}

EMPTY_CELL = "—"

#: Where the record of what has actually been published lives.
#:
#: The packaged version is **not** that record. Between releases it carries a
#: ``.devN`` suffix and names a candidate that does not exist yet, so asking
#: the compatibility document to describe it would demand prose about an
#: unpublished tag -- and the two checks below did exactly that the first time
#: this package went back to a development version.
RELEASE_DIR = REPO_ROOT / "release"

#: A published candidate is one that shipped a digest manifest.
PUBLISHED_MANIFEST = re.compile(r"^v(?P<version>.+)\.digest\.json$")

#: Sortable form for a published version. ``.devN`` never appears here: a
#: development build publishes no manifest, which is the point.
_ORDER = re.compile(r"^(?P<release>\d+\.\d+\.\d+)(?:(?P<kind>rc|a|b)(?P<serial>\d+))?$")


def _sortable(version: str) -> tuple:
    match = _ORDER.fullmatch(version)
    assert match is not None, f"unparseable published version {version!r}"
    release = tuple(int(part) for part in match.group("release").split("."))
    # A final release sorts after every candidate of itself.
    serial = float("inf") if match.group("kind") is None else int(match.group("serial"))
    return release + (serial,)


def latest_published_tag() -> str:
    """The newest tag this repository has actually published.

    Derived from ``release/``, not from the version string, because a version
    string is a statement of intent and a digest manifest is a record of an
    event. Deleting a manifest to make a check pass would be caught by
    ``tests/test_release_signature.py``, which pins the published candidates
    literally.
    """

    versions = [
        match.group("version")
        for path in RELEASE_DIR.glob("*.digest.json")
        if (match := PUBLISHED_MANIFEST.fullmatch(path.name))
    ]
    assert versions, "release/ records no published candidate"
    return "v" + max(versions, key=_sortable)


def _package_contract_families() -> set[str]:
    """Derived from the package, never listed here.

    A hand-kept list would be one more thing to forget to update, and the
    family it forgot is exactly the one that would ship unrecorded.
    """

    return {
        path.name
        for path in PACKAGE_ROOT.iterdir()
        if path.is_dir() and path.name.endswith("_contracts")
    }


def _matrix_rows() -> list[tuple[str, str, str, str]]:
    """Parse the family table under the R1c heading."""

    text = DOC_PATH.read_text(encoding="utf-8")
    assert MATRIX_HEADING in text, f"{DOC_PATH.name} lost its adoption matrix"
    section = text.split(MATRIX_HEADING, 1)[1]

    rows: list[tuple[str, str, str, str]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if rows:
                break  # the table ended; do not fall into the next one
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 4:
            continue
        if cells[0] == "Family" or set(cells[0]) <= {"-", ":", " "}:
            continue
        rows.append((cells[0], cells[1], cells[2], cells[3]))
    assert rows, "the adoption matrix has no data rows"
    return rows


def _citations(cell: str) -> list[str]:
    if cell == EMPTY_CELL:
        return []
    return [part.strip() for part in cell.split(",")]


@pytest.fixture(scope="module")
def rows() -> list[tuple[str, str, str, str]]:
    return _matrix_rows()


def test_every_contract_family_in_the_package_has_a_row(rows):
    """A family cannot ship without its adoption being stated."""
    documented = {row[0].strip("`") for row in rows}
    missing = _package_contract_families() - documented

    assert missing == set(), (
        f"these contract families ship but are absent from the adoption matrix: "
        f"{sorted(missing)}. A family with no row is a family whose R1c evidence "
        "nobody has had to state -- record it, even if the honest row is 'not met' "
        "with no citations."
    )


def test_no_row_names_a_family_the_package_does_not_have(rows):
    """The reverse direction: a row left behind after a family was renamed."""
    documented = {row[0].strip("`") for row in rows}
    phantom = documented - _package_contract_families()

    assert phantom == set(), (
        f"the adoption matrix names families the package does not contain: "
        f"{sorted(phantom)}"
    )


def test_each_row_carries_a_verdict_someone_decided(rows):
    offenders = [(row[0], row[3]) for row in rows if row[3] not in VERDICTS]

    assert offenders == [], (
        f"rows with an unrecognized R1c verdict: {offenders}. "
        f"Use exactly one of {sorted(VERDICTS)} so the gate reads the same way "
        "for every family."
    )


def test_a_row_claiming_the_gate_is_met_carries_the_evidence_for_it(rows):
    """`met` means 1+ producer and 2+ consumers. Not a judgement call."""
    offenders = []
    for family, producers, consumers, verdict in rows:
        if verdict != "**met**":
            continue
        if len(_citations(producers)) < 1 or len(_citations(consumers)) < 2:
            offenders.append(
                f"{family}: {len(_citations(producers))} producer(s), "
                f"{len(_citations(consumers))} consumer(s)"
            )

    assert offenders == [], (
        f"these rows claim the R1c gate is met without the evidence the gate "
        f"names (one producer, two consumers): {offenders}"
    )


def test_a_row_claiming_the_gate_is_unmet_does_not_already_meet_it(rows):
    """The other direction, which is the one that goes stale.

    A family reaches the gate when its second consumer lands in another
    repository -- nothing in Fabric changes on that day, so nobody comes back
    to update the verdict. This fails then, which is the only reminder there is.
    """

    offenders = []
    for family, producers, consumers, verdict in rows:
        if verdict != "not met":
            continue
        if len(_citations(producers)) >= 1 and len(_citations(consumers)) >= 2:
            offenders.append(family)

    assert offenders == [], (
        f"these rows say the R1c gate is unmet but already cite one producer and "
        f"two consumers: {offenders}. If the citations are right the verdict is "
        "stale; if the verdict is right a citation is wrong. Either way the table "
        "is no longer evidence."
    )


def test_every_citation_points_somewhere_a_reader_can_go(rows):
    offenders = []
    for family, producers, consumers, _ in rows:
        for cell in (producers, consumers):
            for citation in _citations(cell):
                if not CITATION.match(citation):
                    offenders.append(f"{family}: {citation!r}")

    assert offenders == [], (
        f"citations that are not shaped `Repo:`path``: {offenders}. "
        "A product name alone asserts adoption without saying where to check it."
    )


def test_an_empty_cell_is_empty_rather_than_absent(rows):
    """`—` and `` look the same in rendered markdown and mean different things.

    One says "nobody, and we looked"; the other says nothing at all. The gate
    is an argument from absence, so the absence has to be deliberate.
    """

    offenders = [
        (row[0], index)
        for row in rows
        for index, cell in enumerate(row[1:3], start=1)
        if cell == ""
    ]

    assert offenders == [], (
        f"blank cells in the adoption matrix: {offenders}. Write {EMPTY_CELL!r} "
        "to say the absence was checked."
    )


def test_the_release_history_has_a_row_for_the_packaged_version():
    """Catches the failure that produced this file: a release note left behind.

    Checked against the release table specifically, not the document as a
    whole. "Is the version mentioned anywhere" passes on a document whose
    prose still describes the previous candidate as current, because the new
    one appears once in a historical aside.
    """

    text = DOC_PATH.read_text(encoding="utf-8")
    tag = latest_published_tag()
    rows = [
        line for line in text.splitlines()
        if line.strip().startswith(f"| `{tag}`")
    ]

    assert len(rows) == 1, (
        f"the release table in docs/{DOC_PATH.name} has {len(rows)} rows for the "
        f"published tag {tag}, expected exactly one. A release the "
        "compatibility document has not been updated for is a release consumers "
        "will read wrongly."
    )


def test_the_prose_names_the_packaged_version_as_the_latest_published_tag():
    """The sentence a reader actually acts on.

    The release table is a history; one line of prose says which tag is
    current. That line is what goes stale on a release, and a reader who
    believes it pins the wrong thing.
    """

    text = DOC_PATH.read_text(encoding="utf-8")
    section = text.split("## Current Fabric release", 1)
    assert len(section) == 2, f"docs/{DOC_PATH.name} lost its release section"
    prose = section[1].split("##", 1)[0]

    marker = "latest **published** tag"
    assert marker in prose, f"docs/{DOC_PATH.name} no longer states a latest tag"

    # Split on a period followed by whitespace: a bare "." also ends `v0.9.0`,
    # which would truncate the sentence before the tag it names.
    tail = prose.split(marker, 1)[1]
    sentence = re.split(r"\.(?=\s|$)", tail, maxsplit=1)[0]

    tag = latest_published_tag()

    # The *first* tag in the sentence, not merely a tag somewhere in it. This
    # sentence legitimately names older tags after the current one ("...on top
    # of `v0.9.0rc1`"), so "mentions it" is satisfied by a stale answer -- a
    # mutation that made this check ask for the oldest published candidate
    # passed until it was narrowed to the tag the sentence leads with.
    named = re.findall(r"`(v[0-9][^`]*)`", sentence)
    assert named, (
        f"the document's latest-tag sentence names no tag at all: {sentence!r}"
    )
    assert named[0] == tag, (
        f"the document answers 'latest published tag' with {named[0]!r}, but the "
        f"newest manifest in release/ is {tag}. Update the sentence consumers "
        "read to decide what to pin, not only the history table below it."
    )


def test_a_development_version_is_ahead_of_every_published_tag():
    """The relationship the two checks above now rely on.

    They ask the document about ``release/`` rather than about
    ``__version__``. That is only the right question while the package version
    is at or ahead of what has been published. If a version bump ever went
    backwards -- or a candidate were published without the package version
    moving past it -- those checks would quietly start describing the wrong
    release, and this is what refuses to let that happen silently.
    """

    packaged = __version__.split(".dev", 1)[0]
    published = latest_published_tag().lstrip("v")
    assert _sortable(packaged) >= _sortable(published), (
        f"the package is {__version__} but {latest_published_tag()} is already "
        "published. Bump src/azazel_fabric/version.py past the newest published "
        "candidate; a package that claims to be older than a tag it ships the "
        "manifest for cannot be reasoned about."
    )
