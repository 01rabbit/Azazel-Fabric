from __future__ import annotations

import json
from pathlib import Path

from azazel_fabric.outcome_contracts import ExecutionRefV0, canonical_fact_json


FIXTURE = Path(__file__).parent / "fixtures" / "outcome" / "gadget_execution_v0.json"


def test_gadget_execution_golden_fixture_is_valid_fabric_fact():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    fact = ExecutionRefV0.model_validate(payload)
    assert fact.producer_product == "azazel-gadget"
    assert fact.execution_ref == "gadget-execution-91f976eb55c60d75a17d8272"
    assert json.loads(canonical_fact_json(fact)) == payload
