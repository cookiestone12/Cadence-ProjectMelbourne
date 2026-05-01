from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, Date, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class ExpenseCategory(str, enum.Enum):
    PRODUCER_FEE = "PRODUCER_FEE"
    DAY_RATE = "DAY_RATE"
    VIDEO_PRODUCTION = "VIDEO_PRODUCTION"
    CONTENT_CREATION = "CONTENT_CREATION"
    LEGAL = "LEGAL"
    MARKETING = "MARKETING"
    TRAVEL = "TRAVEL"
    STUDIO = "STUDIO"
    MIXING_MASTERING = "MIXING_MASTERING"
    OTHER = "OTHER"


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        Index('ix_expenses_org_id', 'organization_id'),
    )
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    category = Column(String, nullable=False, default="OTHER")
    description = Column(String, nullable=False)
    amount_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String, default="USD")
    payee_name = Column(String, nullable=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    placement_id = Column(Integer, ForeignKey("placements.id"), nullable=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    expense_date = Column(Date, nullable=True)
    status = Column(String, default="PENDING")
    payment_method = Column(String, nullable=True)
    invoice_reference = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    budget_source = Column(String, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    organization = relationship("Organization")
    creator = relationship("Creator")
    contract = relationship("Contract")
    placement = relationship("Placement")
    song = relationship("Song")
    created_by = relationship("User")


class Placement(Base):
    __tablename__ = "placements"
    __table_args__ = (
        Index('ix_placements_org_id', 'organization_id'),
        Index('ix_placements_status', 'status'),
        Index('ix_placements_song_id', 'song_id'),
        Index('ix_placements_release_id', 'release_id'),
        Index('ix_placements_work_id', 'work_id'),
        Index('ix_placements_updated_at', 'updated_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    placement_type = Column(String, nullable=False, default="SYNC")
    status = Column(String, nullable=False, default="PITCHED")

    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    work_id = Column(Integer, ForeignKey("works.id"), nullable=True)
    release_id = Column(Integer, ForeignKey("releases.id"), nullable=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)

    client_name = Column(String, nullable=True)
    project_name = Column(String, nullable=True)
    media_type = Column(String, nullable=True)

    license_fee = Column(Float, nullable=True, default=0.0)
    license_currency = Column(String, default="USD")
    license_type = Column(String, nullable=True)
    territory = Column(String, nullable=True)
    usage_notes = Column(Text, nullable=True)

    pitched_date = Column(Date, nullable=True)
    secured_date = Column(Date, nullable=True)
    delivery_date = Column(Date, nullable=True)
    air_date = Column(Date, nullable=True)

    contact_name = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)

    notes = Column(Text, nullable=True)

    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    song = relationship("Song")
    work = relationship("Work")
    release = relationship("Release")
    contract = relationship("Contract")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
