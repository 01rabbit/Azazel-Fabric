"""Producer captures: real producer output, kept honest (Fabric#23, B2).

`azazel_fabric.testing.producer_captures` publishes what Azazel-Edge and
Azazel-Deception actually emitted. Each test here is one way that publication
could stop meaning that: the embedded bytes drifting from the reviewed JSON, a
capture no longer validating as the model it claims, provenance going missing,
or a signed record that no longer verifies.
"""

from __future__ import annotations

import hashlib
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
from azazel_fabric.testing._producer_capture_data import CAPTURES
from azazel_fabric.testing.producer_captures import SIGNATURE_FIELD

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "tests" / "fixtures" / "producer_captures"
STABLE_FAMILIES = ("deception_contracts", "effect_contracts", "engagement_contracts", "outcome_contracts")

sys.path.insert(0, str(REPO / "tools" / "producer_captures"))

from embed import OUT, build  # noqa: E402

NAMES = producer_capture_names()

#: SHA-256 of every published capture's bytes. This is the "bytes under a name
#: never change" promise made checkable: editing a fixture and re-running
#: embed.py keeps the embedded data and the JSON in agreement, so only a table
#: kept apart from both can notice a name's contents being replaced. A new
#: capture is added here under a new name; an existing line is never edited.
PINNED_SHA256 = {
    "deception/deception_contracts_interaction_observation_export_list_v0": "2c29edc56634056407c78138b50142e2e2fa67558d696eb7c5a43289bae13a49",
    "deception/deception_contracts_interaction_observation_interaction_port_v0": "35883b605fbeb5e1f8653ded4c49e298a6d71ec052dc3b152fee515a9ae2652a",
    "deception/deception_contracts_interaction_observation_reaction_service_v0": "92a1e78a11ff8affc7df3785b1549df9aa4a0615a41481ae5b3e808f1c277729",
    "deception/effect_contracts_effect_observation_active_v0": "6225aaf140e92ee880d97c1331102577f40559ee7c9f1d7963d2cb062f16a992",
    "deception/effect_contracts_effect_observation_terminated_v0": "311f927336e8847d3b53377661296282aedeb185cd15dfe3ccd342d428dd775b",
    "deception/effect_contracts_presented_terrain_ref_live_bound_to_decided_effect_v0": "2fbd6e520060b18a0057a5f3099b2c53b0f76232c054241aa19634767e836fba",
    "deception/effect_contracts_presented_terrain_ref_live_v0": "6c525982fa0cbf35614de04a3e34519602f2cb480ca44cf972efb57f62dec703",
    "deception/effect_contracts_presented_terrain_ref_shadow_stale_v0": "d9e9f3bd7c6a665d8847aec21688fa2aa779d6af8ec12c9e73de5090a8cad1a3",
    "deception/effect_contracts_presented_terrain_ref_synthetic_refs_v0": "de53e1aec82341edb68740fa79f32ac7764ae8d9bfabe8f30af1cb0f7b1f3e06",
    "deception/outcome_contracts_presented_terrain_lifecycle_after_reset_v0": "47de610bc6e381876313e4a8df7fbc965b4ed0f13c6cb416fd0dd3c5d60f8e0d",
    "deception/outcome_contracts_presented_terrain_lifecycle_during_v0": "23b1f643b7f8306e90eab3fd1ff3c538e86faf170a9e18837ac0f24e503b12a7",
    "edge/deception_transition_from_arbiter_v0": "5a4cc7ff30816baf5c2d37bd589c9b475bf6b3aa74ed025add8e3adab9db5a75",
    "edge/deception_transition_signed_v0": "5ec67de5ce61dd0b3617bd515c683f9a96ca9de365d61d7eab3232414150f4aa",
    "edge/deception_transition_unsigned_v0": "2884ec9c56994beac00dcea4d536b39351fce67b730f8d6d0863c647bc5ccc47",
    "edge/effect_isolation_v0": "780821fa9869bcf23bcafe068d25a0d9f87ef1c8eeacf599d77f1f0554938839",
    "edge/effect_traffic_shaping_v0": "96091661940861ff63acd5341637fcc344b16f5cac67d079802411df7d2eef88",
    "edge/engagement_candidate_isolate_v0": "5f1ba19f37fafcdccdb54f5d1f8ebe1053636432954f3336518526ddb396aa54",
    "edge/engagement_candidate_redirect_v0": "bc081428f366138636a2ea6a882bdd9b5275430044b7a126fa72ca947e1a5194",
    "edge/engagement_event_redirect_accepted_v0": "45e9d2a3c91406841b6c6d3f520ce24cde391f3e82f1d4cf37b6f9d4814fbbb3",
    "edge/engagement_event_redirect_downgraded_to_notify_v0": "fb06225c7583a134e546dc28d933ea12259a99cbd9608fa3efa8c668db9ed7f3",
    "edge/outcome_assessment_redirect_v0": "1dcfe1e21aba41869d83231483f41760fd4be2624808aa93f73c9a91348e1b26",
    "edge/outcome_assessment_throttle_v0": "6b644b2c7d92a7bef0e5ad81438ca48ffefc7529b60db4ab0aa222bd279fa654",
    "edge/outcome_execution_redirect_v0": "cf4307d5bb187f7e4e9df47a39231e4610b799f238dbe522b7ea0bf220c215ac",
    "edge/outcome_execution_throttle_v0": "17bb374312f17d8a5daefcbb3d45dc8e41ca45db22352996a3d1f3f9a96252c9",
    "edge/outcome_mechanism_redirect_v0": "9f4ddc1251b94a41ad4f417c541acfb5add4ea53e25d34c6d0e9cb554d75236b",
    "edge/outcome_mechanism_route_change_degraded_to_unknown_v0": "4ccb5fdbee023195eaf2d9a857e00716e4e623b0918546b8e3403ac0117a4522",
    "edge/outcome_mechanism_throttle_observed_v0": "ac30ddfb37a5241de290656afc4b0254019c737ff96b1a45cef45454779fbfa0",
    "edge/outcome_mechanism_throttle_v0": "8d7b262048920ce6cd9bceb83ccd0a8032ecea78b210398e6122d5ff14869243",
    "edge/outcome_outcome_redirect_v0": "62405b0448fa33ed5e52242b89d9602076bd5f9eb427bd8ebcf7736ddbcfdaa9",
    "edge/outcome_outcome_throttle_v0": "80ef9a5bfa5f6d5b7c610629f832f1fc90993346b7b6439cea63a803bdcf24b6",
}


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


def test_the_bytes_under_every_name_are_the_ones_first_published():
    published = set(CAPTURES)
    assert set(PINNED_SHA256) <= published, (
        f"{sorted(set(PINNED_SHA256) - published)} were published and are gone; "
        "a capture name is never removed"
    )
    assert published <= set(PINNED_SHA256), (
        f"{sorted(published - set(PINNED_SHA256))} are not pinned; add their SHA-256 "
        "to PINNED_SHA256 when the capture is first published"
    )
    changed = sorted(
        name
        for name, digest in PINNED_SHA256.items()
        if hashlib.sha256(CAPTURES[name]["payload_json"].encode("utf-8")).hexdigest() != digest
    )
    assert changed == [], (
        f"{changed} changed bytes under an existing name. A refreshed capture is "
        "a new name (..._v1); the old one stays as it was"
    )


@pytest.mark.parametrize("name", NAMES)
def test_every_capture_states_its_full_provenance(name):
    provenance = producer_capture_provenance(name)
    for field in ("product", "repository", "commit", "fabric_pin", "captured", "family", "model", "producer"):
        assert isinstance(provenance[field], str) and provenance[field], field
    for field in ("input_from_product_tests", "list", "signed"):
        assert isinstance(provenance[field], bool), field
