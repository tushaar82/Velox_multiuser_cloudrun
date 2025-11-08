"""
User authentication and management data models.
Implements User, UserAccount, AccountAccess, InvestorInvitation, and Session tables.
"""
import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Integer, 
    String, Text, CheckConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from shared.database.connection import Base


class UserRole(PyEnum):
    """User role enumeration."""
    ADMIN = "admin"
    TRADER = "trader"
    INVESTOR = "investor"


class InvitationStatus(PyEnum):
    """Investor invitation status enumeration."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class User(Base):
    """User model for authentication and authorization."""
    
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        Enum(UserRole, name="user_role", create_type=True),
        nullable=False,
        default=UserRole.TRADER
    )
    is_locked = Column(Boolean, default=False, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    trader_accounts = relationship(
        "UserAccount", 
        back_populates="trader",
        foreign_keys="UserAccount.trader_id",
        cascade="all, delete-orphan"
    )
    account_accesses = relationship("AccountAccess", back_populates="user", cascade="all, delete-orphan")
    sent_invitations = relationship(
        "InvestorInvitation",
        back_populates="inviter",
        foreign_keys="InvestorInvitation.inviter_id",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, role={self.role.value})>"


class UserAccount(Base):
    """User account model for multi-user account sharing."""
    
    __tablename__ = "user_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trader_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    trader = relationship("User", back_populates="trader_accounts", foreign_keys=[trader_id])
    account_accesses = relationship("AccountAccess", back_populates="account", cascade="all, delete-orphan")
    invitations = relationship("InvestorInvitation", back_populates="account", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<UserAccount(id={self.id}, name={self.name}, trader_id={self.trader_id})>"


class AccountAccess(Base):
    """Account access model for managing user permissions on accounts."""
    
    __tablename__ = "account_access"
    
    account_id = Column(UUID(as_uuid=True), ForeignKey("user_accounts.id"), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    role = Column(String(20), nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    account = relationship("UserAccount", back_populates="account_accesses")
    user = relationship("User", back_populates="account_accesses")
    
    __table_args__ = (
        CheckConstraint(
            "role IN ('trader', 'investor')",
            name="check_account_access_role"
        ),
    )
    
    def __repr__(self) -> str:
        return f"<AccountAccess(account_id={self.account_id}, user_id={self.user_id}, role={self.role})>"


class InvestorInvitation(Base):
    """Investor invitation model for inviting users to view accounts."""
    
    __tablename__ = "investor_invitations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("user_accounts.id"), nullable=False)
    inviter_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    invitee_email = Column(String(255), nullable=False)
    status = Column(
        Enum(InvitationStatus, name="invitation_status", create_type=True),
        nullable=False,
        default=InvitationStatus.PENDING
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    
    # Relationships
    account = relationship("UserAccount", back_populates="invitations")
    inviter = relationship("User", back_populates="sent_invitations", foreign_keys=[inviter_id])
    
    __table_args__ = (
        Index("idx_invitations_email", "invitee_email", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<InvestorInvitation(id={self.id}, invitee_email={self.invitee_email}, status={self.status.value})>"


class Session(Base):
    """Session model for managing user sessions with JWT tokens."""
    
    __tablename__ = "sessions"
    
    token = Column(String(512), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    last_activity = Column(DateTime, default=datetime.utcnow, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    
    __table_args__ = (
        Index("idx_sessions_user", "user_id", "last_activity"),
        Index("idx_sessions_expiry", "expires_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Session(user_id={self.user_id}, expires_at={self.expires_at})>"
