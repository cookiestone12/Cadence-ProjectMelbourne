from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON, Enum, Date, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class PRO(str, enum.Enum):
    ASCAP = "ASCAP"
    BMI = "BMI"
    PRS = "PRS"
    SESAC = "SESAC"
    OTHER = "OTHER"


class AccountLinkStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class AccountLinkPermission(str, enum.Enum):
    VIEW_ONLY = "VIEW_ONLY"
    EDIT = "EDIT"
    FULL_ACCESS = "FULL_ACCESS"


class IPAssetType(str, enum.Enum):
    TRACK = "TRACK"
    VIDEO = "VIDEO"
    PODCAST = "PODCAST"
    AUDIOBOOK = "AUDIOBOOK"
    OTHER = "OTHER"


class AccountLink(Base):
    __tablename__ = "account_links"
    __table_args__ = (
        Index('ix_account_links_individual', 'individual_org_id'),
        Index('ix_account_links_enterprise', 'enterprise_org_id'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    individual_org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    enterprise_org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    status = Column(String, default="PENDING")
    permission_level = Column(String, default="VIEW_ONLY")
    
    initiated_by = Column(String, nullable=False)
    individual_consent = Column(Boolean, default=False)
    enterprise_consent = Column(Boolean, default=False)
    
    agreement_terms = Column(Text, nullable=True)
    start_date = Column(DateTime, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    individual_org = relationship("Organization", foreign_keys=[individual_org_id])
    enterprise_org = relationship("Organization", foreign_keys=[enterprise_org_id])


class SongContract(Base):
    __tablename__ = "song_contracts"
    __table_args__ = (
        Index('ix_song_contracts_song_id', 'song_id'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String, default="application/pdf")
    
    contract_type = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    
    song = relationship("Song", back_populates="contracts")
    organization = relationship("Organization")
    uploaded_by = relationship("User")
    contract = relationship("Contract")


class ContractType(str, enum.Enum):
    MASTER = "MASTER"
    PUBLISHING = "PUBLISHING"
    SYNC_LICENSE = "SYNC_LICENSE"
    DISTRIBUTION = "DISTRIBUTION"
    MANAGEMENT = "MANAGEMENT"
    ADMINISTRATION = "ADMINISTRATION"
    CO_PUBLISHING = "CO_PUBLISHING"
    SUB_PUBLISHING = "SUB_PUBLISHING"
    OTHER = "OTHER"


class ContractStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"


class AssetType(str, enum.Enum):
    SONG = "SONG"
    WORK = "WORK"


class RightsType(str, enum.Enum):
    MASTER = "MASTER"
    PUBLISHING = "PUBLISHING"
    SYNC = "SYNC"
    MECHANICAL = "MECHANICAL"
    PERFORMANCE = "PERFORMANCE"
    NEIGHBORING = "NEIGHBORING"
    OTHER = "OTHER"


class PartyRole(str, enum.Enum):
    LICENSOR = "LICENSOR"
    LICENSEE = "LICENSEE"
    ASSIGNOR = "ASSIGNOR"
    ASSIGNEE = "ASSIGNEE"
    PUBLISHER = "PUBLISHER"
    SUB_PUBLISHER = "SUB_PUBLISHER"
    ADMINISTRATOR = "ADMINISTRATOR"
    ARTIST = "ARTIST"
    LABEL = "LABEL"
    DISTRIBUTOR = "DISTRIBUTOR"
    OTHER = "OTHER"


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (
        Index('ix_contracts_organization_id', 'organization_id'),
        Index('ix_contracts_status', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    title = Column(String, nullable=False, index=True)
    contract_type = Column(String, nullable=False, default="OTHER")
    payment_direction = Column(String, nullable=True, default="INCOMING")
    status = Column(String, nullable=False, default="DRAFT")
    reference_number = Column(String, nullable=True)

    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    territory = Column(JSON, default=list)

    advance_amount = Column(Float, nullable=True, default=0.0)
    advance_currency = Column(String, default="USD")
    advance_recouped = Column(Float, nullable=True, default=0.0)

    notes = Column(Text, nullable=True)
    terms_summary = Column(Text, nullable=True)

    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    organization = relationship("Organization")
    created_by = relationship("User")
    creator = relationship("Creator")
    parties = relationship("ContractParty", back_populates="contract", cascade="all, delete-orphan")
    assets = relationship("ContractAsset", back_populates="contract", cascade="all, delete-orphan")
    documents = relationship("ContractDocument", back_populates="contract", cascade="all, delete-orphan")


class ContractParty(Base):
    __tablename__ = "contract_parties"
    __table_args__ = (
        Index('ix_contract_parties_contract_id', 'contract_id'),
        Index('ix_contract_parties_creator_id', 'creator_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)

    party_name = Column(String, nullable=False)
    party_role = Column(String, nullable=False, default="OTHER")
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)

    contact_email = Column(String, nullable=True)
    contact_info = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="parties")
    creator = relationship("Creator")


class ContractAsset(Base):
    __tablename__ = "contract_assets"
    __table_args__ = (
        UniqueConstraint('contract_id', 'asset_type', 'asset_id', name='uq_contract_asset'),
        Index('ix_contract_assets_contract_id', 'contract_id'),
        Index('ix_contract_assets_asset', 'asset_type', 'asset_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    asset_type = Column(String, nullable=False)
    asset_id = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="assets")


class ContractDocument(Base):
    __tablename__ = "contract_documents"
    __table_args__ = (
        Index('ix_contract_documents_contract_id', 'contract_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    description = Column(String, nullable=True)

    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    work_id = Column(Integer, ForeignKey("works.id"), nullable=True)
    release_id = Column(Integer, ForeignKey("releases.id"), nullable=True)

    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="documents")
    organization = relationship("Organization")
    uploaded_by = relationship("User")


class RightsSplit(Base):
    __tablename__ = "rights_splits"
    __table_args__ = (
        Index('ix_rights_splits_contract_asset_id', 'contract_asset_id'),
        Index('ix_rights_splits_rights_holder_id', 'rights_holder_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    contract_asset_id = Column(Integer, ForeignKey("contract_assets.id", ondelete="CASCADE"), nullable=False)
    rights_holder_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    rights_holder_name = Column(String, nullable=True)

    rights_type = Column(String, nullable=False, default="MASTER")
    share_percentage = Column(Float, nullable=False)
    role = Column(String, nullable=True)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contract_asset = relationship("ContractAsset")
    rights_holder = relationship("Creator", foreign_keys=[rights_holder_id])
