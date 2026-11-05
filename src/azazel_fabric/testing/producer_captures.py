"""Records that real producers emitted, for consumers to test against (Fabric#23).

Every other golden vector in ``azazel_fabric.testing`` is built by Fabric from
its own models. That proves the models agree with themselves; it does not prove
that what Azazel-Edge or Azazel-Deception actually emits is what a consumer
reads. These are the other half: each payload is the output of a named
producer function in a named product repository at a recorded commit, called
with the inputs that product's own tests use, captured byte for byte.

Use them in a consumer's test suite: feed the payload to the code that parses
or validates what it receives, and assert what it does with it.

    from azazel_fabric.testing import load_producer_capture, producer_capture_names

    for name in producer_capture_names(family="effect_contracts"):
        payload = load_producer_capture(name)
        ...

**What is promised.** The functions and the names they return are part of the
``azazel_fabric.testing`` surface. The bytes under a name never change: a
refreshed capture from a newer producer commit is added under a new name
(``..._v1``), and the old one stays. A capture is a record of what one commit
emitted, not a statement that the producer still emits exactly that.

**What is not.** A capture is not a certification of either product, and its
presence here does not grant any authority -- the payloads are descriptive
contract records like any other. ``deception_transition_signed`` carries a
transport MAC made with :data:`GOLDEN_DECISION_SIGNATURE_KEY`, a published test
constant that is no product's operational key; ``decision_signature`` is not a
model field, so validate the record with the MAC removed and check the MAC
separately (:func:`producer_capture_body`).

Provenance for each capture (producer function, input source, commit) is in
``tests/fixtures/producer_captures/<product>/provenance.json`` and
``tools/producer_captures/<product>/README.md``; :func:`producer_capture_provenance`
returns the same fields.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from azazel_fabric.testing._producer_capture_data import CAPTURES as _CAPTURES
from azazel_fabric.testing.golden import GOLDEN_DECISION_SIGNATURE_KEY

#: The transport MAC field a signed decision carries beside its model fields.
SIGNATURE_FIELD = "decision_signature"

_PROVENANCE_FIELDS = (
    "product",
    "repository",
    "commit",
    "fabric_pin",
    "captured",
    "family",
    "model",
    "producer",
    "input_from_product_tests",
    "list",
    "signed",
)

__all__ = [
    "GOLDEN_DECISION_SIGNATURE_KEY",
    "SIGNATURE_FIELD",
    "load_producer_capture",
    "producer_capture_body",
    "producer_capture_names",
    "producer_capture_provenance",
]


def producer_capture_names(*, family: str | None = None, product: str | None = None) -> tuple[str, ...]:
    """Every capture name, optionally only one contract family or one producer."""

    return tuple(
        sorted(
            name
            for name, record in _CAPTURES.items()
            if (family is None or record["family"] == family)
            and (product is None or record["product"] == product)
        )
    )


def _record(name: str) -> dict[str, Any]:
    try:
        return _CAPTURES[name]
    except KeyError:
        raise KeyError(f"no producer capture named {name!r}") from None


def load_producer_capture(name: str) -> Any:
    """The captured payload, exactly as the producer emitted it (a fresh copy)."""

    return json.loads(_record(name)["payload_json"])


def producer_capture_body(name: str) -> Any:
    """The payload as its Fabric model validates it.

    The same as :func:`load_producer_capture` except for a signed decision, whose
    transport MAC (:data:`SIGNATURE_FIELD`) is removed because it is not a model
    field.
    """

    payload = load_producer_capture(name)
    if _record(name)["signed"]:
        payload = {key: value for key, value in payload.items() if key != SIGNATURE_FIELD}
    return payload


def producer_capture_provenance(name: str) -> dict[str, Any]:
    """Where the capture came from: product, commit, producer, model, family."""

    record = _record(name)
    return copy.deepcopy({field: record[field] for field in _PROVENANCE_FIELDS})
