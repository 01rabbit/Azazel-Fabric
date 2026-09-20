"""Single source of truth for the package version.

Version management is tag-driven on GitHub. This version must match the
release tag being cut; a ``.devN`` suffix is only present between releases.

``v0.9.0rc1`` and ``v0.9.0rc2`` are published, and both are signed
(``release/*.digest.json.sig``). ``main`` has moved past ``rc2``, so it carries
``0.9.0rc3.dev0``: development toward the next candidate or the stable
``0.9.0``, whichever the downstream evidence calls for.

The ``.dev0`` suffix also switches off the release-digest gate in
``tests/test_release_candidate_digest.py``, which is what that gate is designed
to do between releases. It is the gate that forced this bump: the first source
change after ``rc2`` made ``release/v0.9.0rc2.digest.json`` disagree with the
tree, which is exactly the fact it exists to report.

Both ``release/v0.9.0rc*.digest.json`` files stay in the tree as the record of
what those tags contain — they describe the tags, not ``main``, and are
verified by checking out the tag and running ``tools/rc_digest.py --check``.
Regenerating one against a moved ``main`` would make it claim to be a digest of
a tag it no longer matches, and would strand the signature that covers its
current bytes.
"""

__version__ = "0.9.0rc3.dev0"
