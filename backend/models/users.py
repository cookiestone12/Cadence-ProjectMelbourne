from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Index, text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        # Functional unique index on lower(username) to enforce
        # case-insensitive username uniqueness at the DB level.
        Index('idx_users_username_lower', text('lower(username)'), unique=True),
    )

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)
    is_super_admin = Column(Boolean, default=False)
    is_cadence_staff = Column(Boolean, default=False, nullable=False, server_default="false")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    # Task #190: server-side "active organization" pointer for users who
    # belong to multiple orgs. Validated against OrganizationMember on
    # every read; if it points at an org the user is no longer in, we
    # self-heal to the oldest membership. Kept out of the JWT so existing
    # tokens stay valid across switches.
    current_organization_id = Column(
        Integer,
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )

    organization_memberships = relationship("OrganizationMember", back_populates="user")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    @property
    def is_master_admin(self) -> bool:
        """Alias for is_super_admin. Task #74 spec uses the
        'master_admin' name; the column itself stays is_super_admin
        to avoid a rename across the codebase.
        """
        return bool(self.is_super_admin)


class UserSession(Base):
    """One row per issued JWT, keyed by SHA-256 of the token. Lets
    us revoke a token mid-flight (e.g. on staff deprovision) by
    flipping is_revoked. Cleaned up nightly by the scheduler.
    """
    __tablename__ = "user_sessions"
    __table_args__ = (
        Index('ix_user_sessions_token_hash', 'token_hash', unique=True),
        Index('ix_user_sessions_user_id', 'user_id'),
        Index('ix_user_sessions_expires_at', 'expires_at'),
    )

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(64), nullable=False)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False, server_default="false")
    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="sessions")
