from fastapi import Header, HTTPException, status
import jwt
from jwt import PyJWKClient
from app.core.config import settings

_clerk_jwk_client: PyJWKClient | None = None


def _get_clerk_jwk_client() -> PyJWKClient:
    global _clerk_jwk_client
    if _clerk_jwk_client is None:
        if not settings.clerk_jwks_url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Clerk JWKS URL is not configured.",
            )
        _clerk_jwk_client = PyJWKClient(settings.clerk_jwks_url)
    return _clerk_jwk_client


def get_current_clerk_user(
    authorization: str | None = Header(default=None),
) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Clerk bearer token.",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Clerk bearer token.",
        )

    try:
        signing_key = _get_clerk_jwk_client().get_signing_key_from_jwt(token)
        decode_kwargs = {
            "key": signing_key.key,
            "algorithms": ["RS256"],
        }
        if settings.clerk_issuer:
            decode_kwargs["issuer"] = settings.clerk_issuer
        if settings.clerk_audience:
            decode_kwargs["audience"] = settings.clerk_audience

        claims = jwt.decode(token, **decode_kwargs)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Clerk token: {exc}",
        )

    user_id = claims.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clerk token is missing subject.",
        )

    return {"user_id": user_id, "claims": claims}
