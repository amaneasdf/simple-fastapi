from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
from .core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(30), unique=True, index=True)
    email = Column(String(255))
    fullname = Column(String(255))
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superadmin = Column(Boolean, default=False)


class AccessToken(Base):
    __tablename__ = "accesstokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    token = Column(String(255), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(Integer)
    expired_at = Column(Integer)
    is_revoked = Column(Boolean, default=False)
