"""FastAPI dependencies: DB session, current user, role guards."""
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select

from app.core.security import decode_access_token
from app.database import get_session
from app.models import Faculty, RevokedToken, Student, User
from app.models.enums import Role

# tokenUrl powers the "Authorize" button in Swagger (/docs).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")

SessionDep = Annotated[Session, Depends(get_session)]

_credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired authentication token",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_token_payload(token: Annotated[str, Depends(oauth2_scheme)]) -> dict:
    try:
        return decode_access_token(token)
    except jwt.PyJWTError:
        raise _credentials_error from None


TokenPayload = Annotated[dict, Depends(get_token_payload)]


def get_current_user(session: SessionDep, payload: TokenPayload) -> User:
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise _credentials_error from None
    if session.get(RevokedToken, payload["jti"]) is not None:  # logged out
        raise _credentials_error
    user = session.get(User, user_id)
    if user is None or not user.is_active:
        raise _credentials_error
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role) -> Callable[[User], User]:
    """Dependency factory: allow only users whose role is in ``roles``."""

    def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "You do not have permission to perform this action")
        return user

    return checker


def get_student_profile(session: Session, user: User) -> Student | None:
    return session.exec(select(Student).where(Student.user_id == user.id)).first()


def get_faculty_profile(session: Session, user: User) -> Faculty | None:
    return session.exec(select(Faculty).where(Faculty.user_id == user.id)).first()


def current_student(session: SessionDep, user: Annotated[User, Depends(require_roles(Role.student))]) -> Student:
    student = get_student_profile(session, user)
    if student is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No student profile is linked to this account")
    return student


def current_faculty(session: SessionDep, user: Annotated[User, Depends(require_roles(Role.faculty))]) -> Faculty:
    faculty = get_faculty_profile(session, user)
    if faculty is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No faculty profile is linked to this account")
    return faculty


CurrentStudent = Annotated[Student, Depends(current_student)]
CurrentFaculty = Annotated[Faculty, Depends(current_faculty)]
StaffUser = Annotated[User, Depends(require_roles(Role.admin, Role.faculty))]
AdminUser = Annotated[User, Depends(require_roles(Role.admin))]
