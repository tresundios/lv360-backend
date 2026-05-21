"""
FastAPI dependencies: get_current_user(), require_role(), get_lang()
PRD: AUTH-FR-005, AUTH-FR-006
"""

from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.i18n import Lang, MessageCode, parse_accept_language, t
from app.core.security import InvalidTokenException, TokenExpiredException, decode_access_token
from app.database import get_db
from app.models.user import User, UserRole, UserStatus

bearer_scheme = HTTPBearer(auto_error=False)


def get_lang(accept_language: str | None = Header(None, alias="Accept-Language")) -> Lang:
    """Extract language preference from Accept-Language header. Default: vi."""
    return parse_accept_language(accept_language)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
    lang: Lang = Depends(get_lang),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": MessageCode.SESSION_INVALIDATED, "message": t(MessageCode.SESSION_INVALIDATED, lang)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenExpiredException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": MessageCode.TOKEN_EXPIRED, "message": t(MessageCode.TOKEN_EXPIRED, lang)},
        )
    except InvalidTokenException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": MessageCode.SESSION_INVALIDATED, "message": t(MessageCode.SESSION_INVALIDATED, lang)},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": MessageCode.SESSION_INVALIDATED, "message": t(MessageCode.SESSION_INVALIDATED, lang)},
        )

    user = db.query(User).filter(User.id == UUID(user_id)).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": MessageCode.USER_NOT_FOUND, "message": t(MessageCode.USER_NOT_FOUND, lang)},
        )

    if user.status == UserStatus.suspended:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": MessageCode.ACCOUNT_SUSPENDED, "message": t(MessageCode.ACCOUNT_SUSPENDED, lang)},
        )

    return user


def require_role(*roles: UserRole):
    """Dependency factory: restrict endpoint to specific roles."""
    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "FORBIDDEN", "message": "Forbidden"},
            )
        return current_user
    return _check
