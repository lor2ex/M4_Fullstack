from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String
from pydantic import BaseModel, EmailStr
from app.db import Base

# ---------- ORM ----------
class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer)
    email: Mapped[str] = mapped_column(String, unique=True)


# ---------- Pydantic схемы ----------
class PersonCreate(BaseModel):
    name: str
    age: int | None = None
    email: EmailStr

class PersonRead(BaseModel):
    id: int
    name: str
    age: int | None = None
    email: EmailStr

    model_config = {
        "from_attributes": True  # SQLAlchemy -> Pydantic v2
    }
