from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON, Enum, Date, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class LegacyStatementStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    PARTIALLY_MATCHED = "PARTIALLY_MATCHED"


class TransactionMatchStatus(str, enum.Enum):
    MATCHED = "MATCHED"
    UNMATCHED = "UNMATCHED"
    MANUAL = "MANUAL"


class PaymentStatus(str, enum.Enum):
    PENDING_PAYMENT = "PENDING"
    APPROVED = "APPROVED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class RoyaltyStatement(Base):
    __tablename__ = "royalty_statements"
    __table_args__ = (
        Index('ix_royalty_statements_org_id', 'organization_id'),
        Index('ix_royalty_statements_status', 'status'),
        Index('ix_royalty_statements_period', 'period_start', 'period_end'),
        Index('ix_royalty_statements_creator_id', 'creator_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    source_name = Column(String, nullable=False)
    source_type = Column(String, nullable=True)

    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)

    currency = Column(String, default="USD")
    exchange_rate = Column(Float, default=1.0)

    file_name = Column(String, nullable=True)
    file_path = Column(String, nullable=True)

    total_revenue_cents = Column(Integer, default=0)
    total_transactions = Column(Integer, default=0)
    matched_transactions = Column(Integer, default=0)
    unmatched_transactions = Column(Integer, default=0)

    status = Column(String, default="PENDING")
    processing_notes = Column(Text, nullable=True)

    column_mapping = Column(JSON, nullable=True)

    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)

    reported_gross = Column(Float, nullable=True)
    reported_withholding = Column(Float, nullable=True)
    reported_net = Column(Float, nullable=True)
    reconciliation_result = Column(JSON, nullable=True)

    opening_balance = Column(Float, nullable=True)
    closing_balance = Column(Float, nullable=True)
    reconciliation_details = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transactions = relationship("RoyaltyTransaction", back_populates="statement", cascade="all, delete-orphan")
    statement_lines = relationship("RoyaltyStatementLine", back_populates="statement", cascade="all, delete-orphan")
    organization = relationship("Organization")
    uploaded_by = relationship("User")


