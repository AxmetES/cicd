from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    resume: Mapped["Resume"] = relationship(back_populates="user", uselist=False)


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship(back_populates="resume")
    experience: Mapped[list["Experience"]] = relationship(back_populates="resume", cascade="all, delete-orphan")
    education: Mapped[list["Education"]] = relationship(back_populates="resume", cascade="all, delete-orphan")
    projects: Mapped[list["Project"]] = relationship(back_populates="resume", cascade="all, delete-orphan")


class Experience(Base):
    __tablename__ = "experience"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"))
    role: Mapped[str] = mapped_column(String)
    company: Mapped[str] = mapped_column(String)
    period: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)

    resume: Mapped["Resume"] = relationship(back_populates="experience")


class Education(Base):
    __tablename__ = "education"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"))
    title: Mapped[str] = mapped_column(String)
    place: Mapped[str] = mapped_column(String)
    period: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)

    resume: Mapped["Resume"] = relationship(back_populates="education")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"))
    name: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)

    resume: Mapped["Resume"] = relationship(back_populates="projects")