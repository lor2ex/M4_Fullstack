from pydantic import BaseModel, ConfigDict
from typing import Optional
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# SQLAlchemy модель
class BookORM(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    year = Column(Integer, nullable=True)

# Pydantic модель
class Book(BaseModel):
    id: int
    title: str
    author: str
    year: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)