class RoyaltyTransaction(Base):
    __tablename__ = "royalty_transactions"
    __table_args__ = (
        Index('ix_royalty_tx_statement_id', 'statement_id'),
        Index('ix_royalty_tx_song_id', 'song_id'),
        Index('ix_royalty_tx_match_status', 'match_status'),
        Index('ix_royalty_tx_org_id', 'organization_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(Integer, ForeignKey("royalty_statements.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    original_track_title = Column(String, nullable=True)
    original_artist = Column(String, nullable=True)
    original_isrc = Column(String, nullable=True)
    original_upc = Column(String, nullable=True)

    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    match_status = Column(String, default="UNMATCHED")
    match_confidence = Column(Float, nullable=True)

    revenue_cents = Column(Integer, default=0)
    currency = Column(String, default="USD")
    quantity = Column(Integer, default=0)

    territory = Column(String, nullable=True)
    platform = Column(String, nullable=True)
    revenue_type = Column(String, nullable=True)

    raw_data = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    statement = relationship("RoyaltyStatement", back_populates="transactions")
    song = relationship("Song")
    allocations = relationship("RoyaltyAllocation", back_populates="transaction", cascade="all, delete-orphan")


class RoyaltyAllocation(Base):
    __tablename__ = "royalty_allocations"
    __table_args__ = (
        Index('ix_royalty_alloc_tx_id', 'transaction_id'),
        Index('ix_royalty_alloc_contract_id', 'contract_id'),
        Index('ix_royalty_alloc_holder_id', 'rights_holder_id'),
        Index('ix_royalty_alloc_org_id', 'organization_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("royalty_transactions.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    rights_holder_id = Column(Integer, ForeignKey("creators.id"), nullable=False)

    rights_type = Column(String, nullable=False)
    share_percentage = Column(Float, nullable=False)
    allocated_cents = Column(Integer, default=0)

    is_recoupable = Column(Boolean, default=False)
    recouped_cents = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("RoyaltyTransaction", back_populates="allocations")
    contract = relationship("Contract")
    rights_holder = relationship("Creator")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index('ix_payments_org_id', 'organization_id'),
        Index('ix_payments_payee_id', 'payee_id'),
        Index('ix_payments_status', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    payee_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)

    amount_cents = Column(Integer, nullable=False)
    currency = Column(String, default="USD")

    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)

    status = Column(String, default="PENDING")

    payment_date = Column(Date, nullable=True)
    payment_method = Column(String, nullable=True)
    payment_reference = Column(String, nullable=True)

    notes = Column(Text, nullable=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    payee = relationship("Creator")
    contract = relationship("Contract")
    created_by = relationship("User")


class FeeType(str, enum.Enum):
    MANAGEMENT_FEE = "MANAGEMENT_FEE"
    ADMIN_FEE = "ADMIN_FEE"
    DISTRIBUTION_FEE = "DISTRIBUTION_FEE"
    SYNC_FEE = "SYNC_FEE"
    LEGAL_FEE = "LEGAL_FEE"
    OTHER = "OTHER"


class Fee(Base):
    __tablename__ = "fees"
    __table_args__ = (
        Index('ix_fees_org_id', 'organization_id'),
        Index('ix_fees_creator_id', 'creator_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    placement_id = Column(Integer, ForeignKey("placements.id"), nullable=True)

    fee_type = Column(String, nullable=False, default="MANAGEMENT_FEE")
    description = Column(String, nullable=True)
    amount_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String, default="USD")
    fee_date = Column(Date, nullable=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    status = Column(String, default="PENDING")
    notes = Column(Text, nullable=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    creator = relationship("Creator")
    contract = relationship("Contract")
    song = relationship("Song")
    placement = relationship("Placement")
    created_by = relationship("User")


# Legacy v1 ``Advance`` removed in Task #169. The v1 ``advances`` table was
# dropped by Alembic revision ``b7c8d9e0f1a2``; the v2 ``advance_pools`` table
# was renamed to ``advances`` and is now mapped by the consolidated ``Advance``
# class defined further down (formerly ``AdvanceV2``).


class ProviderType(str, enum.Enum):
    PRO = "PRO"
    DSP = "DSP"
    DISTRIBUTOR = "DISTRIBUTOR"
    LABEL = "LABEL"
    PUBLISHER = "PUBLISHER"
    OTHER = "OTHER"


class RevenueType(str, enum.Enum):
    MASTER = "MASTER"
    PUBLISHING = "PUBLISHING"
    MECHANICAL = "MECHANICAL"
    PERFORMANCE = "PERFORMANCE"
    SYNC = "SYNC"
    NEIGHBORING = "NEIGHBORING"
    OTHER = "OTHER"


class MatchStatus(str, enum.Enum):
    UNMATCHED = "UNMATCHED"
    AUTO_MATCHED = "AUTO_MATCHED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    IGNORED = "IGNORED"


class ProcessingRunStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"


class LedgerEntryType(str, enum.Enum):
    EARNING = "EARNING"
    FEE = "FEE"
    RECOUPMENT_APPLIED = "RECOUPMENT_APPLIED"
    PAYABLE_CREATED = "PAYABLE_CREATED"
    PAYMENT = "PAYMENT"
    REVERSAL = "REVERSAL"
    ADJUSTMENT = "ADJUSTMENT"


class PayeeType(str, enum.Enum):
    CREATOR = "CREATOR"
    COMPANY = "COMPANY"
    PUBLISHER = "PUBLISHER"
    LABEL = "LABEL"
    OTHER = "OTHER"


class RecoupmentPool(str, enum.Enum):
    MASTER = "MASTER"
    PUBLISHING = "PUBLISHING"
    BOTH = "BOTH"
    CUSTOM = "CUSTOM"


class PayoutStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    PAID = "PAID"
    VOID = "VOID"


class StatementStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    MAPPING_REQUIRED = "MAPPING_REQUIRED"
    MAPPING_COMPLETE = "MAPPING_COMPLETE"
    MATCHING = "MATCHING"
    READY_TO_PROCESS = "READY_TO_PROCESS"
    PROCESSED = "PROCESSED"
    LOCKED = "LOCKED"


class Payee(Base):
    __tablename__ = "payees"
    __table_args__ = (
        UniqueConstraint('org_id', 'creator_id', name='uq_payee_org_creator'),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    payee_type = Column(String, nullable=False)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    company_name = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    payment_details_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("Creator")
    organization = relationship("Organization")


class RoyaltyStatementLine(Base):
    __tablename__ = "royalty_statement_lines"
    __table_args__ = (
        Index('ix_rsl_org_statement', 'org_id', 'statement_id'),
        Index('ix_rsl_org_isrc', 'org_id', 'isrc'),
        Index('ix_rsl_org_match_status', 'org_id', 'match_status'),
        Index('ix_rsl_org_matched_song', 'org_id', 'matched_song_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    statement_id = Column(Integer, ForeignKey("royalty_statements.id", ondelete="CASCADE"), nullable=False)
    line_hash = Column(String, nullable=True, index=True)
    isrc = Column(String, nullable=True)
    upc = Column(String, nullable=True)
    iswc = Column(String, nullable=True)
    track_title_raw = Column(String, nullable=True)
    release_title_raw = Column(String, nullable=True)
    artist_name_raw = Column(String, nullable=True)
    label_raw = Column(String, nullable=True)
    territory = Column(String, nullable=True)
    store = Column(String, nullable=True)
    usage_type = Column(String, nullable=True)
    revenue_type = Column(String, nullable=True)
    unit_count = Column(Float, nullable=True)
    gross_amount = Column(Float, nullable=True)
    deductions_amount = Column(Float, nullable=True)
    net_amount = Column(Float, default=0)
    currency = Column(String, nullable=True)
    fx_rate_to_statement_currency = Column(Float, nullable=True)
    net_amount_statement_currency = Column(Float, default=0)
    matched_song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    matched_work_id = Column(Integer, ForeignKey("works.id"), nullable=True)
    matched_release_id = Column(Integer, ForeignKey("releases.id"), nullable=True)
    match_status = Column(String, default="UNMATCHED")
    match_confidence = Column(Float, nullable=True)
    match_method = Column(String, nullable=True)
    matched_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    matched_at = Column(DateTime, nullable=True)
    canonical_right_category = Column(String, nullable=True)
    canonical_channel = Column(String, nullable=True)
    accounting_flags = Column(JSON, nullable=True)
    territory_iso2 = Column(String, nullable=True)
    territory_confidence = Column(String, nullable=True)
    activity_period_start = Column(Date, nullable=True)
    activity_period_end = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    statement = relationship("RoyaltyStatement", back_populates="statement_lines")
    song = relationship("Song")
    work = relationship("Work")
    release = relationship("Release")


class RoyaltyProcessingRun(Base):
    __tablename__ = "royalty_processing_runs"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    statement_id = Column(Integer, ForeignKey("royalty_statements.id"), nullable=False, index=True)
    run_version = Column(Integer, nullable=False)
    status = Column(String, default="RUNNING")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    started_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    summary_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RoyaltyLedgerEntry(Base):
    __tablename__ = "royalty_ledger_entries"
    __table_args__ = (
        Index('ix_rle_org_payee_created', 'org_id', 'payee_id', 'created_at'),
        Index('ix_rle_org_contract', 'org_id', 'contract_id'),
        Index('ix_rle_org_entry_type', 'org_id', 'entry_type'),
        Index('ix_rle_org_statement', 'org_id', 'statement_id'),
        Index('ix_rle_org_processing_run', 'org_id', 'processing_run_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    statement_id = Column(Integer, ForeignKey("royalty_statements.id"), nullable=False)
    statement_line_id = Column(Integer, ForeignKey("royalty_statement_lines.id"), nullable=True)
    processing_run_id = Column(Integer, ForeignKey("royalty_processing_runs.id"), nullable=False)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    work_id = Column(Integer, ForeignKey("works.id"), nullable=True)
    release_id = Column(Integer, ForeignKey("releases.id"), nullable=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    payee_id = Column(Integer, ForeignKey("payees.id"), nullable=False)
    entry_type = Column(String, nullable=False)
    revenue_type = Column(String, nullable=True)
    source = Column(String, nullable=True)
    amount_cents = Column(Integer, nullable=False)
    payee_currency = Column(String, nullable=True)
    amount_payee_currency_cents = Column(Integer, nullable=True)
    fx_rate = Column(Float, nullable=True)
    advance_id = Column(Integer, ForeignKey("advances.id"), nullable=True)
    recoupment_pool = Column(String, nullable=True)
    memo = Column(Text, nullable=True)
    payout_item_id = Column(Integer, ForeignKey("payout_items.id"), nullable=True, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Advance(Base):
    """Consolidated Advance model (formerly ``AdvanceV2``).

    Backed by the ``advances`` table (renamed from ``advance_pools`` in revision
    ``b7c8d9e0f1a2``). Keyed by ``payee_id`` (Payee may wrap a creator or company).
    """
    __tablename__ = "advances"
    __table_args__ = (
        Index('ix_advances_org_payee', 'org_id', 'payee_id'),
        Index('ix_advances_org_contract', 'org_id', 'contract_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    payee_id = Column(Integer, ForeignKey("payees.id"), nullable=False)
    advance_name = Column(String, nullable=False)
    advance_date = Column(Date, nullable=False)
    currency = Column(String, default="USD")
    principal_amount_cents = Column(Integer, nullable=False)
    recoupable = Column(Boolean, default=True)
    recoupment_pool = Column(String, nullable=False)
    recoupment_priority = Column(Integer, default=1)
    cross_collateralize = Column(Boolean, default=False)
    start_recouping_on = Column(Date, nullable=True)
    end_recouping_on = Column(Date, nullable=True)
    outstanding_balance_cents = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    payee = relationship("Payee")
    contract = relationship("Contract")
    organization = relationship("Organization")


class PayoutBatch(Base):
    __tablename__ = "payout_batches"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    currency = Column(String, default="USD")
    status = Column(String, default="DRAFT")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("PayoutItem", back_populates="batch", cascade="all, delete-orphan")
    organization = relationship("Organization")
    created_by = relationship("User")


class PayoutItem(Base):
    __tablename__ = "payout_items"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("payout_batches.id"), nullable=False, index=True)
    payee_id = Column(Integer, ForeignKey("payees.id"), nullable=False, index=True)
    amount_cents = Column(Integer, nullable=False)
    memo = Column(Text, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    payment_method = Column(String, nullable=True)
    external_reference = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    batch = relationship("PayoutBatch", back_populates="items")
    payee = relationship("Payee")


RoyaltyStatement.statement_lines = relationship("RoyaltyStatementLine", back_populates="statement", cascade="all, delete-orphan")
RoyaltyStatement.processing_runs = relationship("RoyaltyProcessingRun", backref="statement")


# Backwards-compatibility alias: code that still imports ``AdvanceV2`` keeps
# working. New code should use ``Advance`` directly.
AdvanceV2 = Advance
