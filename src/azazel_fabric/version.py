"""Single source of truth for the package version.

Version management is tag-driven on GitHub. This version must match the
release tag being cut; a ``.devN`` suffix is only present between releases.

``v0.9.0rc1`` is published. ``main`` has moved past it, so it carries
``0.9.0rc2.dev0``: development toward the next candidate or the stable
``0.9.0``, whichever the downstream evidence calls for.

The ``.dev0`` suffix also switches off the release-digest gate in
``tests/test_release_candidate_digest.py``, which is what that gate is designed
to do between releases. ``release/v0.9.0rc1.digest.json`` stays in the tree as
the record of what that tag contains — it describes the tag, not ``main``, and
is verified by checking out ``v0.9.0rc1`` and running ``tools/rc_digest.py
--check``. Regenerating it against a moved ``main`` would make it claim to be a
digest of a tag it no longer matches, which is worse than not checking it here.
"""

__version__ = "0.9.0rc2"
