"""The feature-to-minimum-version matrix is complete and pinnable.

The matrix exists so consumers converge deliberately rather than re-pinning in
lockstep (Fabric#23). That only works if every shipped feature has a row: a
family with no stated minimum is one a consumer cannot plan around, and it goes
missing in exactly the way the `v0.9.0rc2` families did -- shipped, then absent
from the matrix until someone happened to look.

This checks the matrix against the package, and the versions it names against
the package version -- and, in the second half of the file, against release
history. A minimum is a claim that the named release is the *first* one
carrying the feature. That claim is checked against the three records of
history that exist independently of the table: the `CHANGELOG.md` headings,
the per-tag file lists in `release/v*.digest.json`, and -- when the checkout
has them -- the git tags themselves. None of the three is the table, so the
check is not the table restating itself.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from azazel_fabric.version import __version__

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "src" / "azazel_fabric"
DOC_PATH = REPO_ROOT / "docs" / "provisioning-contracts.md"
HEADING = "## Feature-to-minimum-Fabric-version matrix"

#: `0.9.0`, `0.9.0rc2`, `1.0.0` — the shapes `version.py` and the tags use.
#: ``.devN`` is recognized and then discarded: a development build *toward*
#: ``0.9.0rc3`` contains what ``0.9.0rc3`` will contain, which is what makes a
#: row naming that candidate satisfiable from ``main``. Whether the tree really
#: is that candidate yet is the release digest gate's question
#: (``tests/test_release_candidate_digest.py``), not this file's -- and it is
#: answered there against bytes rather than against a version string.
VERSION = re.compile(
    r"^(?P<release>\d+\.\d+\.\d+)(?:(?P<kind>rc|a|b)(?P<serial>\d+))?(?:\.dev\d+)?$"
)

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


# ---------------------------------------------------------------------------
# The minimums against release history
# ---------------------------------------------------------------------------

CHANGELOG_PATH = REPO_ROOT / "CHANGELOG.md"
RELEASE_DIR = REPO_ROOT / "release"

#: The module whose first appearance marks each feature, relative to the
#: package root. Kept by hand because the feature id is not derivable from the
#: path (`deception-observation` is a file inside `deception_contracts`), and
#: checked against the matrix in both directions so it cannot go stale.
FEATURE_MODULES: dict[str, str] = {
    "schema/v1.0": "schema/__init__.py",
    "cti-contracts/v1.0": "cti_contracts/__init__.py",
    "view/v1.0": "view/__init__.py",
    "deception-contracts/v0.1": "deception_contracts/__init__.py",
    "deception-observation/v0.1": "deception_contracts/observation.py",
    "engagement-contracts/v0.1": "engagement_contracts/__init__.py",
    "decision-signing/v0.1": "deception_contracts/decision_signing.py",
    "outcome-contracts/v0.1": "outcome_contracts/__init__.py",
    "provisioning-contracts/v0.1": "provisioning_contracts/__init__.py",
    "mio-contracts/v0.1": "mio_contracts/__init__.py",
    "defensive-state/v0.1": "schema/defensive_state.py",
    "effect-contracts/v0.1": "effect_contracts/__init__.py",
    "external-security-contracts/v0.1": "external_security_contracts/__init__.py",
}

#: The package directory has had two names. `v0.1.0` and `v0.2.0` shipped as
#: `azazel_common`; the rename to `azazel_fabric` is `v0.3.0`.
PACKAGE_DIRS = ("src/azazel_fabric", "src/azazel_common")

_HEADING = re.compile(r"^## \[(?P<version>[^\]]+)\](?P<rest>.*)$", re.MULTILINE)


def _released_versions() -> list[str]:
    """Every version `CHANGELOG.md` records as released, oldest first.

    `[Unreleased]` is not a version, and `0.7.0` is recorded as never released
    (there is no tag): neither is something a consumer could have pinned.
    """

    text = CHANGELOG_PATH.read_text(encoding="utf-8")
    versions = [
        match.group("version")
        for match in _HEADING.finditer(text)
        if match.group("version") != "Unreleased"
        and "NEVER RELEASED" not in match.group("rest")
    ]
    return sorted(versions, key=_ordered)


def _unpublished_target() -> str | None:
    """The version `main` is building toward, when it is a `.devN` build."""
    if ".dev" not in __version__:
        return None
    return __version__.split(".dev", 1)[0]


def _predecessor(version: str, released: list[str]) -> str | None:
    earlier = [v for v in released if _ordered(v) < _ordered(version)]
    return earlier[-1] if earlier else None


def _digest_files() -> dict[str, set[str]]:
    files: dict[str, set[str]] = {}
    for path in sorted(RELEASE_DIR.glob("v*.digest.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        files[record["package_version"]] = set(record["files"])
    return files


def _in_file_list(module: str, listed: set[str]) -> bool:
    return any(f"{root}/{module}" in listed for root in PACKAGE_DIRS)


def test_every_row_names_the_module_that_marks_it(rows):
    feature_ids = {row[0] for row in rows}

    assert set(FEATURE_MODULES) == feature_ids, (
        f"rows without a marker module: {sorted(feature_ids - set(FEATURE_MODULES))}; "
        f"marker modules without a row: {sorted(set(FEATURE_MODULES) - feature_ids)}. "
        "A row the history checks below cannot locate is a row whose minimum "
        "nothing verifies."
    )
    missing = [m for m in FEATURE_MODULES.values() if not (PACKAGE_ROOT / m).is_file()]
    assert missing == [], f"marker modules absent from this tree: {missing}"


def test_every_minimum_is_a_release_the_changelog_records(rows):
    """A minimum must be a release that happened, or the one `main` is building.

    This is what makes the `0.7.0` hole visible: that heading exists but says
    it was never released, so a row naming it would be a minimum no consumer
    could ever have pinned.
    """

    released = set(_released_versions())
    target = _unpublished_target()
    unrecorded = [
        (row[0], row[1]) for row in rows if row[1] not in released and row[1] != target
    ]

    assert unrecorded == [], (
        f"rows whose minimum CHANGELOG.md does not record as released: {unrecorded}"
    )


def test_a_row_naming_the_unpublished_target_says_so(rows):
    target = _unpublished_target()
    if target is None:
        pytest.skip("this tree is a release, not a development build")

    unmarked = [
        row[0] for row in rows if row[1] == target and "unpublished" not in row[2].lower()
    ]
    assert unmarked == [], (
        f"rows naming the not-yet-cut v{target} whose Notes do not say "
        f"'unpublished': {unmarked}. A reader cannot pin a tag that does not exist."
    )


def test_every_minimum_agrees_with_the_release_digests(rows):
    """The per-tag file lists are history recorded in this tree.

    For a minimum that has a digest, the feature must be in it; when the
    release before it also has one, the feature must be absent there --
    otherwise the minimum is later than the feature's real first release and
    the table is telling consumers to pin higher than they need. A feature
    whose minimum is newer than every digest must be in none of them.
    """

    digests = _digest_files()
    assert digests, "no release digest found, so this checked nothing"
    released = _released_versions()
    newest = max(digests, key=_ordered)
    problems = []

    for feature, minimum, _ in rows:
        module = FEATURE_MODULES[feature]
        if minimum in digests and not _in_file_list(module, digests[minimum]):
            problems.append(f"{feature}: not in the v{minimum} digest it names")
        previous = _predecessor(minimum, released)
        if previous in digests and _in_file_list(module, digests[previous]):
            problems.append(f"{feature}: already in v{previous}, before its minimum v{minimum}")
        if _ordered(minimum) > _ordered(newest):
            early = sorted(
                (v for v, listed in digests.items() if _in_file_list(module, listed)),
                key=_ordered,
            )
            if early:
                problems.append(f"{feature}: minimum v{minimum} but already in v{early[0]}")

    assert problems == [], "; ".join(problems)


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args], capture_output=True, text=True, timeout=60
    )


def _tags() -> set[str]:
    try:
        result = _git("tag", "--list", "v*")
    except (OSError, subprocess.SubprocessError):
        return set()
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _tag_has(tag: str, module: str) -> bool:
    return any(_git("cat-file", "-e", f"{tag}:{root}/{module}").returncode == 0 for root in PACKAGE_DIRS)


def test_every_minimum_is_the_first_tag_carrying_its_feature(rows):
    """The tags are the history; the digests above cover only the `rc` line.

    Skipped, not passed, when the checkout has no tags (a source tarball, a
    shallow local clone): absence of history is not agreement with it. Under
    CI (`CI` set) a missing tag set is a misconfigured checkout instead --
    `actions/checkout` defaults to a depth-1 clone with no tags -- and a skip
    there would report success for a check that never ran, so it fails.
    """

    tags = _tags()
    if not tags:
        if os.environ.get("CI"):
            pytest.fail(
                "CI is set but the checkout has no release tags, so the "
                "feature minimums were not checked against history. Check out "
                "with full history and tags (fetch-depth: 0, fetch-tags: true)."
            )
        pytest.skip("no release tags in this checkout")

    released = _released_versions()
    target = _unpublished_target()
    # A release tree is prepared before its tag exists: the digest is signed on
    # the branch, the branch merges, and the tag is cut at the merge commit
    # (docs/release-signing.md). Between the merge and the tag, the version this
    # tree *is* has no tag yet, and that is the procedure working rather than a
    # minimum naming a release that never happened. Only that one version is
    # excused, only from "is a tag"; once the tag exists it is checked in full.
    releasing = None if ".dev" in __version__ else __version__
    problems = []

    for feature, minimum, _ in rows:
        module = FEATURE_MODULES[feature]
        tag = f"v{minimum}"
        if minimum == target:
            if tag in tags:
                problems.append(f"{feature}: v{minimum} is tagged but the row says unpublished")
            latest = max((v for v in released if f"v{v}" in tags), key=_ordered, default=None)
            if latest is not None and _tag_has(f"v{latest}", module):
                problems.append(f"{feature}: already in v{latest}, before unpublished v{minimum}")
            continue
        if tag not in tags:
            if minimum != releasing:
                problems.append(f"{feature}: minimum {tag} is not a tag")
                continue
        elif not _tag_has(tag, module):
            problems.append(f"{feature}: {tag} does not contain {module}")
        previous = _predecessor(minimum, released)
        if previous is not None and f"v{previous}" in tags and _tag_has(f"v{previous}", module):
            problems.append(f"{feature}: already in v{previous}, before its minimum {tag}")

    assert problems == [], "; ".join(problems)


def test_the_history_checks_can_fail():
    """Non-vacuity: a minimum set one release too late is caught."""
    digests = _digest_files()
    released = _released_versions()
    module = FEATURE_MODULES["effect-contracts/v0.1"]

    # effect_contracts first shipped in rc2; claiming rc3 must be refused.
    previous = _predecessor("0.9.0rc3", released)
    assert previous == "0.9.0rc2"
    assert _in_file_list(module, digests[previous])
    # ... and claiming rc1 must be refused too.
    assert not _in_file_list(module, digests["0.9.0rc1"])
