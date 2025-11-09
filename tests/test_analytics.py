"""
Unit tests for Analytics Service

Tests performance metrics calculations, equity curve generation,
and benchmark comparisons.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from shared.database.connection import Base
from shared.models.position import Position, PositionSide
from shared.models.order import TradingMode
from analytics_service.performance_calculator import PerformanceCalculator
from analytics_service.trade_analyzer import TradeAnalyzer
from analytics_service.benchmark_comparator import BenchmarkComparator
from analytics_service.models import AnalyticsPeriod


@pytest.fixture
def db_session():
    """Create in-memory database session for testing"""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_account_id():
    """Generate sample account ID"""
    return str(uuid.uuid4())


@pytest.fixture
def sample_positions(db_session, sample_account_id):
    """Create sample closed positions for testing"""
    positions = []
    base_time = datetime.now() - timedelta(days=30)
    
    # Create 10 winning positions
    for i in range(10):
        position = Position(
            id=str(uuid.uuid4()),
            account_id=sample_account_id,
            strategy_id=str(uuid.uuid4()),
            symbol='RELIANCE',
            side=PositionSide.LONG,
            quantity=10,
            entry_price=2400.0,
            current_price=2450.0,
            unrealized_pnl=0.0,
            realized_pnl=500.0,  # Winning trade
            trading_mode=TradingMode.PAPER,
            opened_at=base_time + timedelta(days=i),
            closed_at=base_time + timedelta(days=i, hours=2)
        )
        db_session.add(position)
        positions.append(position)
    
    # Create 5 losing positions
    for i in range(5):
        position = Position(
            id=str(uuid.uuid4()),
            account_id=sample_account_id,
            strategy_id=str(uuid.uuid4()),
            symbol='TCS',
            side=PositionSide.LONG,
            quantity=10,
            entry_price=3500.0,
            current_price=3450.0,
            unrealized_pnl=0.0,
            realized_pnl=-500.0,  # Losing trade
            trading_mode=TradingMode.PAPER,
            opened_at=base_time + timedelta(days=10 + i),
            closed_at=base_time + timedelta(days=10 + i, hours=3)
        )
        db_session.add(position)
        positions.append(position)
    
    db_session.commit()
    return positions


def test_performance_metrics_calculation(db_session, sample_account_id, sample_positions):
    """Test performance metrics calculation with sample trades"""
    calculator = PerformanceCalculator(db_session)
    
    period = AnalyticsPeriod(
        period='monthly',
        start_date=datetime.now() - timedelta(days=31),
        end_date=datetime.now()
    )
    
    summary = calculator.calculate_performance_summary(
        account_id=sample_account_id,
        trading_mode=TradingMode.PAPER,
        period=period,
        initial_capital=1000000.0
    )
    
    # Verify basic metrics
    assert summary.account_id == sample_account_id
    assert summary.trading_mode == 'paper'
    
    # Verify performance metrics
    metrics = summary.metrics
    assert metrics.total_trades == 15  # 10 wins + 5 losses
    assert metrics.winning_trades == 10
    assert metrics.losing_trades == 5
    assert metrics.total_pnl == 2500.0  # (10 * 500) - (5 * 500)
    assert metrics.win_rate == pytest.approx(66.67, rel=0.1)  # 10/15 * 100
    
    # Verify profit factor
    assert metrics.gross_profit == 5000.0  # 10 * 500
    assert metrics.gross_loss == 2500.0  # 5 * 500
    assert metrics.profit_factor == pytest.approx(2.0, rel=0.01)  # 5000 / 2500
    
    # Verify average win/loss
    assert metrics.average_win == 500.0
    assert metrics.average_loss == 500.0


def test_equity_curve_generation(db_session, sample_account_id, sample_positions):
    """Test equity curve generation from trade history"""
    calculator = PerformanceCalculator(db_session)
    
    start_date = datetime.now() - timedelta(days=31)
    end_date = datetime.now()
    initial_capital = 1000000.0
    
    equity_curve = calculator.generate_equity_curve(
        account_id=sample_account_id,
        trading_mode=TradingMode.PAPER,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital
    )
    
    # Verify equity curve has points
    assert len(equity_curve) > 0
    
    # Verify starting point
    assert equity_curve[0].equity == initial_capital
    assert equity_curve[0].drawdown == 0.0
    
    # Verify final equity
    final_equity = equity_curve[-1].equity
    expected_final = initial_capital + 2500.0  # Total P&L
    assert final_equity == pytest.approx(expected_final, rel=0.01)


def test_trade_analysis(db_session, sample_account_id, sample_positions):
    """Test trade analysis calculations"""
    analyzer = TradeAnalyzer(db_session)
    
    period = AnalyticsPeriod(
        period='monthly',
        start_date=datetime.now() - timedelta(days=31),
        end_date=datetime.now()
    )
    
    statistics = analyzer.analyze_trades(
        account_id=sample_account_id,
        trading_mode=TradingMode.PAPER,
        period=period
    )
    
    # Verify holding times
    assert statistics.average_holding_time > 0
    assert statistics.median_holding_time > 0
    
    # Verify best/worst trades
    assert statistics.best_trade is not None
    assert statistics.best_trade.pnl == 500.0
    assert statistics.worst_trade is not None
    assert statistics.worst_trade.pnl == -500.0
    
    # Verify consecutive streaks
    assert statistics.consecutive_wins > 0
    assert statistics.consecutive_losses > 0
    
    # Verify profit by time analysis
    assert len(statistics.profit_by_time_of_day) == 24
    assert len(statistics.profit_by_day_of_week) == 7


def test_benchmark_comparison(db_session, sample_account_id, sample_positions):
    """Test benchmark comparison calculations"""
    comparator = BenchmarkComparator(db_session)
    calculator = PerformanceCalculator(db_session)
    
    period = AnalyticsPeriod(
        period='monthly',
        start_date=datetime.now() - timedelta(days=31),
        end_date=datetime.now()
    )
    
    # Generate equity curve
    equity_curve = calculator.generate_equity_curve(
        account_id=sample_account_id,
        trading_mode=TradingMode.PAPER,
        start_date=period.start_date,
        end_date=period.end_date,
        initial_capital=1000000.0
    )
    
    # Compare to NIFTY 50
    comparison = comparator.compare_to_benchmark(
        equity_curve=equity_curve,
        benchmark_name='NIFTY 50',
        period=period
    )
    
    # Verify comparison metrics
    assert comparison.benchmark_name == 'NIFTY 50'
    assert comparison.portfolio_return != 0.0
    assert comparison.benchmark_return != 0.0
    assert comparison.beta != 0.0
    
    # Alpha should be portfolio return - benchmark return
    expected_alpha = comparison.portfolio_return - comparison.benchmark_return
    assert comparison.alpha == pytest.approx(expected_alpha, rel=0.01)


def test_empty_positions(db_session, sample_account_id):
    """Test analytics with no positions"""
    calculator = PerformanceCalculator(db_session)
    
    period = AnalyticsPeriod(
        period='monthly',
        start_date=datetime.now() - timedelta(days=31),
        end_date=datetime.now()
    )
    
    summary = calculator.calculate_performance_summary(
        account_id=sample_account_id,
        trading_mode=TradingMode.PAPER,
        period=period,
        initial_capital=1000000.0
    )
    
    # Verify all metrics are zero
    metrics = summary.metrics
    assert metrics.total_trades == 0
    assert metrics.winning_trades == 0
    assert metrics.losing_trades == 0
    assert metrics.total_pnl == 0.0
    assert metrics.win_rate == 0.0
    assert metrics.profit_factor == 0.0


def test_sharpe_ratio_calculation(db_session, sample_account_id, sample_positions):
    """Test Sharpe ratio calculation"""
    calculator = PerformanceCalculator(db_session)
    
    period = AnalyticsPeriod(
        period='monthly',
        start_date=datetime.now() - timedelta(days=31),
        end_date=datetime.now()
    )
    
    summary = calculator.calculate_performance_summary(
        account_id=sample_account_id,
        trading_mode=TradingMode.PAPER,
        period=period,
        initial_capital=1000000.0
    )
    
    # Sharpe ratio should be calculated
    assert summary.metrics.sharpe_ratio != 0.0
    
    # Sortino ratio should also be calculated
    assert summary.metrics.sortino_ratio != 0.0


def test_max_drawdown_calculation(db_session, sample_account_id):
    """Test maximum drawdown calculation"""
    calculator = PerformanceCalculator(db_session)
    
    # Create positions with drawdown scenario
    base_time = datetime.now() - timedelta(days=10)
    
    # Winning trade
    position1 = Position(
        id=str(uuid.uuid4()),
        account_id=sample_account_id,
        symbol='RELIANCE',
        side=PositionSide.LONG,
        quantity=10,
        entry_price=2400.0,
        current_price=2500.0,
        unrealized_pnl=0.0,
        realized_pnl=1000.0,
        trading_mode=TradingMode.PAPER,
        opened_at=base_time,
        closed_at=base_time + timedelta(hours=1)
    )
    db_session.add(position1)
    
    # Large losing trade (creates drawdown)
    position2 = Position(
        id=str(uuid.uuid4()),
        account_id=sample_account_id,
        symbol='TCS',
        side=PositionSide.LONG,
        quantity=10,
        entry_price=3500.0,
        current_price=3200.0,
        unrealized_pnl=0.0,
        realized_pnl=-3000.0,
        trading_mode=TradingMode.PAPER,
        opened_at=base_time + timedelta(hours=2),
        closed_at=base_time + timedelta(hours=3)
    )
    db_session.add(position2)
    
    # Recovery trade
    position3 = Position(
        id=str(uuid.uuid4()),
        account_id=sample_account_id,
        symbol='INFY',
        side=PositionSide.LONG,
        quantity=10,
        entry_price=1500.0,
        current_price=1600.0,
        unrealized_pnl=0.0,
        realized_pnl=1000.0,
        trading_mode=TradingMode.PAPER,
        opened_at=base_time + timedelta(hours=4),
        closed_at=base_time + timedelta(hours=5)
    )
    db_session.add(position3)
    
    db_session.commit()
    
    period = AnalyticsPeriod(
        period='monthly',
        start_date=base_time - timedelta(days=1),
        end_date=datetime.now()
    )
    
    summary = calculator.calculate_performance_summary(
        account_id=sample_account_id,
        trading_mode=TradingMode.PAPER,
        period=period,
        initial_capital=1000000.0
    )
    
    # Max drawdown should be detected
    assert summary.metrics.max_drawdown > 0.0


def test_strategy_breakdown(db_session, sample_account_id):
    """Test strategy-level performance breakdown"""
    calculator = PerformanceCalculator(db_session)
    
    strategy1_id = str(uuid.uuid4())
    strategy2_id = str(uuid.uuid4())
    base_time = datetime.now() - timedelta(days=10)
    
    # Create positions for strategy 1 (winning)
    for i in range(5):
        position = Position(
            id=str(uuid.uuid4()),
            account_id=sample_account_id,
            strategy_id=strategy1_id,
            symbol='RELIANCE',
            side=PositionSide.LONG,
            quantity=10,
            entry_price=2400.0,
            current_price=2450.0,
            unrealized_pnl=0.0,
            realized_pnl=500.0,
            trading_mode=TradingMode.PAPER,
            opened_at=base_time + timedelta(hours=i),
            closed_at=base_time + timedelta(hours=i+1)
        )
        db_session.add(position)
    
    # Create positions for strategy 2 (losing)
    for i in range(3):
        position = Position(
            id=str(uuid.uuid4()),
            account_id=sample_account_id,
            strategy_id=strategy2_id,
            symbol='TCS',
            side=PositionSide.LONG,
            quantity=10,
            entry_price=3500.0,
            current_price=3450.0,
            unrealized_pnl=0.0,
            realized_pnl=-500.0,
            trading_mode=TradingMode.PAPER,
            opened_at=base_time + timedelta(hours=i+10),
            closed_at=base_time + timedelta(hours=i+11)
        )
        db_session.add(position)
    
    db_session.commit()
    
    period = AnalyticsPeriod(
        period='monthly',
        start_date=base_time - timedelta(days=1),
        end_date=datetime.now()
    )
    
    summary = calculator.calculate_performance_summary(
        account_id=sample_account_id,
        trading_mode=TradingMode.PAPER,
        period=period,
        initial_capital=1000000.0
    )
    
    # Verify strategy breakdown
    assert len(summary.strategy_breakdown) == 2
    
    # Find strategies in breakdown
    strategy1_perf = next((s for s in summary.strategy_breakdown if s.strategy_id == str(strategy1_id)), None)
    strategy2_perf = next((s for s in summary.strategy_breakdown if s.strategy_id == str(strategy2_id)), None)
    
    assert strategy1_perf is not None
    assert strategy1_perf.total_trades == 5
    assert strategy1_perf.total_pnl == 2500.0
    
    assert strategy2_perf is not None
    assert strategy2_perf.total_trades == 3
    assert strategy2_perf.total_pnl == -1500.0


def test_equity_curve_with_multiple_strategies(db_session, sample_account_id):
    """Test equity curve generation with multiple strategies"""
    calculator = PerformanceCalculator(db_session)
    
    strategy1_id = str(uuid.uuid4())
    strategy2_id = str(uuid.uuid4())
    base_time = datetime.now() - timedelta(days=20)
    
    # Interleave trades from two strategies
    for i in range(5):
        # Strategy 1 trade
        position1 = Position(
            id=str(uuid.uuid4()),
            account_id=sample_account_id,
            strategy_id=strategy1_id,
            symbol='RELIANCE',
            side=PositionSide.LONG,
            quantity=10,
            entry_price=2400.0,
            current_price=2450.0,
            unrealized_pnl=0.0,
            realized_pnl=500.0,
            trading_mode=TradingMode.PAPER,
            opened_at=base_time + timedelta(days=i*2),
            closed_at=base_time + timedelta(days=i*2, hours=2)
        )
        db_session.add(position1)
        
        # Strategy 2 trade
        position2 = Position(
            id=str(uuid.uuid4()),
            account_id=sample_account_id,
            strategy_id=strategy2_id,
            symbol='TCS',
            side=PositionSide.LONG,
            quantity=10,
            entry_price=3500.0,
            current_price=3550.0,
            unrealized_pnl=0.0,
            realized_pnl=500.0,
            trading_mode=TradingMode.PAPER,
            opened_at=base_time + timedelta(days=i*2+1),
            closed_at=base_time + timedelta(days=i*2+1, hours=2)
        )
        db_session.add(position2)
    
    db_session.commit()
    
    equity_curve = calculator.generate_equity_curve(
        account_id=sample_account_id,
        trading_mode=TradingMode.PAPER,
        start_date=base_time - timedelta(days=1),
        end_date=datetime.now(),
        initial_capital=1000000.0
    )
    
    # Verify equity curve has correct number of points (10 trades + 1 starting point)
    assert len(equity_curve) == 11
    
    # Verify equity increases monotonically (all winning trades)
    for i in range(1, len(equity_curve)):
        assert equity_curve[i].equity >= equity_curve[i-1].equity


def test_benchmark_comparison_with_different_indices(db_session, sample_account_id, sample_positions):
    """Test benchmark comparison with different NSE indices"""
    comparator = BenchmarkComparator(db_session)
    calculator = PerformanceCalculator(db_session)
    
    period = AnalyticsPeriod(
        period='monthly',
        start_date=datetime.now() - timedelta(days=31),
        end_date=datetime.now()
    )
    
    equity_curve = calculator.generate_equity_curve(
        account_id=sample_account_id,
        trading_mode=TradingMode.PAPER,
        start_date=period.start_date,
        end_date=period.end_date,
        initial_capital=1000000.0
    )
    
    # Test with NIFTY 50
    nifty_comparison = comparator.compare_to_benchmark(
        equity_curve=equity_curve,
        benchmark_name='NIFTY 50',
        period=period
    )
    assert nifty_comparison.benchmark_name == 'NIFTY 50'
    assert nifty_comparison.beta != 0.0
    assert nifty_comparison.correlation >= -1.0 and nifty_comparison.correlation <= 1.0
    
    # Test with BANK NIFTY
    banknifty_comparison = comparator.compare_to_benchmark(
        equity_curve=equity_curve,
        benchmark_name='BANK NIFTY',
        period=period
    )
    assert banknifty_comparison.benchmark_name == 'BANK NIFTY'
    assert banknifty_comparison.tracking_error >= 0.0


def test_performance_metrics_with_short_positions(db_session, sample_account_id):
    """Test performance metrics calculation with short positions"""
    calculator = PerformanceCalculator(db_session)
    base_time = datetime.now() - timedelta(days=10)
    
    # Create winning short positions
    for i in range(5):
        position = Position(
            id=str(uuid.uuid4()),
            account_id=sample_account_id,
            symbol='RELIANCE',
            side=PositionSide.SHORT,
            quantity=10,
            entry_price=2500.0,
            current_price=2450.0,
            unrealized_pnl=0.0,
            realized_pnl=500.0,  # Profit from short
            trading_mode=TradingMode.PAPER,
            opened_at=base_time + timedelta(hours=i),
            closed_at=base_time + timedelta(hours=i+1)
        )
        db_session.add(position)
    
    # Create losing short positions
    for i in range(3):
        position = Position(
            id=str(uuid.uuid4()),
            account_id=sample_account_id,
            symbol='TCS',
            side=PositionSide.SHORT,
            quantity=10,
            entry_price=3400.0,
            current_price=3500.0,
            unrealized_pnl=0.0,
            realized_pnl=-1000.0,  # Loss from short
            trading_mode=TradingMode.PAPER,
            opened_at=base_time + timedelta(hours=i+10),
            closed_at=base_time + timedelta(hours=i+11)
        )
        db_session.add(position)
    
    db_session.commit()
    
    period = AnalyticsPeriod(
        period='monthly',
        start_date=base_time - timedelta(days=1),
        end_date=datetime.now()
    )
    
    summary = calculator.calculate_performance_summary(
        account_id=sample_account_id,
        trading_mode=TradingMode.PAPER,
        period=period,
        initial_capital=1000000.0
    )
    
    # Verify metrics
    assert summary.metrics.total_trades == 8
    assert summary.metrics.winning_trades == 5
    assert summary.metrics.losing_trades == 3
    assert summary.metrics.total_pnl == -500.0  # (5 * 500) - (3 * 1000)


def test_drawdown_analysis(db_session, sample_account_id):
    """Test drawdown period analysis"""
    calculator = PerformanceCalculator(db_session)
    base_time = datetime.now() - timedelta(days=30)
    
    # Create a sequence with drawdown and recovery
    trades = [
        (1000.0, 0),   # Win - new peak
        (1000.0, 1),   # Win - new peak
        (-2000.0, 2),  # Loss - drawdown starts
        (-1000.0, 3),  # Loss - drawdown continues
        (1500.0, 4),   # Win - partial recovery
        (2000.0, 5),   # Win - full recovery, new peak
        (-500.0, 6),   # Small loss
        (1000.0, 7),   # Win - recovery
    ]
    
    for pnl, day_offset in trades:
        position = Position(
            id=str(uuid.uuid4()),
            account_id=sample_account_id,
            symbol='RELIANCE',
            side=PositionSide.LONG,
            quantity=10,
            entry_price=2400.0,
            current_price=2400.0 + (pnl / 10),
            unrealized_pnl=0.0,
            realized_pnl=pnl,
            trading_mode=TradingMode.PAPER,
            opened_at=base_time + timedelta(days=day_offset),
            closed_at=base_time + timedelta(days=day_offset, hours=2)
        )
        db_session.add(position)
    
    db_session.commit()
    
    # Generate equity curve
    equity_curve = calculator.generate_equity_curve(
        account_id=sample_account_id,
        trading_mode=TradingMode.PAPER,
        start_date=base_time - timedelta(days=1),
        end_date=datetime.now(),
        initial_capital=1000000.0
    )
    
    # Analyze drawdown periods
    drawdown_periods = calculator.calculate_drawdown_analysis(equity_curve)
    
    # Should have at least one drawdown period
    assert len(drawdown_periods) > 0
    
    # Verify drawdown period structure
    for period in drawdown_periods:
        assert period.start_date is not None
        assert period.end_date is not None
        assert period.drawdown_percent > 0.0
        assert period.duration_days >= 0


def test_performance_metrics_with_live_trading(db_session, sample_account_id):
    """Test performance metrics for live trading mode"""
    calculator = PerformanceCalculator(db_session)
    base_time = datetime.now() - timedelta(days=10)
    
    # Create positions in live trading mode
    for i in range(5):
        position = Position(
            id=str(uuid.uuid4()),
            account_id=sample_account_id,
            symbol='RELIANCE',
            side=PositionSide.LONG,
            quantity=10,
            entry_price=2400.0,
            current_price=2450.0,
            unrealized_pnl=0.0,
            realized_pnl=500.0,
            trading_mode=TradingMode.LIVE,  # Live trading
            opened_at=base_time + timedelta(hours=i),
            closed_at=base_time + timedelta(hours=i+1)
        )
        db_session.add(position)
    
    db_session.commit()
    
    period = AnalyticsPeriod(
        period='monthly',
        start_date=base_time - timedelta(days=1),
        end_date=datetime.now()
    )
    
    # Test with live trading mode
    summary = calculator.calculate_performance_summary(
        account_id=sample_account_id,
        trading_mode=TradingMode.LIVE,
        period=period,
        initial_capital=1000000.0
    )
    
    assert summary.trading_mode == 'live'
    assert summary.metrics.total_trades == 5
    assert summary.metrics.total_pnl == 2500.0


def test_benchmark_comparison_with_empty_equity_curve(db_session):
    """Test benchmark comparison with empty equity curve"""
    comparator = BenchmarkComparator(db_session)
    
    period = AnalyticsPeriod(
        period='monthly',
        start_date=datetime.now() - timedelta(days=31),
        end_date=datetime.now()
    )
    
    # Empty equity curve
    comparison = comparator.compare_to_benchmark(
        equity_curve=[],
        benchmark_name='NIFTY 50',
        period=period
    )
    
    # Should return empty comparison
    assert comparison.benchmark_name == 'NIFTY 50'
    assert comparison.portfolio_return == 0.0
    assert comparison.benchmark_return == 0.0
    assert comparison.alpha == 0.0


def test_annualized_return_calculation(db_session, sample_account_id):
    """Test annualized return calculation over different periods"""
    calculator = PerformanceCalculator(db_session)
    base_time = datetime.now() - timedelta(days=365)
    
    # Create positions over a year
    for i in range(12):  # Monthly trades
        position = Position(
            id=str(uuid.uuid4()),
            account_id=sample_account_id,
            symbol='RELIANCE',
            side=PositionSide.LONG,
            quantity=10,
            entry_price=2400.0,
            current_price=2450.0,
            unrealized_pnl=0.0,
            realized_pnl=10000.0,  # Consistent monthly profit
            trading_mode=TradingMode.PAPER,
            opened_at=base_time + timedelta(days=i*30),
            closed_at=base_time + timedelta(days=i*30, hours=2)
        )
        db_session.add(position)
    
    db_session.commit()
    
    period = AnalyticsPeriod(
        period='yearly',
        start_date=base_time - timedelta(days=1),
        end_date=datetime.now()
    )
    
    summary = calculator.calculate_performance_summary(
        account_id=sample_account_id,
        trading_mode=TradingMode.PAPER,
        period=period,
        initial_capital=1000000.0
    )
    
    # Total return should be 12%
    assert summary.metrics.total_return == pytest.approx(12.0, rel=0.01)
    
    # Annualized return should be close to total return for 1 year period
    assert summary.metrics.annualized_return == pytest.approx(12.0, rel=0.1)


def test_risk_metrics_calculation(db_session, sample_account_id, sample_positions):
    """Test risk metrics calculation"""
    calculator = PerformanceCalculator(db_session)
    
    period = AnalyticsPeriod(
        period='monthly',
        start_date=datetime.now() - timedelta(days=31),
        end_date=datetime.now()
    )
    
    summary = calculator.calculate_performance_summary(
        account_id=sample_account_id,
        trading_mode=TradingMode.PAPER,
        period=period,
        initial_capital=1000000.0
    )
    
    # Verify risk metrics are calculated
    risk_metrics = summary.risk_metrics
    assert risk_metrics is not None
    assert risk_metrics.value_at_risk >= 0.0
    assert risk_metrics.beta != 0.0
    assert risk_metrics.max_position_size >= 0.0
    assert risk_metrics.average_position_size >= 0.0


def test_consecutive_wins_and_losses(db_session, sample_account_id):
    """Test consecutive wins and losses calculation"""
    calculator = PerformanceCalculator(db_session)
    base_time = datetime.now() - timedelta(days=10)
    
    # Create pattern: 5 wins, 3 losses, 4 wins, 2 losses
    pnl_pattern = [500, 500, 500, 500, 500, -500, -500, -500, 500, 500, 500, 500, -500, -500]
    
    for i, pnl in enumerate(pnl_pattern):
        position = Position(
            id=str(uuid.uuid4()),
            account_id=sample_account_id,
            symbol='RELIANCE',
            side=PositionSide.LONG,
            quantity=10,
            entry_price=2400.0,
            current_price=2400.0 + (pnl / 10),
            unrealized_pnl=0.0,
            realized_pnl=pnl,
            trading_mode=TradingMode.PAPER,
            opened_at=base_time + timedelta(hours=i),
            closed_at=base_time + timedelta(hours=i+1)
        )
        db_session.add(position)
    
    db_session.commit()
    
    period = AnalyticsPeriod(
        period='monthly',
        start_date=base_time - timedelta(days=1),
        end_date=datetime.now()
    )
    
    summary = calculator.calculate_performance_summary(
        account_id=sample_account_id,
        trading_mode=TradingMode.PAPER,
        period=period,
        initial_capital=1000000.0
    )
    
    # Max consecutive wins should be 5
    assert summary.metrics.consecutive_wins == 5
    
    # Max consecutive losses should be 3
    assert summary.metrics.consecutive_losses == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
