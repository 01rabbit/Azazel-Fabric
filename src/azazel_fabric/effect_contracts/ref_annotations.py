"""Pydantic annotations over the typed refs in :mod:`.refs` (proposal helper).

No second ref grammar lives here: every check delegates to
:func:`azazel_fabric.effect_contracts.refs.require_ref_kind`, which uses
``OPAQUE_REF_PATTERN``. These only bind a ``RefKind`` to a model field.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, StringConstraints

from azazel_fabric.effect_contracts.refs import RefKind, require_ref_kind

#: Upper bound on a typed ref's length (``kind:`` <= 33 + body <= 200).
TYPED_REF_MAX_LENGTH = 240


def typed_ref(kind: RefKind):
    """Annotation: a string that must be an opaque typed ref of ``kind``."""

    def _check(value: str) -> str:
        return require_ref_kind(value, kind, field=kind.value + "_ref")

    return Annotated[
        str,
        StringConstraints(min_length=1, max_length=TYPED_REF_MAX_LENGTH),
        AfterValidator(_check),
    ]


def require_unique(values: tuple[str, ...], *, field: str) -> tuple[str, ...]:
    if len(set(values)) != len(values):
        raise ValueError(f"{field} must not repeat an entry")
    return values
