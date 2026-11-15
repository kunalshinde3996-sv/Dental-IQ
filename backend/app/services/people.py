"""Builders for student / faculty read models (joins profile + user)."""
from sqlmodel import Session, select

from app.models import Faculty, Student, User
from app.schemas.users import FacultyRead, StudentRead


def student_read(student: Student, user: User) -> StudentRead:
    return StudentRead(
        id=student.id, user_id=user.id, name=user.name, email=user.email,
        roll_no=student.roll_no, year=student.year, batch=student.batch,
    )


def faculty_read(faculty: Faculty, user: User) -> FacultyRead:
    return FacultyRead(
        id=faculty.id, user_id=user.id, name=user.name, email=user.email,
        department=faculty.department, designation=faculty.designation,
    )


def get_student_read(session: Session, student_id: int) -> StudentRead | None:
    row = session.exec(
        select(Student, User).join(User, User.id == Student.user_id).where(Student.id == student_id)
    ).first()
    return student_read(*row) if row else None
