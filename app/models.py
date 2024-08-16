from sqlalchemy import Column, Integer, String, Boolean
from .core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(30), unique=True, index=True)
    email = Column(String(255))
    password = Column(String(255), nullable=False)
    is_activated = Column(Boolean, default=True)
