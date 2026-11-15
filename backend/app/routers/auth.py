"""Authentication: rate-limited login, logout (token revocation), password change."""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlmodel import Session, func, select

from app.core.config import get_settings
from app.core.deps import CurrentUser, SessionDep, TokenPayload, get_faculty_profile, get_student_profile
from app.core.passwords import password_problems
from app.core.rate_limit import LoginRateLimiter
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.models import RevokedToken, User
from app.schemas.users import LoginRequest, MeResponse, TokenResponse, UserRead
from app.services import audit
from app.services.people import faculty_read, student_read

router = APIRouter(prefix="/api/auth", tags=["auth"])

_settings = get_settings()
limiter = LoginRateLimiter(_settings.login_max_failures, _settings.login_window_minutes * 60)
# Same work factor as a real hash, so unknown emails take as long as wrong passwords (no user enumeration).
_DUMMY_HASH = hash_password("timing-equaliser-not-a-real-password")


def _authenticate(session: Session, email: str, password: str, request: Request) -> User:
    email_key = email.strip().lower()
    key = f"{email_key}|{audit.client_ip(request)}"
    wait = limiter.retry_after(key)
    if wait:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            f"Too many failed attempts. Try again in {max(1, wait // 60)} minute(s).",
                            headers={"Retry-After": str(wait)})
    user = session.exec(select(User).where(func.lower(User.email) == email_key)).first()
    ok = verify_password(password, user.password_hash if user else _DUMMY_HASH) and user is not None
    if not ok:
        limiter.record_failure(key)
        audit.record(session, None, "login_failed", "auth", user.id if user else None,
                     f"Failed login for {email_key[:100]}", request)
        session.commit()
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")
    limiter.reset(key)
    audit.record(session, user, "login", "auth", user.id, f"{user.name} signed in", request)
    session.commit()
    return user


def _me(session: Session, user: User) -> MeResponse:
    student = get_student_profile(session, user)
    faculty = get_faculty_profile(session, user)
    return MeResponse(
        user=UserRead.model_validate(user),
        student=student_read(student, user) if student else None,
        faculty=faculty_read(faculty, user) if faculty else None,
    )


@router.post("/login", response_model=TokenResponse, summary="Log in with email + password (rate limited)")
def login(body: LoginRequest, session: SessionDep, request: Request) -> TokenResponse:
    user = _authenticate(session, body.email, body.password, request)
    token = create_access_token(user.id, user.role.value)
    expires = datetime.fromtimestamp(decode_access_token(token)["exp"], tz=timezone.utc)
    return TokenResponse(access_token=token, expires_at=expires, **_me(session, user).model_dump())


@router.post("/token", summary="OAuth2 password flow (used by the Swagger 'Authorize' button)")
def token(form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep,
          request: Request) -> dict[str, str]:
    user = _authenticate(session, form.username, form.password, request)
    return {"access_token": create_access_token(user.id, user.role.value), "token_type": "bearer"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT,
             summary="Revoke the current token (server-side logout)")
def logout(user: CurrentUser, payload: TokenPayload, session: SessionDep, request: Request) -> None:
    session.add(RevokedToken(jti=payload["jti"], user_id=user.id,
                             expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc)))
    audit.record(session, user, "logout", "auth", user.id, f"{user.name} signed out", request)
    session.commit()


@router.get("/me", response_model=MeResponse, summary="Current user with role profile")
def me(user: CurrentUser, session: SessionDep) -> MeResponse:
    return _me(session, user)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT,
             summary="Change your password (policy: 8+ chars, upper, lower, digit, symbol)")
def change_password(body: PasswordChange, user: CurrentUser, session: SessionDep, request: Request) -> None:
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    problems = password_problems(body.new_password, user.email)
    if body.new_password == body.current_password:
        problems.append("different from the current password")
    if problems:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "New password needs: " + "; ".join(problems))
    user.password_hash = hash_password(body.new_password)
    session.add(user)
    audit.record(session, user, "password_change", "auth", user.id, f"{user.name} changed their password", request)
    session.commit()
