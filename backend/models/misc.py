from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON, Enum, Index, LargeBinary, CheckConstraint, text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base


class MigrationLock(Base):
    """Single-row infrastructure table that serializes Alembic upgrades
    across multiple booting workers. Bootstrapped + acquired/released by
    backend.utils.migration_lock at app startup; declared here purely so
    `alembic check` doesn't try to drop it as drift.
    """
    __tablename__ = "migration_lock"
    __table_args__ = (
        CheckConstraint("id = 1", name="migration_lock_id_check"),
    )

    id = Column(Integer, primary_key=True, server_default=text("1"))
    status = Column(String, nullable=False, server_default=text("'idle'"))
    started_at = Column(DateTime(timezone=True), nullable=True)
    host = Column(String, nullable=True)
    revision = Column(String, nullable=True)

class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"
    __table_args__ = (
        Index('ix_ai_usage_logs_org_id', 'org_id'),
        Index('ix_ai_usage_logs_created_at', 'created_at'),
        Index('ix_ai_usage_logs_feature', 'feature'),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    feature = Column(String, nullable=False)
    model = Column(String, nullable=False, default="gpt-4o-mini")
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost_cents = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class TicketCategory(str, enum.Enum):
    BUG_REPORT = "BUG_REPORT"
    FEATURE_REQUEST = "FEATURE_REQUEST"
    GENERAL_SUPPORT = "GENERAL_SUPPORT"


class TicketStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class LeadType(str, enum.Enum):
    WAITLIST = "WAITLIST"
    DEMO_REQUEST = "DEMO_REQUEST"
    INVESTOR_INQUIRY = "INVESTOR_INQUIRY"
    INTERN_APPLICATION = "INTERN_APPLICATION"


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, index=True)
    name = Column(String, nullable=True)
    company = Column(String, nullable=True)
    message = Column(Text, nullable=True)
    lead_type = Column(String, nullable=False, default="WAITLIST")
    resume_path = Column(String, nullable=True)
    resume_data = Column(LargeBinary, nullable=True)
    resume_filename = Column(String, nullable=True)
    resume_mime = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    __table_args__ = (
        Index('ix_support_tickets_user_id', 'user_id'),
        Index('ix_support_tickets_org_id', 'organization_id'),
        Index('ix_support_tickets_status', 'status'),
        Index('ix_support_tickets_created_at', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    category = Column(String, nullable=False, default="GENERAL_SUPPORT")
    subject = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="OPEN")
    admin_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    attachments = relationship("SupportTicketAttachment", back_populates="ticket", cascade="all, delete-orphan")


class SupportTicketAttachment(Base):
    __tablename__ = "support_ticket_attachments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("SupportTicket", back_populates="attachments")


class ScheduleAImport(Base):
    """Persists the original Schedule A upload (PDF/image/text) so admins can
    audit what was ingested, download the source later, or re-run extraction
    with a newer model.
    """
    __tablename__ = "schedule_a_imports"
    __table_args__ = (
        Index('ix_schedule_a_imports_org_id', 'organization_id'),
        Index('ix_schedule_a_imports_created_at', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    creator_id = Column(Integer, ForeignKey("creators.id", ondelete="SET NULL"), nullable=True)
    creator_name = Column(String, nullable=True)

    original_filename = Column(String, nullable=False)
    stored_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    sha256 = Column(String(64), nullable=True)

    extraction_method = Column(String, nullable=True)
    songs_created = Column(Integer, default=0)
    songs_failed = Column(Integer, default=0)
    contract_terms = Column(JSON, nullable=True)
    document_info = Column(JSON, nullable=True)
    is_text_paste = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization")
    user = relationship("User")
    creator = relationship("Creator")


# --- Internal developer tools (Task #89) ------------------------------


class RuntimeConfig(Base):
    """Global runtime config keys editable from /internal/config.

    Read-through cache lives in services/runtime_config.py. Every
    write goes through the audit log."""
    __tablename__ = "runtime_config"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, nullable=False, unique=True, index=True)
    category = Column(String, nullable=False, default="general")
    value_type = Column(String, nullable=False, default="string")  # string|bool|int|float|json
    value = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DeployEvent(Base):
    """Rolling history of process boots / deploys captured at startup."""
    __tablename__ = "deploy_event"
    __table_args__ = (
        Index("ix_deploy_event_booted_at", "booted_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    booted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    git_sha = Column(String(40), nullable=True)
    git_short = Column(String(12), nullable=True)
    git_message = Column(Text, nullable=True)
    git_author = Column(String, nullable=True)
    git_committed_at = Column(DateTime, nullable=True)
    app_env = Column(String, nullable=True)
    build_version = Column(String, nullable=True)
    python_version = Column(String, nullable=True)
    node_version = Column(String, nullable=True)
    hostname = Column(String, nullable=True)


class SavedQuery(Base):
    """Read-only SELECT queries saved by staff users in /internal/database."""
    __tablename__ = "saved_query"
    __table_args__ = (
        Index("ix_saved_query_owner", "owner_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    sql = Column(Text, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User")


class QueryHistoryEntry(Base):
    """Every staff query (saved-or-not) captured for audit + replay."""
    __tablename__ = "query_history"
    __table_args__ = (
        Index("ix_query_history_owner_ran", "owner_id", "ran_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sql = Column(Text, nullable=False)
    ran_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    row_count = Column(Integer, nullable=True)
    success = Column(Boolean, default=True)
    error = Column(Text, nullable=True)

    owner = relationship("User")
