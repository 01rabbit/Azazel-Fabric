"""Transport payload mappers for `NotificationEvent` (`contracts.md` §4).

Thin, pure functions that map the shared :class:`NotificationEvent` onto a
specific transport's payload shape (ntfy, Mattermost). They build and return a
payload; **they do not send anything** — no sockets, no HTTP client, no network
import. Actual delivery (and its ret/backoff, auth, endpoint URL) stays
product-side: the network belongs outside Fabric (design-principles §5, and the
offline-first spirit of the series). These mappers exist only so every product
maps the shared shape onto a transport the same way.
"""

from __future__ import annotations

from typing import Any

from azazel_fabric.notify.model import NotificationEvent

# ntfy priority is 1 (min) .. 5 (max); map the series' three severities onto it.
_NTFY_PRIORITY: dict[str, int] = {"info": 3, "warning": 4, "critical": 5}

# Mattermost has no severity field; convey it as a leading emoji/label instead.
_MM_LABEL: dict[str, str] = {"info": "INFO", "warning": "WARNING", "critical": "CRITICAL"}


def to_ntfy_payload(event: NotificationEvent) -> dict[str, Any]:
    """Map a :class:`NotificationEvent` onto an ntfy publish payload.

    Returns a dict a product can hand to its own ntfy client. Pure — no send.
    """
    tags = [event.product, event.severity]
    if event.trace_id:
        tags.append(f"trace:{event.trace_id}")
    return {
        "title": event.title,
        "message": event.body,
        "priority": _NTFY_PRIORITY[event.severity],
        "tags": tags,
    }


def to_mattermost_payload(event: NotificationEvent) -> dict[str, Any]:
    """Map a :class:`NotificationEvent` onto a Mattermost webhook payload.

    Returns a dict a product can POST via its own Mattermost webhook. Pure — no
    send. Severity is conveyed in the text since Mattermost has no severity field.
    """
    label = _MM_LABEL[event.severity]
    text = f"**[{label}] {event.title}**\n{event.body}"
    return {
        "text": text,
        "props": {
            "product": event.product,
            "severity": event.severity,
            "event_id": event.event_id,
            "trace_id": event.trace_id,
        },
    }
