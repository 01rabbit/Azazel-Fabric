"""Open extension registries for the provisioning contract family.

A registry is a *documented extension list*, not a closed enum: an unregistered
value is descriptive data, not an error, and a product adds a value here rather
than by breaking the base type (the convention already used for
``ModeState.name`` — see ``docs/contracts.md`` §1).

Nothing in this module grants authority. A product name being registered does
not admit that product, and a deployment-profile name being registered does not
enable anything.
"""

from __future__ import annotations

# Series product names. Azazel-Nexus and Azazel-Boot are registered here per the
# program plan's R1 deliverable "define Nexus and Boot product names in open
# extension registries".
REGISTERED_PRODUCTS: tuple[str, ...] = (
    "azazel-boot",
    "azazel-deception",
    "azazel-edge",
    "azazel-fabric",
    "azazel-gadget",
    "azazel-knowledge",
    "azazel-nexus",
)

# Neutral artifact/deployment profile IDs. Deployment *policy* stays in product
# overlays; these names only let two repositories mean the same thing.
REGISTERED_DEPLOYMENT_PROFILES: tuple[str, ...] = (
    "boot-emergency-lite",
    "deception-full-host",
    "knowledge-full-node",
    "nexus-embedded-lite",
)

# Operational interface roles. ``unassigned`` is the only state an interface may
# hold before commissioning; every other role requires an explicit operator
# confirmation against a composite identity (see ``models.InterfaceAssignment``).
INTERFACE_ROLES: tuple[str, ...] = (
    "asset_acquisition",
    "deception_bridge",
    "management",
    "observation",
    "unassigned",
)

# Display vocabulary for the *effective capability* a product computes as
#
#     resource profile   n topology profile
#                        n verified asset set
#                        n current trust/health state
#
# It is recorded here so two products name the same summary the same way. It is
# deliberately NOT a field on any Fabric contract: no single provisioning record
# may imply an effective capability, and none of these values is an authority
# level. ``tests/test_provisioning_contracts.py`` asserts no model carries one.
CAPABILITY_STATES: tuple[str, ...] = ("CORE", "LITE", "FULL")


def is_registered_product(name: str) -> bool:
    """Return True when ``name`` is in the open product registry."""

    return name in REGISTERED_PRODUCTS


def is_registered_deployment_profile(name: str) -> bool:
    """Return True when ``name`` is in the open deployment-profile registry."""

    return name in REGISTERED_DEPLOYMENT_PROFILES


def is_registered_interface_role(name: str) -> bool:
    """Return True when ``name`` is a registered operational interface role."""

    return name in INTERFACE_ROLES


__all__ = [
    "CAPABILITY_STATES",
    "INTERFACE_ROLES",
    "REGISTERED_DEPLOYMENT_PROFILES",
    "REGISTERED_PRODUCTS",
    "is_registered_deployment_profile",
    "is_registered_interface_role",
    "is_registered_product",
]
