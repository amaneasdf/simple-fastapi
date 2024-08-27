from sqlalchemy import Column, ForeignKey, Index, Integer, String, Boolean, func
from sqlalchemy.orm import relationship
from .core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(30), nullable=False, unique=True, index=True)
    email = Column(String(255))
    fullname = Column(String(255))
    password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superadmin = Column(Boolean, default=False)
    created_at = Column(Integer, server_default=func.unix_timestamp())
    updated_at = Column(
        Integer, server_default=func.unix_timestamp(), onupdate=func.unix_timestamp()
    )

    allowed_scopes = relationship(
        "UserScope", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )


class UserScope(Base):
    __tablename__ = "userscopes"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    scope = Column(String(120), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(Integer, server_default=func.unix_timestamp())
    updated_at = Column(
        Integer, server_default=func.unix_timestamp(), onupdate=func.unix_timestamp()
    )

    user = relationship("User", back_populates="allowed_scopes")

    __table_args__ = (Index("ix_userscopes_user_id_scope", "user_id", "scope"),)


class AccessToken(Base):
    __tablename__ = "accesstokens"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    token = Column(String(255), unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    timestamp = Column(Integer)
    expired_at = Column(Integer)
    is_revoked = Column(Boolean, default=False)
    created_at = Column(Integer, server_default=func.unix_timestamp())
    updated_at = Column(
        Integer, server_default=func.unix_timestamp(), onupdate=func.unix_timestamp()
    )
