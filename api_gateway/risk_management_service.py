"""
Risk Management Service

Handles maximum loss limit tracking and strategy limit enforcement.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func

from shared.models.risk_management import RiskLimits, StrategyLimits
from shared.models.risk_data import RiskLimitsData, LossCalculation
from shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class RiskManagementService:
    """Service for managing risk limits and loss tracking."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def set_max_loss_limit(
        self,
        account_id: UUID,
        trading_mode: str,
        max_loss_limit: Decimal
    ) -> RiskLimitsData:
        """
        Set or update maximum loss limit for an account and trading mode.
        
        Args:
            account_id: Account UUID
            trading_mode: 'paper' or 'live'
            max_loss_limit: Maximum loss limit in rupees
            
        Returns:
            RiskLimitsData with updated limits
        """
        logger.info(f"Setting max loss limit for account {account_id} ({trading_mode}): {max_loss_limit}")
        
        # Check if risk limits already exist
        risk_limits = self.db.query(RiskLimits).filter(
            RiskLimits.account_id == account_id,
            RiskLimits.trading_mode == trading_mode
        ).first()
        
        if risk_limits:
            # Update existing limits
            risk_limits.max_loss_limit = max_loss_limit
            risk_limits.updated_at = datetime.utcnow()
            
            # If limit is increased and was breached, reset breach status
            if risk_limits.is_breached and max_loss_limit > risk_limits.current_loss:
                risk_limits.is_breached = False
                risk_limits.breached_at = None
                risk_limits.acknowledged = False
                logger.info(f"Breach status reset for account {account_id} ({trading_mode})")
        else:
            # Create new risk limits
            risk_limits = RiskLimits(
                account_id=account_id,
                trading_mode=trading_mode,
                max_loss_limit=max_loss_limit,
                current_loss=Decimal('0.00'),
                is_breached=False,
                acknowledged=False
            )
            self.db.add(risk_limits)
        
        self.db.commit()
        self.db.refresh(risk_limits)
        
        return self._to_risk_limits_data(risk_limits)
    
    def calculate_current_loss(
        self,
        account_id: UUID,
        trading_mode: str
    ) -> LossCalculation:
        """
        Calculate current total loss (realized + unrealized) for an account.
        
        Queries the positions table to calculate:
        - Realized loss: Sum of negative realized P&L from all positions
        - Unrealized loss: Sum of negative unrealized P&L from open positions
        
        Args:
            account_id: Account UUID
            trading_mode: 'paper' or 'live'
            
        Returns:
            LossCalculation with realized, unrealized, and total losses
        """
        from shared.models.position import Position
        
        logger.debug(f"Calculating current loss for account {account_id} ({trading_mode})")
        
        # Query all positions for this account and trading mode
        positions = self.db.query(Position).filter(
            Position.account_id == account_id,
            Position.trading_mode == trading_mode
        ).all()
        
        realized_loss = Decimal('0.00')
        unrealized_loss = Decimal('0.00')
        
        for position in positions:
            # Sum up negative realized P&L (losses only)
            if position.realized_pnl < 0:
                realized_loss += abs(Decimal(str(position.realized_pnl)))
            
            # Sum up negative unrealized P&L from open positions (losses only)
            if position.closed_at is None and position.unrealized_pnl < 0:
                unrealized_loss += abs(Decimal(str(position.unrealized_pnl)))
        
        total_loss = realized_loss + unrealized_loss
        
        logger.debug(
            f"Loss calculation for account {account_id} ({trading_mode}): "
            f"Realized: {realized_loss}, Unrealized: {unrealized_loss}, Total: {total_loss}"
        )
        
        return LossCalculation(
            realized_loss=realized_loss,
            unrealized_loss=unrealized_loss,
            total_loss=total_loss,
            timestamp=datetime.utcnow()
        )
    
    def check_loss_limit(
        self,
        account_id: UUID,
        trading_mode: str,
        current_loss: Optional[Decimal] = None
    ) -> bool:
        """
        Check if loss limit has been breached.
        
        Args:
            account_id: Account UUID
            trading_mode: 'paper' or 'live'
            current_loss: Optional current loss value. If not provided, will be calculated.
            
        Returns:
            True if limit is breached, False otherwise
        """
        logger.debug(f"Checking loss limit for account {account_id} ({trading_mode})")
        
        # Get risk limits
        risk_limits = self.db.query(RiskLimits).filter(
            RiskLimits.account_id == account_id,
            RiskLimits.trading_mode == trading_mode
        ).first()
        
        if not risk_limits:
            logger.warning(f"No risk limits found for account {account_id} ({trading_mode})")
            return False
        
        # Calculate current loss if not provided
        if current_loss is None:
            loss_calc = self.calculate_current_loss(account_id, trading_mode)
            current_loss = loss_calc.total_loss
        
        # Update current loss in database
        risk_limits.current_loss = current_loss
        
        # Check if limit is breached
        is_breached = current_loss >= risk_limits.max_loss_limit
        
        if is_breached and not risk_limits.is_breached:
            # First time breach
            risk_limits.is_breached = True
            risk_limits.breached_at = datetime.utcnow()
            risk_limits.acknowledged = False
            logger.warning(
                f"Loss limit BREACHED for account {account_id} ({trading_mode}): "
                f"Current loss {current_loss} >= Limit {risk_limits.max_loss_limit}"
            )
            
            # TODO: Trigger pauseAllStrategies when strategy execution is implemented
            # self.pause_all_strategies(account_id, trading_mode, "Loss limit breached")
        
        self.db.commit()
        
        return is_breached
    
    def pause_all_strategies(
        self,
        account_id: UUID,
        trading_mode: str,
        reason: str
    ) -> int:
        """
        Pause all active strategies for an account.
        
        This is a placeholder for when strategy execution is implemented.
        TODO: Implement actual strategy pausing when strategy execution is available.
        
        Args:
            account_id: Account UUID
            trading_mode: 'paper' or 'live'
            reason: Reason for pausing strategies
            
        Returns:
            Number of strategies paused
        """
        logger.warning(
            f"Pausing all strategies for account {account_id} ({trading_mode}): {reason}"
        )
        
        # TODO: Implement when active_strategies table and strategy execution are available
        # Query active strategies and set their status to 'paused'
        # Send notifications to user
        
        return 0  # Placeholder
    
    def acknowledge_limit_breach(
        self,
        account_id: UUID,
        trading_mode: str,
        new_limit: Optional[Decimal] = None
    ) -> RiskLimitsData:
        """
        Acknowledge a loss limit breach and optionally update the limit.
        
        Args:
            account_id: Account UUID
            trading_mode: 'paper' or 'live'
            new_limit: Optional new loss limit. If provided, limit will be updated.
            
        Returns:
            RiskLimitsData with updated status
        """
        logger.info(
            f"Acknowledging limit breach for account {account_id} ({trading_mode})"
        )
        
        risk_limits = self.db.query(RiskLimits).filter(
            RiskLimits.account_id == account_id,
            RiskLimits.trading_mode == trading_mode
        ).first()
        
        if not risk_limits:
            raise ValueError(f"No risk limits found for account {account_id} ({trading_mode})")
        
        if not risk_limits.is_breached:
            raise ValueError(f"No breach to acknowledge for account {account_id} ({trading_mode})")
        
        # Mark as acknowledged
        risk_limits.acknowledged = True
        risk_limits.updated_at = datetime.utcnow()
        
        # Update limit if provided
        if new_limit is not None:
            risk_limits.max_loss_limit = new_limit
            
            # If new limit is higher than current loss, reset breach status
            if new_limit > risk_limits.current_loss:
                risk_limits.is_breached = False
                risk_limits.breached_at = None
                risk_limits.acknowledged = False
                logger.info(f"Breach status reset with new limit: {new_limit}")
        
        self.db.commit()
        self.db.refresh(risk_limits)
        
        return self._to_risk_limits_data(risk_limits)
    
    def get_risk_limits(
        self,
        account_id: UUID,
        trading_mode: str
    ) -> Optional[RiskLimitsData]:
        """
        Get risk limits for an account and trading mode.
        
        Args:
            account_id: Account UUID
            trading_mode: 'paper' or 'live'
            
        Returns:
            RiskLimitsData or None if not found
        """
        risk_limits = self.db.query(RiskLimits).filter(
            RiskLimits.account_id == account_id,
            RiskLimits.trading_mode == trading_mode
        ).first()
        
        if not risk_limits:
            return None
        
        return self._to_risk_limits_data(risk_limits)
    
    def _to_risk_limits_data(self, risk_limits: RiskLimits) -> RiskLimitsData:
        """Convert RiskLimits model to RiskLimitsData."""
        return RiskLimitsData(
            account_id=str(risk_limits.account_id),
            trading_mode=risk_limits.trading_mode,
            max_loss_limit=risk_limits.max_loss_limit,
            current_loss=risk_limits.current_loss,
            is_breached=risk_limits.is_breached,
            breached_at=risk_limits.breached_at,
            acknowledged=risk_limits.acknowledged,
            updated_at=risk_limits.updated_at
        )


    # Concurrent Strategy Limit Management
    
    def set_global_strategy_limit(
        self,
        trading_mode: str,
        max_concurrent_strategies: int,
        updated_by: UUID
    ) -> Dict:
        """
        Set global concurrent strategy limit (admin only).
        
        Args:
            trading_mode: 'paper' or 'live'
            max_concurrent_strategies: Maximum number of concurrent strategies
            updated_by: UUID of admin user setting the limit
            
        Returns:
            Dictionary with updated strategy limits
        """
        logger.info(
            f"Setting global strategy limit for {trading_mode}: {max_concurrent_strategies} "
            f"(by user {updated_by})"
        )
        
        # Get or create strategy limits
        strategy_limits = self.db.query(StrategyLimits).filter(
            StrategyLimits.trading_mode == trading_mode
        ).first()
        
        if strategy_limits:
            # Update existing limits
            strategy_limits.max_concurrent_strategies = max_concurrent_strategies
            strategy_limits.last_updated = datetime.utcnow()
            strategy_limits.updated_by = updated_by
        else:
            # Create new limits (shouldn't happen as defaults are inserted in migration)
            strategy_limits = StrategyLimits(
                trading_mode=trading_mode,
                max_concurrent_strategies=max_concurrent_strategies,
                updated_by=updated_by
            )
            self.db.add(strategy_limits)
        
        self.db.commit()
        self.db.refresh(strategy_limits)
        
        return {
            'trading_mode': strategy_limits.trading_mode,
            'max_concurrent_strategies': strategy_limits.max_concurrent_strategies,
            'last_updated': strategy_limits.last_updated.isoformat(),
            'updated_by': str(strategy_limits.updated_by) if strategy_limits.updated_by else None
        }
    
    def get_strategy_limit(self, trading_mode: str) -> Optional[Dict]:
        """
        Get global strategy limit for a trading mode.
        
        Args:
            trading_mode: 'paper' or 'live'
            
        Returns:
            Dictionary with strategy limits or None if not found
        """
        strategy_limits = self.db.query(StrategyLimits).filter(
            StrategyLimits.trading_mode == trading_mode
        ).first()
        
        if not strategy_limits:
            return None
        
        return {
            'trading_mode': strategy_limits.trading_mode,
            'max_concurrent_strategies': strategy_limits.max_concurrent_strategies,
            'last_updated': strategy_limits.last_updated.isoformat(),
            'updated_by': str(strategy_limits.updated_by) if strategy_limits.updated_by else None
        }
    
    def get_active_strategy_count(
        self,
        account_id: UUID,
        trading_mode: str
    ) -> int:
        """
        Get count of active strategies for an account.
        
        This is a placeholder for when strategy execution is implemented.
        TODO: Implement actual strategy counting when active_strategies table is available.
        
        Args:
            account_id: Account UUID
            trading_mode: 'paper' or 'live'
            
        Returns:
            Number of active strategies
        """
        logger.debug(f"Getting active strategy count for account {account_id} ({trading_mode})")
        
        # TODO: Query active_strategies table when it's implemented
        # SELECT COUNT(*) FROM active_strategies 
        # WHERE account_id = ? AND trading_mode = ? AND status = 'running'
        
        return 0  # Placeholder
    
    def can_activate_strategy(
        self,
        account_id: UUID,
        trading_mode: str
    ) -> tuple[bool, Optional[str]]:
        """
        Check if a strategy can be activated based on concurrent strategy limits.
        
        Args:
            account_id: Account UUID
            trading_mode: 'paper' or 'live'
            
        Returns:
            Tuple of (can_activate: bool, error_message: Optional[str])
        """
        logger.debug(f"Checking if strategy can be activated for account {account_id} ({trading_mode})")
        
        # Get global limit
        strategy_limits = self.db.query(StrategyLimits).filter(
            StrategyLimits.trading_mode == trading_mode
        ).first()
        
        if not strategy_limits:
            logger.warning(f"No strategy limits found for {trading_mode}")
            return True, None  # Allow if no limits configured
        
        # Get current active count
        active_count = self.get_active_strategy_count(account_id, trading_mode)
        
        # Check if limit would be exceeded
        if active_count >= strategy_limits.max_concurrent_strategies:
            error_msg = (
                f"Cannot activate strategy: concurrent strategy limit reached "
                f"({active_count}/{strategy_limits.max_concurrent_strategies})"
            )
            logger.warning(f"Strategy activation blocked for account {account_id}: {error_msg}")
            return False, error_msg
        
        return True, None
    
    def enforce_limit(
        self,
        account_id: UUID,
        trading_mode: str
    ) -> bool:
        """
        Enforce concurrent strategy limit before activation.
        
        Args:
            account_id: Account UUID
            trading_mode: 'paper' or 'live'
            
        Returns:
            True if activation is allowed, False otherwise
            
        Raises:
            ValueError: If limit is reached
        """
        can_activate, error_msg = self.can_activate_strategy(account_id, trading_mode)
        
        if not can_activate:
            raise ValueError(error_msg)
        
        return True
