"""`.github/workflows/release-guard.yml` keeps the property it exists for.

It is the only thing that acts on a Release `release.yml` did not make (see
docs/release-signing.md, "A Release is made by release.yml, never by hand").
Each check below is a way it could quietly stop doing that: firing on the wrong
event, exempting the wrong author, losing the permission it needs, or doing
something other than returning the Release to draft.
"""

from __future__ import annotations

from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release-guard.yml"


def _text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_it_fires_on_every_published_release():
    text = _text()
    assert "  release:\n    types: [published]" in text


def test_it_exempts_only_the_release_workflow():
    text = _text()
    assert "if: github.event.release.author.login != 'github-actions[bot]'" in text
    assert text.count("github-actions[bot]") >= 1


def test_it_returns_the_release_to_draft_and_never_deletes_it():
    text = _text()
    assert '-X PATCH "repos/$REPO/releases/$RELEASE_ID" -F draft=true' in text
    assert "-X DELETE" not in text
    # The tag is the record of what was cut; the guard never moves or removes it.
    assert "git push" not in text and "refs/tags" not in text


def test_it_has_the_permissions_it_needs_and_no_more():
    text = _text()
    block = text.split("permissions:", 1)[1].split("jobs:", 1)[0]
    lines = {line.strip() for line in block.splitlines() if line.strip()}
    assert lines == {"contents: write", "issues: write"}


def test_it_tells_the_owner():
    assert "gh issue create" in _text()
