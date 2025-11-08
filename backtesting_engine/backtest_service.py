"""
Backtest Service

Manages backtest execution and result storage.
"""
import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

from shared.models.backtest import (
    Backtest, BacktestConfig, BacktestResult, BacktestStatus,
    PerformanceMetrics
)
from shared.database.connection import get_db
from backtesting_engine.data_loader import HistoricalDataLoader, MultiTimeframeDataSynchronizer
from backtesting_engine.execution_engine import BacktestExecutionEngine
from backtesting_engine.metrics_calculator import MetricsCalculator
from strategy_workers.strategy_plugin_manager import StrategyPluginManager

logger = logging.getLogger(__name__)


class BacktestService:
    """Service for managing backtests"""
    
    def __init__(self):
        self.strategy_manager = StrategyPluginManager('strategy_workers/strategies')
        self.strategy_manager.discover_plugins()
    
    def start_backtest(self, config: BacktestConfig, db: Session) -> str:
        """
        Start a new backtest.
        
        Args:
            config: Backtest configuration
            db: Database session
            
        Returns:
            Backtest ID
        """
        # Validate configuration
        config.validate()
        
        # Create backtest record
        backtest_id = str(uuid.uuid4())
        backtest = Backtest(
            id=uuid.UUID(backtest_id),
            strategy_id=uuid.UUID(config.strategy_id),
            account_id=uuid.UUID(config.account_id),
            config={
                'strategy_id': config.strategy_id,
                'account_id': config.account_id,
                'symbols': config.symbols,
                'timeframes': config.timeframes,
                'start_date': config.start_date.isoformat(),
                'end_date': config.end_date.isoformat(),
                'initial_capital': config.initial_capital,
                'slippage': config.slippage,
                'commission': config.commission,
                'strategy_params': config.strategy_params
            },
            status=BacktestStatus.RUNNING
        )
        
        db.add(backtest)
        db.commit()
        
        logger.info(f"Started backtest {backtest_id}")
        
        # Execute backtest asynchronously (in production, use Celery task)
        try:
            self._execute_backtest(backtest_id, config, db)
        except Exception as e:
            logger.error(f"Backtest {backtest_id} failed: {e}")
            backtest.status = BacktestStatus.FAILED
            backtest.completed_at = datetime.utcnow()
            db.commit()
            raise
        
        return backtest_id
    
    def _execute_backtest(self, backtest_id: str, config: BacktestConfig, db: Session) -> None:
        """Execute the backtest"""
        logger.info(f"Executing backtest {backtest_id}")
        
        # Load historical data
        data_loader = HistoricalDataLoader()
        try:
            historical_data = data_loader.load_data(config)
        finally:
            data_loader.close()
        
        # Create data synchronizer
        data_sync = MultiTimeframeDataSynchronizer(historical_data)
        
        # Load strategy
        # For now, assume strategy_id maps to a strategy name
        # In production, you'd look up the strategy from database
        strategy_class = self.strategy_manager.get_strategy('Moving Average Crossover')
        if not strategy_class:
            raise ValueError(f"Strategy not found: {config.strategy_id}")
        
        strategy = strategy_class()
        
        # Create execution engine
        engine = BacktestExecutionEngine(config, strategy, data_sync)
        
        # Run backtest
        trades, equity_curve = engine.run()
        
        # Calculate metrics
        metrics = MetricsCalculator.calculate_metrics(
            trades=trades,
            equity_curve=equity_curve,
            initial_capital=config.initial_capital,
            start_date=config.start_date,
            end_date=config.end_date
        )
        
        # Update backtest record
        backtest = db.query(Backtest).filter(Backtest.id == uuid.UUID(backtest_id)).first()
        if backtest:
            backtest.status = BacktestStatus.COMPLETED
            backtest.completed_at = datetime.utcnow()
            backtest.metrics = {
                'metrics': metrics.to_dict(),
                'trades': [t.to_dict() for t in trades],
                'equity_curve': [p.to_dict() for p in equity_curve]
            }
            db.commit()
        
        logger.info(f"Backtest {backtest_id} completed successfully")
    
    def get_backtest_status(self, backtest_id: str, db: Session) -> Optional[Dict]:
        """
        Get backtest status.
        
        Args:
            backtest_id: Backtest ID
            db: Database session
            
        Returns:
            Status information or None if not found
        """
        backtest = db.query(Backtest).filter(Backtest.id == uuid.UUID(backtest_id)).first()
        
        if not backtest:
            return None
        
        return {
            'id': str(backtest.id),
            'status': backtest.status.value,
            'created_at': backtest.created_at.isoformat(),
            'completed_at': backtest.completed_at.isoformat() if backtest.completed_at else None
        }
    
    def get_backtest_results(self, backtest_id: str, db: Session) -> Optional[BacktestResult]:
        """
        Get complete backtest results.
        
        Args:
            backtest_id: Backtest ID
            db: Database session
            
        Returns:
            BacktestResult or None if not found
        """
        backtest = db.query(Backtest).filter(Backtest.id == uuid.UUID(backtest_id)).first()
        
        if not backtest:
            return None
        
        if backtest.status != BacktestStatus.COMPLETED:
            return None
        
        return BacktestResult.from_orm(backtest)
    
    def list_backtests(
        self,
        strategy_id: Optional[str] = None,
        account_id: Optional[str] = None,
        limit: int = 50,
        db: Session = None
    ) -> List[Dict]:
        """
        List backtests with optional filters.
        
        Args:
            strategy_id: Filter by strategy ID
            account_id: Filter by account ID
            limit: Maximum number of results
            db: Database session
            
        Returns:
            List of backtest summaries
        """
        query = db.query(Backtest)
        
        if strategy_id:
            query = query.filter(Backtest.strategy_id == uuid.UUID(strategy_id))
        
        if account_id:
            query = query.filter(Backtest.account_id == uuid.UUID(account_id))
        
        query = query.order_by(Backtest.created_at.desc()).limit(limit)
        
        backtests = query.all()
        
        results = []
        for bt in backtests:
            result = {
                'id': str(bt.id),
                'strategy_id': str(bt.strategy_id),
                'account_id': str(bt.account_id),
                'status': bt.status.value,
                'created_at': bt.created_at.isoformat(),
                'completed_at': bt.completed_at.isoformat() if bt.completed_at else None
            }
            
            # Add summary metrics if completed
            if bt.status == BacktestStatus.COMPLETED and bt.metrics:
                metrics = bt.metrics.get('metrics', {})
                result['summary'] = {
                    'total_return': metrics.get('total_return', 0),
                    'total_trades': metrics.get('total_trades', 0),
                    'win_rate': metrics.get('win_rate', 0),
                    'max_drawdown': metrics.get('max_drawdown', 0)
                }
            
            results.append(result)
        
        return results
    
    def activate_strategy_from_backtest(
        self,
        backtest_id: str,
        trading_mode: str,
        db: Session
    ) -> Dict:
        """
        Activate a strategy in paper trading mode after successful backtest.
        
        Args:
            backtest_id: Backtest ID
            trading_mode: Trading mode ('paper' only for now)
            db: Database session
            
        Returns:
            Activation result
        """
        if trading_mode != 'paper':
            raise ValueError("Only paper trading mode is supported for backtest activation")
        
        backtest = db.query(Backtest).filter(Backtest.id == uuid.UUID(backtest_id)).first()
        
        if not backtest:
            raise ValueError(f"Backtest {backtest_id} not found")
        
        if backtest.status != BacktestStatus.COMPLETED:
            raise ValueError("Can only activate strategies from completed backtests")
        
        # In production, this would create an active strategy instance
        # For now, just return success
        return {
            'success': True,
            'message': 'Strategy activated in paper trading mode',
            'strategy_id': str(backtest.strategy_id),
            'trading_mode': trading_mode
        }
