from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from pydantic import BaseModel

from app.core.config import settings

security = HTTPBearer(auto_error=False)


class ClerkAuthContext(BaseModel):
    user_id: str
    session_id: Optional[str] = None


def _auth_error(message: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": "AUTH_INVALID_TOKEN", "message": message},
    )


def _resolve_issuer(unverified_claims: dict) -> str:
    issuer = settings.clerk_jwt_issuer or unverified_claims.get("iss", "")
    if not issuer:
        raise _auth_error("Token issuer is missing.")
    return issuer.rstrip("/")


def _decode_clerk_token(token: str) -> dict:
    try:
        unverified_claims = jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": False, "verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise _auth_error(f"Malformed token: {exc}") from exc

    issuer = _resolve_issuer(unverified_claims)
    jwks_client = PyJWKClient(f"{issuer}/.well-known/jwks.json")
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        decode_kwargs = {
            "algorithms": ["RS256"],
            "issuer": issuer,
        }
        if settings.clerk_jwt_audience:
            decode_kwargs["audience"] = settings.clerk_jwt_audience
        else:
            decode_kwargs["options"] = {"verify_aud": False}
        return jwt.decode(token, signing_key.key, **decode_kwargs)
    except jwt.PyJWTError as exc:
        raise _auth_error(f"Token verification failed: {exc}") from exc


def get_current_clerk_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> ClerkAuthContext:
    if not credentials or not credentials.credentials:
        raise _auth_error("Bearer token is required.")
    claims = _decode_clerk_token(credentials.credentials)
    user_id = claims.get("sub")
    if not user_id:
        raise _auth_error("Token subject is missing.")
    return ClerkAuthContext(user_id=user_id, session_id=claims.get("sid"))
