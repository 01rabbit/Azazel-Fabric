"""Candidate-path *hints* for the Azazel series (`contracts.md` §5).

These are helpers, never authority. A product keeps its own path schema; this
module only offers the series' *conventional* directory names as candidate
lists, so a product that wants to follow the convention (or discover a legacy
sibling's directory) does not have to re-derive the string. Nothing here reads
the filesystem, the environment, or the clock — every function is pure and
deterministic, so the same product name always yields the same candidate list.

Convention (contracts.md §5):

- runtime dir: ``/run/azazel-<product>``
- config dir:  ``/etc/azazel-<product>``
- log dir:     ``/var/log/azazel-<product>``

Legacy compatibility (contracts.md §5): ``azazel-pi`` maps to the ``edge`` path
schema and ``azazel-zero`` maps to the ``gadget`` path schema. Candidate lists
put the canonical path first and any legacy alias path after it, so a caller can
prefer the modern location while still discovering an older one.

**Not authoritative.** Edge has legacy-compat paths that must not be forced
through this helper; a product is free to ignore every candidate returned here.
"""

from __future__ import annotations

from typing import Literal

# Directory *kinds* this module knows the series convention for.
PathKind = Literal["runtime", "config", "log"]

# The base directory each kind lives under, per contracts.md §5.
_BASE_BY_KIND: dict[str, str] = {
    "runtime": "/run",
    "config": "/etc",
    "log": "/var/log",
}

# Canonical product names the series uses in path segments.
KNOWN_PRODUCTS = ("edge", "gadget", "cti")

# Legacy product/codename aliases -> canonical product (contracts.md §5). A
# request for a legacy name resolves to the canonical schema, and the canonical
# candidate list also surfaces the legacy directory as a lower-priority hint so
# an on-disk migration can find it.
LEGACY_ALIASES: dict[str, str] = {
    "azazel-pi": "edge",
    "pi": "edge",
    "azazel-zero": "gadget",
    "zero": "gadget",
}

# Reverse map: canonical product -> legacy path segment(s) still worth probing.
_LEGACY_SEGMENTS: dict[str, tuple[str, ...]] = {
    "edge": ("azazel-pi",),
    "gadget": ("azazel-zero",),
}


def normalize_product(product: str) -> str:
    """Resolve a product name or legacy alias to its canonical form.

    Accepts ``"edge"``, ``"azazel-edge"``, ``"azazel-pi"`` (legacy), etc. and
    returns the canonical product word (e.g. ``"edge"``). Unknown names are
    lower-cased and returned unchanged — this is a hint helper, not a gate, so
    a future product name is never rejected.
    """
    key = product.strip().lower()
    if key in LEGACY_ALIASES:
        return LEGACY_ALIASES[key]
    if key.startswith("azazel-"):
        key = key[len("azazel-") :]
    return LEGACY_ALIASES.get(key, key)


def _segment(product: str) -> str:
    """The canonical path segment for a product, e.g. ``azazel-edge``."""
    return f"azazel-{normalize_product(product)}"


def candidate_dirs(product: str, kind: PathKind) -> list[str]:
    """Return candidate directories for ``kind`` for ``product``, best-first.

    The canonical ``/<base>/azazel-<product>`` path comes first; any legacy
    alias directory (e.g. ``/run/azazel-pi`` for ``edge``) follows as a hint.
    The list is deterministic and de-duplicated; it is a suggestion, not an
    instruction — a product may use, reorder, or ignore it.
    """
    if kind not in _BASE_BY_KIND:
        raise ValueError(
            f"unknown path kind {kind!r}; expected one of {tuple(_BASE_BY_KIND)}"
        )
    base = _BASE_BY_KIND[kind]
    canonical = normalize_product(product)
    out = [f"{base}/{_segment(product)}"]
    for legacy in _LEGACY_SEGMENTS.get(canonical, ()):  # legacy hints, lower priority
        legacy_path = f"{base}/{legacy}"
        if legacy_path not in out:
            out.append(legacy_path)
    return out


def candidate_runtime_dirs(product: str) -> list[str]:
    """Candidate runtime dirs (``/run/azazel-<product>`` first). Hint only."""
    return candidate_dirs(product, "runtime")


def candidate_config_dirs(product: str) -> list[str]:
    """Candidate config dirs (``/etc/azazel-<product>`` first). Hint only."""
    return candidate_dirs(product, "config")


def candidate_log_dirs(product: str) -> list[str]:
    """Candidate log dirs (``/var/log/azazel-<product>`` first). Hint only."""
    return candidate_dirs(product, "log")


def preferred_dir(product: str, kind: PathKind) -> str:
    """The single canonical candidate for ``kind`` — the first of the list.

    Convenience for a caller that only wants the modern path and does not care
    about legacy discovery. Still only a hint.
    """
    return candidate_dirs(product, kind)[0]
