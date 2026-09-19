"""Single source of truth for the package version.

Version management is tag-driven on GitHub. This version must match the
release tag being cut; a ``.devN`` suffix is only present between releases.

``main`` currently carries unreleased, additive contract work on top of the
published ``v0.8.0`` tag — ``outcome_contracts`` (Outcome-as-Evidence shared
facts) and the R1a provisioning / M.I.O. contract families — so the packaged
version is ``0.9.0.dev0`` and is explicitly **not** a release. Cutting
``v0.9.0`` means dropping the ``.dev0`` suffix, tagging, and publishing the
matching GitHub Release (see ``docs/release-compatibility.md``).
"""

__version__ = "0.9.0.dev0"
