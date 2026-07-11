"""Shared notification payload model + transport mappers (`contracts.md` §4).

`NotificationEvent` is the single payload shape every Azazel notification
transport consumes; :mod:`azazel_fabric.notify.transports` maps it onto ntfy /
Mattermost payloads. Payload shape and payload mapping only — no product copy,
no UI, and no network (the mappers build payloads, they never send). Actual
delivery stays product-side.
"""

from azazel_fabric.notify.model import SEVERITIES, NotificationEvent, Severity
from azazel_fabric.notify.transports import to_mattermost_payload, to_ntfy_payload

__all__ = [
    "NotificationEvent",
    "Severity",
    "SEVERITIES",
    "to_ntfy_payload",
    "to_mattermost_payload",
]
