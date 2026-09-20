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
#: The three answers a family's row may give.
#:
#: `**experimental**` is not a third grade of adoption. It says the family is
#: outside the R1c gate entirely, which the gate's own sentence has assumed
#: since it was written ("per non-experimental contract family") without ever
#: naming one. A verdict of `not met` on a family nobody intends to build is a
#: gap that will never close, and reads as work outstanding.
VERDICTS = {"**met**", "not met", "**experimental**"}

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
    # The release table, not the document. The docstring has said so since
    # this test was written and the implementation scanned everything, which
    # only showed up once a second table in this document keyed its rows on
    # tag literals too -- and then reported the new table as a duplicate
    # release row. A check that is narrower in its docstring than in its code
    # fails on the wrong thing.
    rows = [
        line
        for line in _release_table(text).splitlines()
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


#: The header of the release history table, used to find it.
_RELEASE_TABLE_HEADER = "| Release | Contract addition | Compatibility effect |"


def _release_table(text: str) -> str:
    """The release history table alone, header to blank line."""

    assert _RELEASE_TABLE_HEADER in text, (
        f"docs/{DOC_PATH.name} lost its release history table header"
    )
    after = text.split(_RELEASE_TABLE_HEADER, 1)[1]
    lines = []
    for line in after.splitlines():
        stripped = line.strip()
        if not stripped:
            # The split leaves an empty first element before the separator
            # row. Breaking on it ends the table before it starts, which is
            # how the first version of this returned nothing and reported the
            # release table as missing.
            if lines:
                break
            continue
        if not stripped.startswith("|"):
            break
        lines.append(line)
    assert lines, f"docs/{DOC_PATH.name} release table header has no rows under it"
    return "\n".join(lines)


def _published_tags() -> set[str]:
    """Every tag ``release/`` records a manifest for."""

    return {
        "v" + match.group("version")
        for path in RELEASE_DIR.glob("*.digest.json")
        if (match := PUBLISHED_MANIFEST.fullmatch(path.name))
    }


def _release_history_rows() -> list[tuple[str, str]]:
    """``(tag, first cell)`` for each row of the release history table."""

    rows: list[tuple[str, str]] = []
    for line in _release_table(DOC_PATH.read_text(encoding="utf-8")).splitlines():
        stripped = line.strip()
        if not stripped.startswith("| `v"):
            continue
        cell = stripped.split("|")[1].strip()
        tag = re.match(r"`(v[^`]+)`", cell)
        if tag is not None:
            rows.append((tag.group(1), cell))
    return rows


def test_a_release_row_for_an_unpublished_tag_says_so():
    """`v0.9.0rc4` is documented before it is cut, and that is new here.

    Every row before it described a tag that already existed, so "appears in
    the table" and "can be pinned" meant the same thing. They no longer do. A
    reader who pins `v0.9.0rc4` today resolves to nothing -- the same failure
    `v0.7.0` records, one row of this table earning its own line of prose
    because nobody wrote it down in time.

    Derived from ``release/`` rather than from a list kept here, so publishing
    a tag is what retires its marker: a manifest appearing makes this test
    require the word to go, rather than leaving it to be noticed.
    """

    published = _published_tags()
    rows = _release_history_rows()
    assert rows, f"docs/{DOC_PATH.name} lost its release history table"

    # `release/` began at the first candidate, so it is evidence only from
    # there forward. `v0.5.0` through `v0.8.0` are published and have no
    # manifest, and reading that absence as "unpublished" is the mistake this
    # file exists to catch in the other direction: silence is not a claim.
    # This test therefore says nothing about a tag older than the oldest
    # manifest, rather than guessing about it.
    floor = min(_sortable(tag.lstrip("v")) for tag in published)

    for tag, cell in rows:
        if _sortable(tag.lstrip("v")) < floor:
            continue
        marked = "unpublished" in cell.lower() or "never released" in cell.lower()
        if tag in published:
            assert not marked, (
                f"{tag} has a manifest in release/ but its row still calls it "
                "unpublished; a reader is being told not to pin a tag that exists"
            )
        else:
            assert marked, (
                f"the release history has a row for {tag}, which release/ has no "
                "manifest for, and does not say so. A consumer that pins it "
                "resolves to nothing -- which is the failure the v0.7.0 row in "
                "this same table exists to record."
            )


def test_every_experimental_family_says_why_it_is_one(rows):
    """Outside the gate is a position, and a position has a reason.

    `**experimental**` removes a family from what blocks `v0.9.0`. That is a
    decision with consequences for the release, so the row alone is not
    enough: the document has to say what makes the family experimental and
    what it means for the stable tag. Without that, the verdict is
    indistinguishable from a convenient way to stop a row reading `not met`.
    """

    text = DOC_PATH.read_text(encoding="utf-8")
    section = text.split(MATRIX_HEADING, 1)[1]

    experimental = [row[0].strip("`") for row in rows if row[3] == "**experimental**"]
    assert experimental, (
        "no family is marked experimental, yet the gate's own sentence says it "
        "applies 'per non-experimental contract family'. Either mark them or "
        "drop the qualifier"
    )

    # The explanation block, taken by its lead-in rather than by guessing
    # which of two identically-shaped rows is which. Both tables open a row
    # with the same `| \`family\` |`, so a line-shape heuristic picks the wrong
    # one -- it did, on the first attempt at this test.
    lead_in = "**Which families are experimental, stated rather than implied.**"
    assert lead_in in section, (
        f"docs/{DOC_PATH.name} lost the block explaining which families are "
        "experimental; the verdict then appears with no stated reason"
    )
    explanation = section.split(lead_in, 1)[1].split("| Family | Producers", 1)[0]

    for family in experimental:
        assert f"`{family}`" in explanation, (
            f"{family} is marked experimental in the adoption matrix and the "
            "block above it does not say why. A family excused from the gate "
            "needs its reason written where the gate is."
        )
        assert "stable tag" in explanation, (
            "the explanation does not say what experimental means for the "
            "stable tag, which is the only consequence a reader is after"
        )


def test_an_experimental_family_is_not_one_that_simply_has_no_adopter(rows):
    """The distinction this verdict would otherwise erase.

    `provisioning_contracts` has no producer and no consumer either, and it is
    gated: Azazel-Nexus consumes `InterfaceIdentity` from it today, so the
    missing half is a gap. Marking a family experimental because its row is
    empty would turn every unfinished family into a design position.
    """

    for family, producers, consumers, verdict in rows:
        if verdict != "**experimental**":
            continue
        assert family.strip("`") in {"cti_contracts", "mio_contracts"}, (
            f"{family} is newly marked experimental. That takes it out of the "
            "R1c gate, so it is a release decision rather than a table edit: "
            "record it where the gate is defined and update this test "
            "deliberately."
        )
