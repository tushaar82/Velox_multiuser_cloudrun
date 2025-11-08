"""
User management service for account creation, investor invitations, and access control.
Implements multi-user account sharing functionality.
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from shared.models import (
    User, UserAccount, AccountAccess, InvestorInvitation,
    UserRole, InvitationStatus
)

logger = logging.getLogger(__name__)


class UserManagementError(Exception):
    """Base exception for user management errors."""
    pass


class AccountNotFoundError(UserManagementError):
    """Raised when account is not found."""
    pass


class UnauthorizedAccessError(UserManagementError):
    """Raised when user doesn't have permission."""
    pass


class InvitationError(UserManagementError):
    """Raised when invitation operation fails."""
    pass


class UserService:
    """Service for managing user accounts and access control."""
    
    def __init__(self, db_session: Session):
        """
        Initialize user service.
        
        Args:
            db_session: Database session for queries
        """
        self.db = db_session
    
    def create_user_account(
        self,
        trader_id: uuid.UUID,
        account_name: str
    ) -> UserAccount:
        """
        Create a new user account for a trader.
        Automatically grants trader role access to the account.
        
        Args:
            trader_id: ID of the trader creating the account
            account_name: Name for the account
            
        Returns:
            Created user account
            
        Raises:
            UserManagementError: If trader not found or not a trader role
        """
        # Verify trader exists and has trader role
        trader = self.db.query(User).filter(User.id == trader_id).first()
        if not trader:
            raise UserManagementError("Trader not found")
        
        if trader.role != UserRole.TRADER:
            raise UserManagementError("Only traders can create accounts")
        
        # Create account
        account = UserAccount(
            id=uuid.uuid4(),
            trader_id=trader_id,
            name=account_name,
            is_active=True
        )
        
        self.db.add(account)
        self.db.flush()  # Get account ID
        
        # Grant trader access to the account
        access = AccountAccess(
            account_id=account.id,
            user_id=trader_id,
            role='trader'
        )
        
        self.db.add(access)
        self.db.commit()
        self.db.refresh(account)
        
        logger.info(f"User account created: {account.name} by trader {trader.email}")
        return account
    
    def invite_investor(
        self,
        account_id: uuid.UUID,
        inviter_id: uuid.UUID,
        invitee_email: str,
        expiration_days: int = 7
    ) -> InvestorInvitation:
        """
        Create an invitation for an investor to view an account.
        
        Args:
            account_id: Account to grant access to
            inviter_id: User creating the invitation
            invitee_email: Email of the investor to invite
            expiration_days: Days until invitation expires (default: 7)
            
        Returns:
            Created invitation
            
        Raises:
            AccountNotFoundError: If account doesn't exist
            UnauthorizedAccessError: If inviter doesn't have trader access
        """
        # Verify account exists
        account = self.db.query(UserAccount).filter(UserAccount.id == account_id).first()
        if not account:
            raise AccountNotFoundError("Account not found")
        
        # Verify inviter has trader access to the account
        access = self.db.query(AccountAccess).filter(
            AccountAccess.account_id == account_id,
            AccountAccess.user_id == inviter_id,
            AccountAccess.role == 'trader'
        ).first()
        
        if not access:
            raise UnauthorizedAccessError("Only account traders can invite investors")
        
        # Check if there's already a pending invitation for this email
        existing = self.db.query(InvestorInvitation).filter(
            InvestorInvitation.account_id == account_id,
            InvestorInvitation.invitee_email == invitee_email.lower().strip(),
            InvestorInvitation.status == InvitationStatus.PENDING
        ).first()
        
        if existing:
            raise InvitationError("Pending invitation already exists for this email")
        
        # Create invitation
        invitation = InvestorInvitation(
            id=uuid.uuid4(),
            account_id=account_id,
            inviter_id=inviter_id,
            invitee_email=invitee_email.lower().strip(),
            status=InvitationStatus.PENDING,
            expires_at=datetime.utcnow() + timedelta(days=expiration_days)
        )
        
        self.db.add(invitation)
        self.db.commit()
        self.db.refresh(invitation)
        
        logger.info(f"Investor invitation created: {invitee_email} for account {account.name}")
        return invitation
    
    def accept_invitation(
        self,
        invitation_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> AccountAccess:
        """
        Accept an investor invitation and grant account access.
        
        Args:
            invitation_id: Invitation to accept
            user_id: User accepting the invitation
            
        Returns:
            Created account access
            
        Raises:
            InvitationError: If invitation is invalid or expired
        """
        # Find invitation
        invitation = self.db.query(InvestorInvitation).filter(
            InvestorInvitation.id == invitation_id
        ).first()
        
        if not invitation:
            raise InvitationError("Invitation not found")
        
        # Verify invitation status
        if invitation.status != InvitationStatus.PENDING:
            raise InvitationError(f"Invitation is {invitation.status.value}")
        
        # Check expiration
        if datetime.utcnow() > invitation.expires_at:
            invitation.status = InvitationStatus.EXPIRED
            self.db.commit()
            raise InvitationError("Invitation has expired")
        
        # Verify user email matches invitation
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise InvitationError("User not found")
        
        if user.email.lower() != invitation.invitee_email.lower():
            raise InvitationError("Email does not match invitation")
        
        # Check if user already has access
        existing_access = self.db.query(AccountAccess).filter(
            AccountAccess.account_id == invitation.account_id,
            AccountAccess.user_id == user_id
        ).first()
        
        if existing_access:
            # Update invitation status but don't create duplicate access
            invitation.status = InvitationStatus.ACCEPTED
            invitation.accepted_at = datetime.utcnow()
            self.db.commit()
            return existing_access
        
        # Grant investor access
        access = AccountAccess(
            account_id=invitation.account_id,
            user_id=user_id,
            role='investor'
        )
        
        self.db.add(access)
        
        # Update invitation status
        invitation.status = InvitationStatus.ACCEPTED
        invitation.accepted_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(access)
        
        logger.info(f"Invitation accepted: {user.email} for account {invitation.account_id}")
        return access
    
    def revoke_investor_access(
        self,
        account_id: uuid.UUID,
        investor_id: uuid.UUID,
        revoker_id: uuid.UUID
    ) -> bool:
        """
        Revoke an investor's access to an account.
        
        Args:
            account_id: Account to revoke access from
            investor_id: Investor to revoke access for
            revoker_id: User revoking the access
            
        Returns:
            True if access was revoked
            
        Raises:
            UnauthorizedAccessError: If revoker doesn't have trader access
            UserManagementError: If trying to revoke trader access
        """
        # Verify revoker has trader access
        revoker_access = self.db.query(AccountAccess).filter(
            AccountAccess.account_id == account_id,
            AccountAccess.user_id == revoker_id,
            AccountAccess.role == 'trader'
        ).first()
        
        if not revoker_access:
            raise UnauthorizedAccessError("Only account traders can revoke access")
        
        # Find investor access
        investor_access = self.db.query(AccountAccess).filter(
            AccountAccess.account_id == account_id,
            AccountAccess.user_id == investor_id
        ).first()
        
        if not investor_access:
            return False
        
        # Prevent revoking trader access
        if investor_access.role == 'trader':
            raise UserManagementError("Cannot revoke trader access")
        
        # Revoke access
        self.db.delete(investor_access)
        self.db.commit()
        
        logger.info(f"Investor access revoked: user {investor_id} from account {account_id}")
        return True
    
    def get_account_users(self, account_id: uuid.UUID) -> List[dict]:
        """
        Get all users with access to an account.
        
        Args:
            account_id: Account to get users for
            
        Returns:
            List of user dictionaries with access info
        """
        accesses = self.db.query(AccountAccess).filter(
            AccountAccess.account_id == account_id
        ).all()
        
        users = []
        for access in accesses:
            user = access.user
            users.append({
                'user_id': str(user.id),
                'email': user.email,
                'role': access.role,
                'granted_at': access.granted_at.isoformat()
            })
        
        return users
    
    def get_investor_accounts(self, investor_id: uuid.UUID) -> List[UserAccount]:
        """
        Get all accounts an investor has access to.
        
        Args:
            investor_id: Investor user ID
            
        Returns:
            List of user accounts
        """
        accesses = self.db.query(AccountAccess).filter(
            AccountAccess.user_id == investor_id
        ).all()
        
        accounts = [access.account for access in accesses if access.account.is_active]
        return accounts
    
    def update_user_role(
        self,
        user_id: uuid.UUID,
        new_role: UserRole,
        admin_id: uuid.UUID
    ) -> User:
        """
        Update a user's role (admin only).
        
        Args:
            user_id: User to update
            new_role: New role to assign
            admin_id: Admin performing the update
            
        Returns:
            Updated user
            
        Raises:
            UnauthorizedAccessError: If admin_id is not an admin
            UserManagementError: If user not found
        """
        # Verify admin
        admin = self.db.query(User).filter(User.id == admin_id).first()
        if not admin or admin.role != UserRole.ADMIN:
            raise UnauthorizedAccessError("Only admins can update user roles")
        
        # Find user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise UserManagementError("User not found")
        
        old_role = user.role
        user.role = new_role
        self.db.commit()
        self.db.refresh(user)
        
        logger.info(f"User role updated: {user.email} from {old_role.value} to {new_role.value}")
        return user
    
    def disable_user(
        self,
        user_id: uuid.UUID,
        admin_id: uuid.UUID
    ) -> bool:
        """
        Disable a user account (admin only).
        Sets is_locked to True.
        
        Args:
            user_id: User to disable
            admin_id: Admin performing the action
            
        Returns:
            True if user was disabled
            
        Raises:
            UnauthorizedAccessError: If admin_id is not an admin
        """
        # Verify admin
        admin = self.db.query(User).filter(User.id == admin_id).first()
        if not admin or admin.role != UserRole.ADMIN:
            raise UnauthorizedAccessError("Only admins can disable users")
        
        # Find user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.is_locked = True
        user.locked_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"User disabled: {user.email}")
        return True
    
    def enable_user(
        self,
        user_id: uuid.UUID,
        admin_id: uuid.UUID
    ) -> bool:
        """
        Enable a user account (admin only).
        Sets is_locked to False.
        
        Args:
            user_id: User to enable
            admin_id: Admin performing the action
            
        Returns:
            True if user was enabled
            
        Raises:
            UnauthorizedAccessError: If admin_id is not an admin
        """
        # Verify admin
        admin = self.db.query(User).filter(User.id == admin_id).first()
        if not admin or admin.role != UserRole.ADMIN:
            raise UnauthorizedAccessError("Only admins can enable users")
        
        # Find user
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.is_locked = False
        user.locked_at = None
        user.failed_login_attempts = 0
        self.db.commit()
        
        logger.info(f"User enabled: {user.email}")
        return True
