"""Backtest data models for backtesting engine."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from sqlalchemy import Column, String, DateTime, JSON, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID
import uuid
from shared.database.connection import Base


class BacktestStatus(str, Enum):
    """Backtest status enumeration."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Backtest(Base):
    """SQLAlchemy model for backtests table."""
    __tablename__ = "backtests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(UUID(as_uuid=True), nullable=False)
    account_id = Column(UUID(as_uuid=True), nullable=False)
    config = Column(JSON, nullable=False)
    metrics = Column(JSON, nullable=True)
    status = Column(SQLEnum(BacktestStatus), nullable=False, default=BacktestStatus.RUNNING)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index('idx_backtests_strategy', 'strategy_id', 'created_at'),
        Index('idx_backtests_account', 'account_id', 'created_at'),
        Index('idx_backtests_status', 'status'),
    )


@dataclass
class BacktestConfig:
    """Configuration for backtest execution."""
    strategy_id: str
    account_id: str
    symbols: List[str]
    timeframes: List[str]
    start_date: datetime
    end_date: datetime
    initial_capital: float
    slippage: float = 0.0005  # 0.05% default
    commission: float = 0.0003  # 0.03% default
    strategy_params: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Validate backtest configuration."""
        if not self.symbols:
            raise ValueError("At least one symbol is required")
        if not self.timeframes:
            raise ValueError("At least one timeframe is required")
        if self.start_date >= self.end_date:
            raise ValueError("Start date must be before end date")
        if self.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")
        if self.slippage < 0 or self.slippage > 0.1:
            raise ValueError("Slippage must be between 0 and 0.1 (10%)")
        if self.commission < 0 or self.commission > 0.1:
            raise ValueError("Commission must be between 0 and 0.1 (10%)")


@dataclass
class BacktestTrade:
    """Trade executed during backtest."""
    entry_date: datetime
    exit_date: datetime
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    exit_price: float
    quantity: int
    pnl: float
    pnl_percent: float
    commission: float
    holding_time_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'entry_date': self.entry_date.isoformat(),
            'exit_date': self.exit_date.isoformat(),
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'quantity': self.quantity,
            'pnl': self.pnl,
            'pnl_percent': self.pnl_percent,
            'commission': self.commission,
            'holding_time_seconds': self.holding_time_seconds
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BacktestTrade':
        """Create from dictionary."""
        return cls(
            entry_date=datetime.fromisoformat(data['entry_date']),
            exit_date=datetime.fromisoformat(data['exit_date']),
            symbol=data['symbol'],
            side=data['side'],
            entry_price=data['entry_price'],
            exit_price=data['exit_price'],
            quantity=data['quantity'],
            pnl=data['pnl'],
            pnl_percent=data['pnl_percent'],
            commission=data['commission'],
            holding_time_seconds=data['holding_time_seconds']
        )


@dataclass
class EquityPoint:
    """Point in equity curve."""
    timestamp: datetime
    equity: float
    drawdown: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'equity': self.equity,
            'drawdown': self.drawdown
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EquityPoint':
        """Create from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            equity=data['equity'],
            drawdown=data['drawdown']
        )


@dataclass
class PerformanceMetrics:
    """Performance metrics for backtest results."""
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    win_rate: float
    profit_factor: float
    average_win: float
    average_loss: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    max_consecutive_wins: int
    max_consecutive_losses: int
    average_holding_time_seconds: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'total_return': self.total_return,
            'annualized_return': self.annualized_return,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'average_win': self.average_win,
            'average_loss': self.average_loss,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'max_consecutive_wins': self.max_consecutive_wins,
            'max_consecutive_losses': self.max_consecutive_losses,
            'average_holding_time_seconds': self.average_holding_time_seconds
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PerformanceMetrics':
        """Create from dictionary."""
        return cls(
            total_return=data['total_return'],
            annualized_return=data['annualized_return'],
            max_drawdown=data['max_drawdown'],
            sharpe_ratio=data['sharpe_ratio'],
            sortino_ratio=data['sortino_ratio'],
            win_rate=data['win_rate'],
            profit_factor=data['profit_factor'],
            average_win=data['average_win'],
            average_loss=data['average_loss'],
            total_trades=data['total_trades'],
            winning_trades=data['winning_trades'],
            losing_trades=data['losing_trades'],
            max_consecutive_wins=data['max_consecutive_wins'],
            max_consecutive_losses=data['max_consecutive_losses'],
            average_holding_time_seconds=data['average_holding_time_seconds']
        )


@dataclass
class BacktestResult:
    """Complete backtest results."""
    id: str
    config: BacktestConfig
    metrics: PerformanceMetrics
    trades: List[BacktestTrade]
    equity_curve: List[EquityPoint]
    completed_at: datetime
    status: BacktestStatus

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'config': {
                'strategy_id': self.config.strategy_id,
                'account_id': self.config.account_id,
                'symbols': self.config.symbols,
                'timeframes': self.config.timeframes,
                'start_date': self.config.start_date.isoformat(),
                'end_date': self.config.end_date.isoformat(),
                'initial_capital': self.config.initial_capital,
                'slippage': self.config.slippage,
                'commission': self.config.commission,
                'strategy_params': self.config.strategy_params
            },
            'metrics': self.metrics.to_dict(),
            'trades': [trade.to_dict() for trade in self.trades],
            'equity_curve': [point.to_dict() for point in self.equity_curve],
            'completed_at': self.completed_at.isoformat(),
            'status': self.status.value
        }

    @classmethod
    def from_orm(cls, backtest: Backtest) -> 'BacktestResult':
        """Create BacktestResult from SQLAlchemy Backtest model."""
        config_data = backtest.config
        metrics_data = backtest.metrics or {}
        
        config = BacktestConfig(
            strategy_id=config_data['strategy_id'],
            account_id=config_data['account_id'],
            symbols=config_data['symbols'],
            timeframes=config_data['timeframes'],
            start_date=datetime.fromisoformat(config_data['start_date']),
            end_date=datetime.fromisoformat(config_data['end_date']),
            initial_capital=config_data['initial_capital'],
            slippage=config_data.get('slippage', 0.0005),
            commission=config_data.get('commission', 0.0003),
            strategy_params=config_data.get('strategy_params', {})
        )
        
        metrics = PerformanceMetrics.from_dict(metrics_data.get('metrics', {})) if metrics_data.get('metrics') else None
        trades = [BacktestTrade.from_dict(t) for t in metrics_data.get('trades', [])]
        equity_curve = [EquityPoint.from_dict(p) for p in metrics_data.get('equity_curve', [])]
        
        return cls(
            id=str(backtest.id),
            config=config,
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve,
            completed_at=backtest.completed_at,
            status=backtest.status
        )
