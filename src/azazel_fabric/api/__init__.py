"""Framework-neutral API conventions for the Azazel series (`contracts.md` §3).

Security *posture* conventions, not endpoint logic: the shared JSON error
envelope, a fail-closed default rejection, the ordered role vocabulary, and
token-header extraction. Everything here is framework-neutral — no Flask/FastAPI
import in this package's core; those adapters are optional extras
(``azazel-fabric[flask]`` / ``azazel-fabric[fastapi]``) per design-principles
§5. A product supplies the policy (which role, which token); Fabric only fixes
the shapes and the fail-closed default.
"""

from azazel_fabric.api.auth import (
    COMPAT_TOKEN_HEADER,
    TOKEN_HEADER,
    extract_token,
    token_matches,
)
from azazel_fabric.api.errors import (
    FORBIDDEN,
    INTERNAL_ERROR,
    INVALID_REQUEST,
    UNAUTHENTICATED,
    ErrorBody,
    ErrorEnvelope,
    error_payload,
    fail_closed_error,
)
from azazel_fabric.api.roles import (
    ROLES,
    is_known_role,
    role_allows,
    role_rank,
)

__all__ = [
    # errors
    "ErrorBody",
    "ErrorEnvelope",
    "error_payload",
    "fail_closed_error",
    "UNAUTHENTICATED",
    "FORBIDDEN",
    "INVALID_REQUEST",
    "INTERNAL_ERROR",
    # roles
    "ROLES",
    "is_known_role",
    "role_rank",
    "role_allows",
    # auth
    "TOKEN_HEADER",
    "COMPAT_TOKEN_HEADER",
    "extract_token",
    "token_matches",
]
