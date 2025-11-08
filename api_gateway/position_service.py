"""Position service for business logic."""

from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from shared.models.position import Position, PositionData, TradingMode
from shared.models.user import AccountAccess
from order_processor.position_manager import PositionManager
from order_processor.trailing_stop_manager import TrailingStopManager
from shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class PositionService:
    """Service for position management operations."""
    
    def __init__(self, db_session: Session):
        """
        Initialize position service.
        
        Args:
            db_session: Database session
        """
        self.db = db_session
        self.position_manager = PositionManager(db_session)
        self.trailing_stop_manager = TrailingStopManager(db_session)
    
    def verify_account_access(self, user_id: str, account_id: str) -> bool:
        """
        Verify user has access to account.
        
        Args:
            user_id: User ID
            account_id: Account ID
            
        Returns:
            True if user has access
        """
        access = self.db.query(AccountAccess).filter(
            AccountAccess.user_id == uuid.UUID(user_id),
            AccountAccess.account_id == uuid.UUID(account_id)
        ).first()
        
        return access is not None
    
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
        return self.position_manager.get_positions(account_id, trading_mode, include_closed)
    
    def get_position(self, position_id: str) -> Optional[PositionData]:
        """
        Get single position by ID.
        
        Args:
            position_id: Position ID
            
        Returns:
            Position data or None if not found
        """
        return self.position_manager.get_position(position_id)
    
    def close_position(
        self,
        position_id: str,
        closing_price: float,
        commission: float = 0.0
    ) -> PositionData:
        """
        Close a position.
        
        Args:
            position_id: Position ID
            closing_price: Closing price
            commission: Commission for closing trade
            
        Returns:
            Closed position data
        """
        return self.position_manager.close_position(position_id, closing_price, commission)
    
    def configure_trailing_stop(
        self,
        position_id: str,
        percentage: float,
        current_price: float
    ) -> PositionData:
        """
        Configure trailing stop-loss for a position.
        
        Args:
            position_id: Position ID
            percentage: Trailing stop percentage
            current_price: Current market price
            
        Returns:
            Updated position data
        """
        return self.trailing_stop_manager.configure_trailing_stop(
            position_id,
            percentage,
            current_price
        )
    
    def calculate_risk_metrics(
        self,
        account_id: str,
        trading_mode: Optional[TradingMode] = None
    ) -> Dict[str, Any]:
        """
        Calculate real-time risk metrics for an account.
        
        Args:
            account_id: Account ID
            trading_mode: Optional trading mode filter
            
        Returns:
            Dictionary of risk metrics
        """
        # Get open positions
        if trading_mode:
            positions = self.position_manager.get_positions(account_id, trading_mode, False)
        else:
            paper_positions = self.position_manager.get_positions(account_id, TradingMode.PAPER, False)
            live_positions = self.position_manager.get_positions(account_id, TradingMode.LIVE, False)
            positions = paper_positions + live_positions
        
        # Calculate metrics
        total_exposure = 0.0
        total_unrealized_pnl = 0.0
        total_realized_pnl = 0.0
        long_exposure = 0.0
        short_exposure = 0.0
        position_count = len(positions)
        
        for pos in positions:
            position_value = pos.current_price * pos.quantity
            total_exposure += position_value
            total_unrealized_pnl += pos.unrealized_pnl
            total_realized_pnl += pos.realized_pnl
            
            if pos.side.value == 'long':
                long_exposure += position_value
            else:
                short_exposure += position_value
        
        # Calculate margin utilization (simplified - would need account balance)
        # For now, just return exposure
        margin_utilization = total_exposure
        
        return {
            'total_exposure': round(total_exposure, 2),
            'long_exposure': round(long_exposure, 2),
            'short_exposure': round(short_exposure, 2),
            'margin_utilization': round(margin_utilization, 2),
            'total_unrealized_pnl': round(total_unrealized_pnl, 2),
            'total_realized_pnl': round(total_realized_pnl, 2),
            'total_pnl': round(total_unrealized_pnl + total_realized_pnl, 2),
            'position_count': position_count,
            'trading_mode': trading_mode.value if trading_mode else 'all'
        }
    
    def get_position_history(
        self,
        account_id: str,
        filters: Dict[str, Any]
    ) -> List[PositionData]:
        """
        Get position history with filters.
        
        Args:
            account_id: Account ID
            filters: Dictionary of filters
            
        Returns:
            List of position data
        """
        query = self.db.query(Position).filter(
            Position.account_id == uuid.UUID(account_id),
            Position.closed_at.isnot(None)  # Only closed positions
        )
        
        # Apply filters
        if filters.get('trading_mode'):
            try:
                trading_mode = TradingMode(filters['trading_mode'])
                query = query.filter(Position.trading_mode == trading_mode)
            except ValueError:
                pass
        
        if filters.get('symbol'):
            query = query.filter(Position.symbol == filters['symbol'])
        
        if filters.get('start_date'):
            try:
                start_date = datetime.fromisoformat(filters['start_date'])
                query = query.filter(Position.closed_at >= start_date)
            except ValueError:
                pass
        
        if filters.get('end_date'):
            try:
                end_date = datetime.fromisoformat(filters['end_date'])
                query = query.filter(Position.closed_at <= end_date)
            except ValueError:
                pass
        
        # Apply limit
        limit = filters.get('limit', 100)
        positions = query.order_by(Position.closed_at.desc()).limit(limit).all()
        
        return [PositionData.from_orm(p) for p in positions]
