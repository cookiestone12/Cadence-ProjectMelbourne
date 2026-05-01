from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON, Enum, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class NotificationType(str, enum.Enum):
    MISSING_ISRC = "MISSING_ISRC"
    MISSING_ISWC = "MISSING_ISWC"
    CONTRACT_PENDING = "CONTRACT_PENDING"
    PRO_INCOMPLETE = "PRO_INCOMPLETE"
    WEEKLY_HEALTH_SUMMARY = "WEEKLY_HEALTH_SUMMARY"
    CUSTOM_DEADLINE = "CUSTOM_DEADLINE"
    SYSTEM_ANNOUNCEMENT = "SYSTEM_ANNOUNCEMENT"
    CATALOG_UPDATE = "CATALOG_UPDATE"
    PLACEMENT_UPDATE = "PLACEMENT_UPDATE"
    CLIENT_SHARE = "CLIENT_SHARE"
    PAYOUT_UNWOUND_BY_STATEMENT_DELETE = "PAYOUT_UNWOUND_BY_STATEMENT_DELETE"


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint('user_id', 'notification_type', name='uq_user_notification_type'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(String, nullable=False)
    
    in_app_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=False)
    
    frequency = Column(String, default="immediate")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User")


class OrgNotificationSetting(Base):
    __tablename__ = "org_notification_settings"
    __table_args__ = (
        UniqueConstraint('organization_id', 'notification_type', name='uq_org_notification_type'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    notification_type = Column(String, nullable=False)
    
    default_frequency = Column(String, default="immediate")
    allow_user_override = Column(Boolean, default=True)
    
    rollup_digest_enabled = Column(Boolean, default=False)
    digest_frequency = Column(String, default="weekly")
    digest_day = Column(Integer, default=1)
    digest_hour = Column(Integer, default=9)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    organization = relationship("Organization")


class EmailDigestPreference(Base):
    __tablename__ = "email_digest_preferences"
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_user_email_digest'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    email_digest_enabled = Column(Boolean, default=False)
    schedule_interval = Column(String, default="weekly")
    min_priority_threshold = Column(Integer, default=3)
    preferred_hour = Column(Integer, default=9)

    last_email_sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")


class ActionItem(Base):
    __tablename__ = "action_items"
    __table_args__ = (
        Index('ix_action_items_org_creator', 'organization_id', 'creator_id'),
        Index('ix_action_items_priority', 'organization_id', 'priority', 'deadline'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    
    work_id = Column(Integer, ForeignKey("works.id"), nullable=True)
    release_id = Column(Integer, ForeignKey("releases.id"), nullable=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    placement_id = Column(Integer, ForeignKey("placements.id"), nullable=True)
    
    entity_type = Column(String, nullable=True)
    entity_label = Column(String, nullable=True)
    entity_id = Column(Integer, nullable=True, index=True)

    action_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    priority = Column(Integer, default=2)
    status = Column(String, default="PENDING")
    
    deadline = Column(DateTime, nullable=True)
    reminder_days_before = Column(Integer, default=3)
    last_reminder_sent = Column(DateTime, nullable=True)
    
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    completed_at = Column(DateTime, nullable=True)
    completed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    is_auto_generated = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    organization = relationship("Organization")
    creator = relationship("Creator")
    song = relationship("Song")
    work = relationship("Work")
    release = relationship("Release")
    contract = relationship("Contract")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    completed_by = relationship("User", foreign_keys=[completed_by_user_id])


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index('ix_notifications_user_read', 'user_id', 'is_read'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    
    notification_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    link = Column(String, nullable=True)
    extra_data = Column(JSON, nullable=True)
    
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")
    organization = relationship("Organization")


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    endpoint = Column(Text, nullable=False, unique=True)
    p256dh = Column(String, nullable=False)
    auth = Column(String, nullable=False)
    user_agent = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")
