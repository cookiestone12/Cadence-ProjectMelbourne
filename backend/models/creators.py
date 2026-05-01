from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON, Enum, UniqueConstraint, Index, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class CreatorRole(str, enum.Enum):
    ARTIST = "ARTIST"
    SONGWRITER = "SONGWRITER"
    PRODUCER = "PRODUCER"


class CreditRole(str, enum.Enum):
    ARTIST = "ARTIST"
    FEATURED_ARTIST = "FEATURED_ARTIST"
    SONGWRITER = "SONGWRITER"
    PRODUCER = "PRODUCER"
    MIX_ENGINEER = "MIX_ENGINEER"
    OTHER = "OTHER"


class CreatorContactRole(str, enum.Enum):
    DISTRIBUTION = "DISTRIBUTION"
    LEGAL = "LEGAL"
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    PUBLISHER = "PUBLISHER"
    A_AND_R = "A_AND_R"
    MARKETING = "MARKETING"
    OTHER = "OTHER"


class ContributorType(str, enum.Enum):
    ARTIST = "ARTIST"
    SONGWRITER = "SONGWRITER"
    PRODUCER = "PRODUCER"
    PUBLISHER = "PUBLISHER"
    LABEL = "LABEL"
    MANAGER = "MANAGER"
    ENGINEER = "ENGINEER"
    OTHER = "OTHER"


class Creator(Base):
    __tablename__ = "creators"
    __table_args__ = (
        Index('ix_creators_organization_id', 'organization_id'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    display_name = Column(String, index=True, nullable=False)
    legal_name = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)
    roles = Column(JSON, default=list)
    primary_territory = Column(String, nullable=True)
    primary_pro = Column(String, nullable=True)
    primary_ipi = Column(String, nullable=True)
    hero_image_url = Column(String, nullable=True)
    hero_image_data = Column(LargeBinary, nullable=True)
    hero_image_mime = Column(String, nullable=True)
    linked_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    contributor_type = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    publisher_name = Column(String, nullable=True)
    label_affiliation = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    website_url = Column(String, nullable=True)
    spotify_artist_id = Column(String, nullable=True)
    apple_music_id = Column(String, nullable=True)
    spotify_url = Column(String, nullable=True)
    apple_music_url = Column(String, nullable=True)
    youtube_url = Column(String, nullable=True)
    instagram_url = Column(String, nullable=True)
    twitter_url = Column(String, nullable=True)
    custom_links = Column(JSONB().with_variant(JSON(), 'sqlite'), default=list)
    roster_export_fields = Column(JSON, default=list)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    publisher_contact_id = Column(Integer, nullable=True)
    admin_contact_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    organization = relationship("Organization", back_populates="creators")
    song_credits = relationship("SongCredit", back_populates="creator")
    work_credits = relationship("WorkCredit", back_populates="creator")
    linked_user = relationship("User", foreign_keys=[linked_user_id])
    assigned_user = relationship("User", foreign_keys=[assigned_to_user_id])
    creator_contacts = relationship("CreatorContact", back_populates="creator", cascade="all, delete-orphan")


class CreatorContact(Base):
    __tablename__ = "creator_contacts"
    __table_args__ = (
        UniqueConstraint('creator_id', 'contact_id', 'role', name='uq_creator_contact_role'),
        Index('ix_creator_contacts_creator_id', 'creator_id'),
        Index('ix_creator_contacts_contact_id', 'contact_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(Integer, ForeignKey("creative_contacts.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False, default="OTHER")
    is_primary = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship("Creator", back_populates="creator_contacts")
    contact = relationship("CreativeContact")


class CreativeContact(Base):
    __tablename__ = "creative_contacts"
    __table_args__ = (
        Index('ix_creative_contacts_organization_id', 'organization_id'),
        Index('ix_creative_contacts_creator_id', 'creator_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    display_name = Column(String, nullable=False, index=True)
    legal_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    pro = Column(String, nullable=True)
    ipi = Column(String, nullable=True)
    isni = Column(String, nullable=True)
    publisher_name = Column(String, nullable=True)
    publisher_ipi = Column(String, nullable=True)
    publisher_pro = Column(String, nullable=True)
    roles = Column(JSON, default=list)
    representation_name = Column(String, nullable=True)
    representation_email = Column(String, nullable=True)
    representation_phone = Column(String, nullable=True)
    territory = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    photo_url = Column(String, nullable=True)
    photo_data = Column(LargeBinary, nullable=True)
    photo_mime = Column(String, nullable=True)
    is_private = Column(Boolean, default=False, nullable=False, server_default="false")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SharedContactLink(Base):
    __tablename__ = "shared_contact_links"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    contact_ids = Column(JSON, nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ClientSharedContact(Base):
    __tablename__ = "client_shared_contacts"
    __table_args__ = (
        UniqueConstraint('creative_contact_id', 'shared_with_user_id', name='uq_client_shared_contact'),
        Index('ix_client_shared_contacts_org_id', 'organization_id'),
        Index('ix_client_shared_contacts_user_id', 'shared_with_user_id'),
        Index('ix_client_shared_contacts_contact_id', 'creative_contact_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    creative_contact_id = Column(Integer, ForeignKey("creative_contacts.id", ondelete="CASCADE"), nullable=False)
    shared_with_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shared_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization")
    creative_contact = relationship("CreativeContact")
    shared_with_user = relationship("User", foreign_keys=[shared_with_user_id])
    shared_by_user = relationship("User", foreign_keys=[shared_by_user_id])
