"""Position manager for tracking positions and calculating P&L."""

from typing import Optional, List, Dict, TYPE_CHECKING
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from shared.models.position import Position, PositionData, PositionSide, TrailingStopConfig
from shared.models.trade import TradeData
from shared.models.order import TradingMode, OrderSide
from shared.utils.logging_config import get_logger

if TYPE_CHECKING:
    from api_gateway.risk_management_service import RiskManagementService

logger = get_logger(__name__)


class PositionManager:
    """Manages position tracking and P&L calculations."""
    
    def __init__(self, db_session: Session, risk_service: Optional['RiskManagementService'] = None):
        """
        Initialize position manager.
        
        Args:
            db_session: Database session for persistence
            risk_service: Optional risk management service for loss limit checks
        """
        self.db = db_session
        self.risk_service = risk_service
        logger.info("Position manager initialized")
    
    def open_position(
        self,
        trade: TradeData,
        strategy_id: Optional[str] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        trailing_stop_percentage: Optional[float] = None
    ) -> PositionData:
        """
        Create new position from trade execution.
        
        Args:
            trade: Trade that opens the position
            strategy_id: Optional strategy ID
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            trailing_stop_percentage: Optional trailing stop percentage
            
        Returns:
            Created position data
        """
        # Determine position side from trade side
        position_side = PositionSide.LONG if trade.side == OrderSide.BUY else PositionSide.SHORT
        
        # Initialize trailing stop config if percentage provided
        trailing_stop_config = None
        if trailing_stop_percentage:
            trailing_stop_config = {
                'enabled': True,
                'percentage': trailing_stop_percentage,
                'current_stop_price': self._calculate_initial_trailing_stop(
                    trade.price, position_side, trailing_stop_percentage
                ),
                'highest_price': trade.price if position_side == PositionSide.LONG else 0,
                'lowest_price': trade.price if position_side == PositionSide.SHORT else float('inf')
            }
        
        # Create position
        position = Position(
            id=uuid.uuid4(),
            account_id=uuid.UUID(trade.account_id),
            strategy_id=uuid.UUID(strategy_id) if strategy_id else None,
            symbol=trade.symbol,
            side=position_side,
            quantity=trade.quantity,
            entry_price=trade.price,
            current_price=trade.price,
            unrealized_pnl=0.0,
            realized_pnl=-trade.commission,  # Commission is realized loss
            trading_mode=trade.trading_mode,
            stop_loss=stop_loss,
            take_profit=take_profit,
            trailing_stop_config=trailing_stop_config,
            opened_at=trade.executed_at
        )
        
        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)
        
        position_data = PositionData.from_orm(position)
        
        logger.info(
            f"Opened position: {position_data.symbol} {position_data.side.value} "
            f"{position_data.quantity} @ {position_data.entry_price} "
            f"(mode: {position_data.trading_mode.value})"
        )
        
        return position_data
    
    def update_position(
        self,
        position_id: str,
        trade: TradeData
    ) -> PositionData:
        """
        Update position with new trade (add to or reduce position).
        
        Args:
            position_id: Position ID to update
            trade: Trade to apply to position
            
        Returns:
            Updated position data
        """
        position = self.db.query(Position).filter(Position.id == uuid.UUID(position_id)).first()
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        # Determine if trade adds to or reduces position
        is_adding = (
            (position.side == PositionSide.LONG and trade.side == OrderSide.BUY) or
            (position.side == PositionSide.SHORT and trade.side == OrderSide.SELL)
        )
        
        if is_adding:
            # Add to position - update average entry price
            total_cost = (position.entry_price * position.quantity) + (trade.price * trade.quantity)
            new_quantity = position.quantity + trade.quantity
            position.entry_price = total_cost / new_quantity
            position.quantity = new_quantity
            position.realized_pnl -= trade.commission
            
            logger.info(
                f"Added to position {position_id}: +{trade.quantity} @ {trade.price} "
                f"(new avg: {position.entry_price:.2f})"
            )
        else:
            # Reduce position - calculate realized P&L
            if trade.quantity > position.quantity:
                raise ValueError(
                    f"Trade quantity {trade.quantity} exceeds position quantity {position.quantity}"
                )
            
            # Calculate realized P&L for closed portion
            if position.side == PositionSide.LONG:
                realized_pnl = (trade.price - position.entry_price) * trade.quantity
            else:  # SHORT
                realized_pnl = (position.entry_price - trade.price) * trade.quantity
            
            position.realized_pnl += realized_pnl - trade.commission
            position.quantity -= trade.quantity
            
            logger.info(
                f"Reduced position {position_id}: -{trade.quantity} @ {trade.price} "
                f"(realized P&L: {realized_pnl:.2f})"
            )
            
            # Close position if quantity reaches zero
            if position.quantity == 0:
                position.closed_at = trade.executed_at
                position.unrealized_pnl = 0.0
                logger.info(f"Closed position {position_id} (total realized P&L: {position.realized_pnl:.2f})")
        
        position.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(position)
        
        # Trigger loss limit check
        self._check_loss_limits(position.account_id, position.trading_mode)
        
        return PositionData.from_orm(position)
    
    def calculate_pnl(
        self,
        position_id: str,
        current_price: float
    ) -> tuple[float, float]:
        """
        Calculate unrealized and total P&L for position.
        
        Args:
            position_id: Position ID
            current_price: Current market price
            
        Returns:
            Tuple of (unrealized_pnl, total_pnl)
        """
        position = self.db.query(Position).filter(Position.id == uuid.UUID(position_id)).first()
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        # Calculate unrealized P&L
        if position.side == PositionSide.LONG:
            unrealized_pnl = (current_price - position.entry_price) * position.quantity
        else:  # SHORT
            unrealized_pnl = (position.entry_price - current_price) * position.quantity
        
        # Update position
        position.current_price = current_price
        position.unrealized_pnl = unrealized_pnl
        
        self.db.commit()
        
        total_pnl = position.realized_pnl + unrealized_pnl
        
        # Trigger loss limit check if risk service is available
        self._check_loss_limits(position.account_id, position.trading_mode)
        
        return unrealized_pnl, total_pnl
    
    def close_position(
        self,
        position_id: str,
        closing_price: float,
        commission: float = 0.0
    ) -> PositionData:
        """
        Close position completely.
        
        Args:
            position_id: Position ID to close
            closing_price: Price at which position is closed
            commission: Commission for closing trade
            
        Returns:
            Closed position data
        """
        position = self.db.query(Position).filter(Position.id == uuid.UUID(position_id)).first()
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        if position.closed_at:
            raise ValueError(f"Position {position_id} is already closed")
        
        # Calculate final realized P&L
        if position.side == PositionSide.LONG:
            final_pnl = (closing_price - position.entry_price) * position.quantity
        else:  # SHORT
            final_pnl = (position.entry_price - closing_price) * position.quantity
        
        position.realized_pnl += final_pnl - commission
        position.unrealized_pnl = 0.0
        position.current_price = closing_price
        position.closed_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(position)
        
        position_data = PositionData.from_orm(position)
        
        # Trigger loss limit check
        self._check_loss_limits(position.account_id, position.trading_mode)
        
        logger.info(
            f"Closed position {position_id}: {position_data.symbol} "
            f"(final P&L: {position_data.realized_pnl:.2f})"
        )
        
        return position_data
    
    def get_positions(
        self,
        account_id: str,
        trading_mode: TradingMode,
        include_closed: bool = False
    ) -> List[PositionData]:
        """
        Get all positions for an account.
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode filter
            include_closed: Whether to include closed positions
            
        Returns:
            List of position data
        """
        query = self.db.query(Position).filter(
            Position.account_id == uuid.UUID(account_id),
            Position.trading_mode == trading_mode
        )
        
        if not include_closed:
            query = query.filter(Position.closed_at.is_(None))
        
        positions = query.order_by(Position.opened_at.desc()).all()
        
        return [PositionData.from_orm(p) for p in positions]
    
    def get_position(self, position_id: str) -> Optional[PositionData]:
        """
        Get single position by ID.
        
        Args:
            position_id: Position ID
            
        Returns:
            Position data or None if not found
        """
        position = self.db.query(Position).filter(Position.id == uuid.UUID(position_id)).first()
        if not position:
            return None
        
        return PositionData.from_orm(position)
    
    def update_all_positions_price(
        self,
        symbol: str,
        current_price: float,
        trading_mode: TradingMode
    ) -> List[PositionData]:
        """
        Update current price and P&L for all open positions of a symbol.
        
        Args:
            symbol: Symbol to update
            current_price: Current market price
            trading_mode: Trading mode filter
            
        Returns:
            List of updated position data
        """
        positions = self.db.query(Position).filter(
            Position.symbol == symbol,
            Position.trading_mode == trading_mode,
            Position.closed_at.is_(None)
        ).all()
        
        updated_positions = []
        accounts_to_check = set()
        
        for position in positions:
            # Calculate unrealized P&L
            if position.side == PositionSide.LONG:
                unrealized_pnl = (current_price - float(position.entry_price)) * position.quantity
            else:  # SHORT
                unrealized_pnl = (float(position.entry_price) - current_price) * position.quantity
            
            position.current_price = current_price
            position.unrealized_pnl = unrealized_pnl
            
            updated_positions.append(PositionData.from_orm(position))
            accounts_to_check.add((position.account_id, position.trading_mode))
        
        self.db.commit()
        
        # Trigger loss limit checks for all affected accounts
        for account_id, mode in accounts_to_check:
            self._check_loss_limits(account_id, mode)
        
        return updated_positions
    
    def _calculate_initial_trailing_stop(
        self,
        entry_price: float,
        side: PositionSide,
        percentage: float
    ) -> float:
        """Calculate initial trailing stop price."""
        if side == PositionSide.LONG:
            return entry_price * (1 - percentage)
        else:  # SHORT
            return entry_price * (1 + percentage)
    
    def _check_loss_limits(self, account_id: uuid.UUID, trading_mode: TradingMode) -> None:
        """
        Trigger loss limit check for an account.
        
        Args:
            account_id: Account UUID
            trading_mode: Trading mode
        """
        if self.risk_service:
            try:
                self.risk_service.check_loss_limit(account_id, trading_mode.value)
            except Exception as e:
                logger.error(f"Error checking loss limits for account {account_id}: {e}")
