from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, func, select

from app.core.deps import CurrentUser, SessionDep, get_faculty_profile, get_student_profile
from app.core.security import create_access_token, verify_password
from app.models import User
from app.schemas.users import LoginRequest, MeResponse, TokenResponse, UserRead
from app.services.people import faculty_read, student_read

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _authenticate(session: Session, email: str, password: str) -> User:
    user = session.exec(select(User).where(func.lower(User.email) == email.strip().lower())).first()
    if user is None or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")
    return user


def _me(session: Session, user: User) -> MeResponse:
    student = get_student_profile(session, user)
    faculty = get_faculty_profile(session, user)
    return MeResponse(
        user=UserRead.model_validate(user),
        student=student_read(student, user) if student else None,
        faculty=faculty_read(faculty, user) if faculty else None,
    )


@router.post("/login", response_model=TokenResponse, summary="Log in with email + password (JSON)")
def login(body: LoginRequest, session: SessionDep) -> TokenResponse:
    user = _authenticate(session, body.email, body.password)
    me = _me(session, user)
    return TokenResponse(access_token=create_access_token(user.id, user.role.value), **me.model_dump())


@router.post("/token", summary="OAuth2 password flow (used by the Swagger 'Authorize' button)")
def token(form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep) -> dict[str, str]:
    user = _authenticate(session, form.username, form.password)
    return {"access_token": create_access_token(user.id, user.role.value), "token_type": "bearer"}


@router.get("/me", response_model=MeResponse, summary="Current user with role profile")
def me(user: CurrentUser, session: SessionDep) -> MeResponse:
    return _me(session, user)
