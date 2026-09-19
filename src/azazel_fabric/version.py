"""Single source of truth for the package version.

Version management is tag-driven on GitHub. This version must match the
release tag being cut; a ``.devN`` suffix is only present between releases.

``main`` carries additive contract work on top of the published ``v0.8.0``
tag — ``outcome_contracts`` (Outcome-as-Evidence shared facts) and the R1a
provisioning / M.I.O. contract families. That work is now offered as the
**release candidate** ``0.9.0rc1``: the Nexus/Boot program plan's R1b step,
which exists so consumers can pin an exact tag and produce the downstream
evidence R1c requires, rather than pinning ``main``.

A release candidate is a real, pinnable tag. It is not the stable release:
cutting ``v0.9.0`` means dropping the ``rc1`` suffix once the plan's "at least
one real producer and two real consumers per non-experimental contract" gate
has evidence (see ``docs/release-compatibility.md``).
"""

__version__ = "0.9.0rc1"
