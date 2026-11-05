"""Single source of truth for the package version.

Version management is tag-driven on GitHub. This version must match the
release tag being cut; a ``.devN`` suffix is only present between releases.

``v0.9.0rc1`` through ``v0.9.0rc6`` are published, and each has a **signed
release digest** (``release/*.digest.json.sig``). ``rc1``'s and ``rc6``'s
signatures were added after their tags, so the ``rc6`` tag's own tree carries
the manifest but not the ``.sig``.

This is ``0.10.0``, the stable release of the ``v0.10.0`` series, and it is the
tree ``release/v0.10.0.digest.json`` records. Its contract surface is
``v0.10.0rc1``'s unchanged: at the ``v0.10.0`` tag only ``version.py`` differs
from ``rc1``. It is **additive** over ``v0.9.0``: the experimental Knowledge
Context profile (``azazel_fabric.knowledge_context``, Fabric#76) and the
producer captures in ``azazel_fabric.testing`` (Fabric#23). No released symbol
changed. Five families are experimental (the four below and
``knowledge_context``).

``0.10.0rc1`` is the tree ``release/v0.10.0rc1.digest.json`` records; its
signature was made before its tag and is inside the tag's tree.

``0.9.0`` is the stable release, and it is the tree
``release/v0.9.0.digest.json`` records. Its contract surface is ``v0.9.0rc6``'s
unchanged: at the ``v0.9.0`` tag only ``version.py`` differed from ``rc6``. Four families
are **experimental** and carry no compatibility promise --
``cti_contracts``, ``mio_contracts``, ``external_security_contracts`` and
``provisioning_contracts`` (see ``docs/release-compatibility.md``). Against
``v0.8.0``, one change is not additive: the deception and engagement directive
guards refuse a payload nested more than 32 levels deep (Fabric#23).

**The git tag itself is not signed and is not a trust boundary.** No
published tag here is signed (``v0.9.0rc1`` through ``rc5`` are annotated,
``v0.8.0`` and ``v0.9.0rc6`` lightweight); what carries a signature is
``release/<tag>.digest.json``. Say "the digest is signed", never "the tag is
signed" — the difference decides what a consumer may conclude from an install
succeeding, and it is what caught ``v0.9.0rc4`` being cut at the wrong commit
twice. See ``docs/release-signing.md`` and Fabric#56.

``0.9.0rc6`` is the tree ``release/v0.9.0rc6.digest.json`` records. It
carries the experimental ``external_security_contracts`` profile
(Fabric#25), which is additive, and three changes that are **not**: a typed
reference, a provisioning digest or a MAC may no longer end in a newline
(Fabric#65); a decision, activation-decision, trace or execution ref typed
``observation_objective:``, ``hypothesis:`` or ``frame:`` is refused where
``rc5`` read it as untyped (Fabric#72); and the deception, engagement and
effect directive walkers refuse a payload nested more than 32 levels deep
(Fabric#23). Input that was valid under ``rc5`` can be refused under ``rc6``.

``v0.9.0rc4`` carries one **non-additive** change: an ``EffectObservation``
may claim only ``observed_fact`` or ``active_materialized`` (Fabric#52). The
four other authority classes were accepted, which let a report of an effect
assert authority over it. Input that was valid under ``rc3`` is refused under
``rc4``.

``v0.9.0rc3`` exists for one change: a typed cross-series reference may carry
further colons in its body. Under the ``rc2`` grammar every hierarchical
reference the series mints was refused by every slot requiring a typed ref, so
``effect_contracts`` had no possible producer anywhere in Azazel.

Each ``release/v0.9.0rc*.digest.json`` stays in the tree as the record of what
its tag contains — it describes the tag, not ``main``, and is verified by
checking out the tag and running ``tools/rc_digest.py --check``. Regenerating
one against a moved ``main`` would make it claim to be a digest of a tag it no
longer matches, and would strand the signature that covers its current bytes.
"""

__version__ = "0.10.0"
