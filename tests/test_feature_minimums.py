"""The feature-to-minimum-version matrix is complete and pinnable.

The matrix exists so consumers converge deliberately rather than re-pinning in
lockstep (Fabric#23). That only works if every shipped feature has a row: a
family with no stated minimum is one a consumer cannot plan around, and it goes
missing in exactly the way the `v0.9.0rc2` families did -- shipped, then absent
from the matrix until someone happened to look.

This checks the matrix against the package, and the versions it names against
the package version. It does **not** check that a named minimum is truly the
first release carrying the feature: that is a fact about release history, which
lives in `CHANGELOG.md` and the tags, and a test asserting it from inside one
tree would only be restating the table it is checking.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from azazel_fabric.version import __version__

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "src" / "azazel_fabric"
DOC_PATH = REPO_ROOT / "docs" / "provisioning-contracts.md"
HEADING = "## Feature-to-minimum-Fabric-version matrix"

#: `0.9.0`, `0.9.0rc2`, `1.0.0` — the shapes `version.py` and the tags use.
VERSION = re.compile(r"^(?P<release>\d+\.\d+\.\d+)(?:(?P<kind>rc|a|b)(?P<serial>\d+))?$")

#: Families whose row carries a different feature id than the module name, or
#: whose surface is documented under another row. Each entry needs a reason:
#: an exemption without one is how a family quietly stops being covered.
ROW_ALIASES: dict[str, str] = {
    # The CTI family predates the `vX.Y` feature-id convention and has shipped
    # under `cti-contracts/v1.0` since 0.1.0; renaming the row would break the
    # id consumers already record in a CompatibilityManifest.
    "cti_contracts": "cti-contracts/v1.0",
}


def _shipped_families() -> set[str]:
    return {
        path.name
        for path in PACKAGE_ROOT.iterdir()
        if path.is_dir() and path.name.endswith("_contracts")
    }


def _matrix_rows() -> list[tuple[str, str, str]]:
    text = DOC_PATH.read_text(encoding="utf-8")
    assert HEADING in text, f"{DOC_PATH.name} lost its feature-minimum matrix"
    section = text.split(HEADING, 1)[1]

    rows: list[tuple[str, str, str]] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) != 3:
            continue
        if cells[0] == "Feature ID" or set(cells[0]) <= {"-", ":", " "}:
            continue
        rows.append((cells[0].strip("`"), cells[1].strip("`"), cells[2]))
    assert rows, "the feature-minimum matrix has no data rows"
    return rows


def _ordered(version: str) -> tuple:
    """Sortable form. A final release sorts after every candidate of itself."""
    match = VERSION.fullmatch(version)
    assert match is not None, f"unparseable version {version!r}"
    release = tuple(int(part) for part in match.group("release").split("."))
    if match.group("kind") is None:
        return release + (float("inf"),)
    return release + (int(match.group("serial")),)


@pytest.fixture(scope="module")
def rows() -> list[tuple[str, str, str]]:
    return _matrix_rows()


def test_every_shipped_contract_family_has_a_minimum_version(rows):
    feature_ids = {row[0] for row in rows}
    missing = []
    for family in sorted(_shipped_families()):
        expected = ROW_ALIASES.get(family, f"{family.replace('_', '-')}/v0.1")
        if expected not in feature_ids:
            missing.append(f"{family} (looked for {expected!r})")

    assert missing == [], (
        f"these families ship with no row in the feature-minimum matrix: "
        f"{missing}. A consumer cannot plan a pin around a feature whose "
        "minimum version is unstated. Add a row, or -- if the feature is "
        "documented under a differently named row -- record that in "
        "ROW_ALIASES with the reason."
    )


def test_every_alias_names_a_family_that_exists(rows):
    """An exemption that outlives its family stops covering anything."""
    stale = set(ROW_ALIASES) - _shipped_families()

    assert stale == set(), (
        f"ROW_ALIASES exempts families the package no longer has: {sorted(stale)}"
    )


def test_every_alias_points_at_a_row_that_exists(rows):
    feature_ids = {row[0] for row in rows}
    dangling = {
        family: feature_id
        for family, feature_id in ROW_ALIASES.items()
        if feature_id not in feature_ids
    }

    assert dangling == {}, (
        f"ROW_ALIASES redirects to rows the matrix does not have: {dangling}. "
        "An alias pointing nowhere silently exempts its family."
    )


def test_every_minimum_is_a_version_a_consumer_could_pin(rows):
    offenders = [(row[0], row[1]) for row in rows if VERSION.fullmatch(row[1]) is None]

    assert offenders == [], (
        f"rows whose minimum is not an exact version: {offenders}. "
        "A range or a branch name is not something a consumer can pin."
    )


def test_no_row_requires_a_version_this_package_is_not_yet(rows):
    """A minimum newer than the package is a promise nothing can satisfy.

    This is the check that would have caught the `v0.9.0rc2` families being
    added to the package while the matrix still stopped at `rc1` -- in the
    other direction, where a row runs ahead of what ships.
    """

    packaged = _ordered(__version__)
    ahead = [
        (row[0], row[1]) for row in rows if _ordered(row[1]) > packaged
    ]

    assert ahead == [], (
        f"rows naming a minimum newer than this package (v{__version__}): "
        f"{ahead}. Until the package is that version, no consumer can satisfy "
        "the row -- state the version that actually carries the feature."
    )


def test_a_candidate_minimum_is_marked_as_one(rows):
    """`0.9.0rc2` promises no stability and the row has to say so.

    A reader scanning the Notes column decides whether to adopt from it. A
    candidate that reads like a stable minimum is the one row that would get
    pinned without the caveat being seen.
    """

    unmarked = [
        (row[0], row[1])
        for row in rows
        if VERSION.fullmatch(row[1]) is not None
        and VERSION.fullmatch(row[1]).group("kind") is not None
        and "candidate" not in row[2].lower()
    ]

    assert unmarked == [], (
        f"candidate minimums whose Notes do not say 'candidate': {unmarked}"
    )
