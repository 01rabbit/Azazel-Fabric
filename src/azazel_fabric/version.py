"""Single source of truth for the package version.

Version management is tag-driven on GitHub. This version must match the
release tag being cut; a ``.devN`` suffix is only present between releases.

``v0.9.0rc1``, ``v0.9.0rc2`` and ``v0.9.0rc3`` are published, and each is
signed (``release/*.digest.json.sig``). This is ``0.9.0rc3``: the tree as that
tag records it. ``main`` moves to ``0.9.0rc4.dev0`` with the first source
change after the tag, which is what the release-digest gate in
``tests/test_release_candidate_digest.py`` exists to force.

``v0.9.0rc3`` exists for one change: a typed cross-series reference may carry
further colons in its body. Under the ``rc2`` grammar every hierarchical
reference the series mints was refused by every slot requiring a typed ref, so
``effect_contracts`` had no possible producer anywhere in Azazel. See
``CHANGELOG.md``.

Each ``release/v0.9.0rc*.digest.json`` stays in the tree as the record of what
its tag contains — it describes the tag, not ``main``, and is verified by
checking out the tag and running ``tools/rc_digest.py --check``. Regenerating
one against a moved ``main`` would make it claim to be a digest of a tag it no
longer matches, and would strand the signature that covers its current bytes.
"""

__version__ = "0.9.0rc3"
