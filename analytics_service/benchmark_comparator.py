"""
Benchmark Comparison Service

This module compares portfolio performance against NSE benchmark indices
like NIFTY 50 and BANK NIFTY.
"""

from datetime import datetime
from typing import List, Optional
import numpy as np
from sqlalchemy.orm import Session

from analytics_service.models import BenchmarkComparison, EquityPoint, AnalyticsPeriod


class BenchmarkComparator:
    """Compares portfolio performance with benchmark indices"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def compare_to_benchmark(
        self,
        equity_curve: List[EquityPoint],
        benchmark_name: str,
        period: AnalyticsPeriod
    ) -> BenchmarkComparison:
        """
        Compare portfolio performance to benchmark index
        
        Args:
            equity_curve: Portfolio equity curve
            benchmark_name: Name of benchmark (e.g., 'NIFTY 50', 'BANK NIFTY')
            period: Time period for comparison
            
        Returns:
            BenchmarkComparison with relative performance metrics
        """
        # Fetch benchmark data for the period
        benchmark_returns = self._fetch_benchmark_data(benchmark_name, period)
        
        if not equity_curve or not benchmark_returns:
            return self._empty_comparison(benchmark_name)
        
        # Calculate portfolio returns
        portfolio_returns = self._calculate_portfolio_returns(equity_curve)
        
        # Calculate total returns
        portfolio_return = self._calculate_total_return(equity_curve)
        benchmark_return = self._calculate_benchmark_return(benchmark_returns)
        
        # Calculate alpha (excess return)
        alpha = portfolio_return - benchmark_return
        
        # Calculate beta
        beta = self._calculate_beta(portfolio_returns, benchmark_returns)
        
        # Calculate correlation
        correlation = self._calculate_correlation(portfolio_returns, benchmark_returns)
        
        # Calculate tracking error
        tracking_error = self._calculate_tracking_error(portfolio_returns, benchmark_returns)
        
        # Calculate information ratio
        information_ratio = alpha / tracking_error if tracking_error > 0 else 0.0
        
        return BenchmarkComparison(
            benchmark_name=benchmark_name,
            portfolio_return=portfolio_return,
            benchmark_return=benchmark_return,
            alpha=alpha,
            beta=beta,
            correlation=correlation,
            tracking_error=tracking_error,
            information_ratio=information_ratio
        )
    
    def _fetch_benchmark_data(
        self,
        benchmark_name: str,
        period: AnalyticsPeriod
    ) -> List[float]:
        """
        Fetch benchmark index data for the period
        
        Note: This is a placeholder implementation. In production, this would
        fetch actual NSE index data from a data provider or database.
        
        Args:
            benchmark_name: Name of benchmark index
            period: Time period
            
        Returns:
            List of daily returns
        """
        # TODO: Implement actual data fetching from NSE or data provider
        # For now, return simulated benchmark returns
        
        days = (period.end_date - period.start_date).days
        
        if benchmark_name == "NIFTY 50":
            # Simulate NIFTY 50 returns (average ~12% annual return)
            daily_return = 0.12 / 252  # Annualized to daily
            volatility = 0.15 / np.sqrt(252)  # Daily volatility
        elif benchmark_name == "BANK NIFTY":
            # Simulate BANK NIFTY returns (average ~15% annual return, higher volatility)
            daily_return = 0.15 / 252
            volatility = 0.20 / np.sqrt(252)
        else:
            # Default benchmark
            daily_return = 0.10 / 252
            volatility = 0.12 / np.sqrt(252)
        
        # Generate simulated returns
        np.random.seed(42)  # For reproducibility
        returns = np.random.normal(daily_return, volatility, days)
        
        return returns.tolist()
    
    def _calculate_portfolio_returns(self, equity_curve: List[EquityPoint]) -> List[float]:
        """Calculate daily returns from equity curve"""
        if len(equity_curve) < 2:
            return []
        
        returns = []
        for i in range(1, len(equity_curve)):
            prev_equity = equity_curve[i-1].equity
            curr_equity = equity_curve[i].equity
            
            if prev_equity > 0:
                daily_return = (curr_equity - prev_equity) / prev_equity
                returns.append(daily_return)
        
        return returns
    
    def _calculate_total_return(self, equity_curve: List[EquityPoint]) -> float:
        """Calculate total return percentage from equity curve"""
        if not equity_curve or len(equity_curve) < 2:
            return 0.0
        
        initial_equity = equity_curve[0].equity
        final_equity = equity_curve[-1].equity
        
        if initial_equity > 0:
            return ((final_equity - initial_equity) / initial_equity) * 100
        
        return 0.0
    
    def _calculate_benchmark_return(self, benchmark_returns: List[float]) -> float:
        """Calculate total benchmark return from daily returns"""
        if not benchmark_returns:
            return 0.0
        
        # Compound returns
        cumulative_return = 1.0
        for daily_return in benchmark_returns:
            cumulative_return *= (1 + daily_return)
        
        return (cumulative_return - 1) * 100
    
    def _calculate_beta(
        self,
        portfolio_returns: List[float],
        benchmark_returns: List[float]
    ) -> float:
        """
        Calculate portfolio beta relative to benchmark
        
        Beta measures the portfolio's sensitivity to benchmark movements.
        Beta = Covariance(portfolio, benchmark) / Variance(benchmark)
        """
        if not portfolio_returns or not benchmark_returns:
            return 1.0
        
        # Align lengths
        min_length = min(len(portfolio_returns), len(benchmark_returns))
        portfolio_returns = portfolio_returns[:min_length]
        benchmark_returns = benchmark_returns[:min_length]
        
        if len(portfolio_returns) < 2:
            return 1.0
        
        # Calculate covariance and variance
        covariance = np.cov(portfolio_returns, benchmark_returns)[0][1]
        benchmark_variance = np.var(benchmark_returns)
        
        if benchmark_variance == 0:
            return 1.0
        
        beta = covariance / benchmark_variance
        return beta
    
    def _calculate_correlation(
        self,
        portfolio_returns: List[float],
        benchmark_returns: List[float]
    ) -> float:
        """Calculate correlation between portfolio and benchmark returns"""
        if not portfolio_returns or not benchmark_returns:
            return 0.0
        
        # Align lengths
        min_length = min(len(portfolio_returns), len(benchmark_returns))
        portfolio_returns = portfolio_returns[:min_length]
        benchmark_returns = benchmark_returns[:min_length]
        
        if len(portfolio_returns) < 2:
            return 0.0
        
        correlation = np.corrcoef(portfolio_returns, benchmark_returns)[0][1]
        return correlation
    
    def _calculate_tracking_error(
        self,
        portfolio_returns: List[float],
        benchmark_returns: List[float]
    ) -> float:
        """
        Calculate tracking error (standard deviation of excess returns)
        
        Tracking error measures how closely the portfolio follows the benchmark.
        """
        if not portfolio_returns or not benchmark_returns:
            return 0.0
        
        # Align lengths
        min_length = min(len(portfolio_returns), len(benchmark_returns))
        portfolio_returns = portfolio_returns[:min_length]
        benchmark_returns = benchmark_returns[:min_length]
        
        if len(portfolio_returns) < 2:
            return 0.0
        
        # Calculate excess returns
        excess_returns = np.array(portfolio_returns) - np.array(benchmark_returns)
        
        # Tracking error is the standard deviation of excess returns
        tracking_error = np.std(excess_returns) * np.sqrt(252) * 100  # Annualized percentage
        
        return tracking_error
    
    def _empty_comparison(self, benchmark_name: str) -> BenchmarkComparison:
        """Return empty comparison when data is insufficient"""
        return BenchmarkComparison(
            benchmark_name=benchmark_name,
            portfolio_return=0.0,
            benchmark_return=0.0,
            alpha=0.0,
            beta=1.0,
            correlation=0.0,
            tracking_error=0.0,
            information_ratio=0.0
        )
    
    def get_available_benchmarks(self) -> List[str]:
        """
        Get list of available benchmark indices
        
        Returns:
            List of benchmark names
        """
        return [
            "NIFTY 50",
            "BANK NIFTY",
            "NIFTY IT",
            "NIFTY PHARMA",
            "NIFTY AUTO",
            "NIFTY FMCG",
            "NIFTY METAL",
            "NIFTY REALTY"
        ]
