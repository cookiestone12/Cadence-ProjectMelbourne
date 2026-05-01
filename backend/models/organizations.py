from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class OrganizationType(str, enum.Enum):
    LABEL = "LABEL"
    PUBLISHER = "PUBLISHER"
    PRODUCTION_COMPANY = "PRODUCTION_COMPANY"
    MANAGER = "MANAGER"
    INDIVIDUAL = "INDIVIDUAL"


class OrganizationMemberRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    CLIENT = "CLIENT"


class AccountType(str, enum.Enum):
    INDIVIDUAL = "INDIVIDUAL"
    ENTERPRISE = "ENTERPRISE"


class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String)
    account_type = Column(String, default="ENTERPRISE")
    
    display_name = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    logo_orientation = Column(String, default="square")
    primary_color = Column(String, nullable=True)
    
    access_code = Column(String, unique=True, nullable=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    members = relationship("OrganizationMember", back_populates="organization")
    creators = relationship("Creator", back_populates="organization")
    songs = relationship("Song", back_populates="organization")


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    can_manage_roster = Column(Boolean, default=False)
    linked_creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    client_access_scope = Column(String, nullable=True, default="OWN")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="organization_memberships")
    linked_creator = relationship("Creator", foreign_keys=[linked_creator_id])
