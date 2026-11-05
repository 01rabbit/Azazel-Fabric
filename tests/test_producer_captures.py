"""Producer captures: real producer output, kept honest (Fabric#23, B2).

`azazel_fabric.testing.producer_captures` publishes what Azazel-Edge and
Azazel-Deception actually emitted. Each test here is one way that publication
could stop meaning that: the embedded bytes drifting from the reviewed JSON, a
capture no longer validating as the model it claims, provenance going missing,
or a signed record that no longer verifies.
"""

from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path

import pytest

from azazel_fabric.deception_contracts import verify_decision_signature
from azazel_fabric.testing import (
    load_producer_capture,
    producer_capture_body,
    producer_capture_names,
    producer_capture_provenance,
)
from azazel_fabric.testing.golden import GOLDEN_DECISION_SIGNATURE_KEY
from azazel_fabric.testing.producer_captures import SIGNATURE_FIELD

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "tests" / "fixtures" / "producer_captures"
STABLE_FAMILIES = ("deception_contracts", "effect_contracts", "engagement_contracts", "outcome_contracts")

sys.path.insert(0, str(REPO / "tools" / "producer_captures"))

from embed import OUT, build  # noqa: E402

NAMES = producer_capture_names()


def _model(dotted: str):
    module, _, attr = dotted.rpartition(".")
    return getattr(importlib.import_module(module), attr)


def test_the_embedded_data_is_the_reviewed_json():
    assert OUT.read_text(encoding="utf-8") == build(), (
        "src/azazel_fabric/testing/_producer_capture_data.py is out of date with "
        "tests/fixtures/producer_captures/; run python3 tools/producer_captures/embed.py"
    )


def test_every_fixture_has_provenance_and_every_provenance_entry_a_fixture():
    for product_dir in sorted(p for p in FIXTURES.iterdir() if p.is_dir()):
        provenance = json.loads((product_dir / "provenance.json").read_text(encoding="utf-8"))
        files = {p.stem for p in product_dir.glob("*.json")} - {"provenance"}
        assert files == set(provenance["captures"]), product_dir.name
        assert re.fullmatch(r"[0-9a-f]{40}", provenance["commit"]), "a capture names the full commit it came from"


def test_every_stable_family_has_real_producer_output():
    for family in STABLE_FAMILIES:
        assert producer_capture_names(family=family), family


def test_the_stable_families_with_two_producers_carry_both():
    """effect, deception and outcome are produced by both Edge and Deception
    (docs/release-compatibility.md); a capture set from one of them alone
    would test a consumer against half its senders."""

    for family in ("deception_contracts", "effect_contracts", "outcome_contracts"):
        products = {producer_capture_provenance(n)["product"] for n in producer_capture_names(family=family)}
        assert products == {"edge", "deception"}, (family, products)


@pytest.mark.parametrize("name", NAMES)
def test_each_capture_validates_as_the_model_it_names(name):
    provenance = producer_capture_provenance(name)
    model = _model(provenance["model"])
    assert provenance["model"].startswith(f"azazel_fabric.{provenance['family']}.")
    body = producer_capture_body(name)
    records = body if provenance["list"] else [body]
    assert records, "an empty capture tests nothing"
    for record in records:
        model.model_validate(record)


@pytest.mark.parametrize("name", NAMES)
def test_signatures_are_exactly_where_provenance_says(name):
    payload = load_producer_capture(name)
    if producer_capture_provenance(name)["signed"]:
        assert verify_decision_signature(payload, GOLDEN_DECISION_SIGNATURE_KEY)
    else:
        records = payload if isinstance(payload, list) else [payload]
        assert all(SIGNATURE_FIELD not in record for record in records)


@pytest.mark.parametrize("name", NAMES)
def test_no_capture_carries_an_address(name):
    """Captured with test inputs; an IP literal here would mean a real one leaked in."""

    text = json.dumps(load_producer_capture(name))
    assert not re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)


def test_a_loaded_capture_is_a_copy():
    name = NAMES[0]
    first = load_producer_capture(name)
    if isinstance(first, dict):
        first["mutated"] = True
    else:
        first.append("mutated")
    assert load_producer_capture(name) != first


def test_an_unknown_name_is_refused():
    with pytest.raises(KeyError):
        load_producer_capture("edge/no_such_capture_v0")
