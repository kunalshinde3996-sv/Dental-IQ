"""Password policy (applied whenever a password is set or changed)."""
import re

MIN_LENGTH = 8
MAX_LENGTH = 128
_COMMON = {"password", "password1", "password@123", "12345678", "qwerty123", "admin@123", "welcome@123"}


def password_problems(password: str, email: str | None = None) -> list[str]:
    """Return human-readable reasons the password is unacceptable (empty list = OK)."""
    problems = []
    if len(password) < MIN_LENGTH:
        problems.append(f"at least {MIN_LENGTH} characters")
    if len(password) > MAX_LENGTH:
        problems.append(f"at most {MAX_LENGTH} characters")
    if not re.search(r"[a-z]", password):
        problems.append("a lower-case letter")
    if not re.search(r"[A-Z]", password):
        problems.append("an upper-case letter")
    if not re.search(r"\d", password):
        problems.append("a digit")
    if not re.search(r"[^A-Za-z0-9]", password):
        problems.append("a symbol")
    if password.lower() in _COMMON:
        problems.append("not a commonly used password")
    if email:
        local = email.split("@")[0].lower()
        if len(local) >= 4 and local in password.lower():
            problems.append("must not contain your email name")
    return problems
