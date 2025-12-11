from __future__ import annotations
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Table, ForeignKey, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column

from db.database import Base

# Association table for many-to-many between users and skills
user_skills = Table(
    "user_skills",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("skill_id", ForeignKey("skills.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False, default="not_set")
    location: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    interest: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    personality: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    commitment_level: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0 - 1.0

    skills: Mapped[List["Skill"]] = relationship(
        "Skill", secondary=user_skills, back_populates="users", lazy="selectin"
    )


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)

    users: Mapped[List[User]] = relationship(
        "User", secondary=user_skills, back_populates="skills", lazy="selectin"
    )
