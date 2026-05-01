from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Enum, Index, LargeBinary, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class ClientShareStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"
    CANCELLED = "CANCELLED"


class ClientShareRole(str, enum.Enum):
    COPRIMARY = "COPRIMARY"
    SECONDARY = "SECONDARY"
    READER = "READER"


class ClientShare(Base):
    __tablename__ = "client_shares"
    __table_args__ = (
        Index('ix_client_shares_org', 'primary_org_id'),
        Index('ix_client_shares_recipient', 'recipient_org_id'),
        Index(
            'ix_client_share_active_unique',
            'creator_id', 'recipient_user_email',
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'ACCEPTED')")
        ),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    primary_org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    recipient_org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    
    recipient_user_email = Column(String, nullable=False)
    recipient_org_name_verification = Column(String, nullable=True)
    
    passcode = Column(String(6), nullable=False)
    role = Column(String, nullable=False, default="READER")
    status = Column(String, nullable=False, default="PENDING")
    shared_modules = Column(JSON, nullable=True)
    
    shared_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    accepted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    
    creator = relationship("Creator")
    primary_org = relationship("Organization", foreign_keys=[primary_org_id])
    recipient_org = relationship("Organization", foreign_keys=[recipient_org_id])
    shared_by = relationship("User", foreign_keys=[shared_by_user_id])
    accepted_by = relationship("User", foreign_keys=[accepted_by_user_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index('ix_audit_logs_org_id', 'organization_id'),
        Index('ix_audit_logs_created_at', 'created_at'),
        Index('ix_audit_logs_action', 'action'),
        Index('ix_audit_logs_entity_type', 'entity_type'),
        # Task #173 — composite for the most common access pattern:
        # "show me all audit log rows for this entity in this org".
        Index('ix_audit_logs_org_entity', 'organization_id', 'entity_type', 'entity_id'),
    )

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=True)
    entity_name = Column(String, nullable=True)
    details = Column(JSONB().with_variant(JSON(), 'sqlite'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization")
    user = relationship("User")


class RegistrationReport(Base):
    __tablename__ = "registration_reports"
    __table_args__ = (
        Index('ix_registration_reports_org_id', 'organization_id'),
        Index('ix_registration_reports_organization_id', 'organization_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    report_type = Column(String, nullable=False, default="SONGS")
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="GENERATED")
    filter_creator_id = Column(Integer, nullable=True)
    filter_status = Column(String, nullable=True)
    item_count = Column(Integer, default=0)
    outstanding_count = Column(Integer, default=0)
    ready_count = Column(Integer, default=0)
    needs_attention_count = Column(Integer, default=0)
    report_data = Column(Text, nullable=True)
    pdf_data = Column(LargeBinary, nullable=True)
    pdf_mime = Column(String, nullable=True)
    generated_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    sent_to = Column(String, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    created_by = relationship("User")


class AccountMergeRequest(Base):
    __tablename__ = "account_merge_requests"
    __table_args__ = (
        Index('ix_merge_requests_status', 'status'),
        Index('ix_merge_requests_requesting_user', 'requesting_user_id'),
        Index('ix_merge_requests_target_user', 'target_user_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    requesting_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    linked_creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)

    status = Column(String, default="PENDING_VERIFICATION")
    verification_code = Column(String, nullable=True)
    verification_expires_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    admin_notes = Column(String, nullable=True)
    resolved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    requesting_user = relationship("User", foreign_keys=[requesting_user_id])
    target_user = relationship("User", foreign_keys=[target_user_id])
    organization = relationship("Organization")
    linked_creator = relationship("Creator")
    resolved_by = relationship("User", foreign_keys=[resolved_by_user_id])


class SharedItemType(str, enum.Enum):
    DOCUMENT = "DOCUMENT"
    CONTACT_CARD = "CONTACT_CARD"
    AUDIO = "AUDIO"
    STATEMENT = "STATEMENT"
    SONG = "SONG"
    CONTRACT = "CONTRACT"


class SharedItemStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    DISMISSED = "DISMISSED"


class SharedItem(Base):
    __tablename__ = "shared_items"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    item_type = Column(String, nullable=False)
    item_id = Column(Integer, nullable=False)
    item_name = Column(String, nullable=True)
    shared_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    shared_with_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    shared_with_email = Column(String, nullable=True)
    shared_with_org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    message = Column(Text, nullable=True)
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", foreign_keys=[organization_id])
    shared_by_user = relationship("User", foreign_keys=[shared_by_user_id])
    shared_with_user = relationship("User", foreign_keys=[shared_with_user_id])
