"""
Mock Data Generator

Generates mock market data for edge cases and testing scenarios.
"""
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EdgeCaseType(Enum):
    """Types of edge cases to generate"""
    GAPS = "gaps"
    CIRCUIT_BREAKER = "circuit_breaker"
    EXTREME_VOLATILITY = "extreme_volatility"
    FLASH_CRASH = "flash_crash"
    ZERO_VOLUME = "zero_volume"
    PRICE_SPIKE = "price_spike"
    HALTED_TRADING = "halted_trading"


class MockDataGenerator:
    """
    Generates mock market data for edge case testing.
    
    Creates realistic but controlled scenarios for testing strategy robustness.
    """
    
    def __init__(self, output_dir: str = "./test_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_normal_data(
        self,
        symbol: str,
        start_price: float,
        num_candles: int,
        start_time: datetime = None
    ) -> str:
        """Generate normal market data"""
        if start_time is None:
            start_time = datetime.now()
        
        candles = []
        current_price = start_price
        current_time = start_time
        
        for i in range(num_candles):
            # Normal price movement
            change = random.gauss(0, 0.01)
            open_price = current_price
            close_price = open_price * (1 + change)
            
            high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.005)))
            low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.005)))
            
            volume = random.randint(1000, 10000)
            
            candles.append({
                'timestamp': current_time.isoformat(),
                'symbol': symbol,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
            
            current_price = close_price
            current_time += timedelta(minutes=1)
        
        # Save to file
        filename = f"{symbol}_normal_{start_time.strftime('%Y%m%d')}.csv"
        file_path = self.output_dir / filename
        self._save_to_csv(candles, file_path)
        
        logger.info(f"Generated normal data: {file_path}")
        return str(file_path)
    
    def generate_with_gaps(
        self,
        symbol: str,
        start_price: float,
        num_candles: int,
        num_gaps: int = 5,
        gap_duration_minutes: int = 10
    ) -> str:
        """Generate data with gaps"""
        candles = []
        current_price = start_price
        current_time = datetime.now()
        
        gap_positions = sorted(random.sample(range(num_candles), min(num_gaps, num_candles)))
        
        for i in range(num_candles):
            # Check if this is a gap position
            if i in gap_positions:
                current_time += timedelta(minutes=gap_duration_minutes)
                logger.info(f"Inserted {gap_duration_minutes} minute gap at candle {i}")
            
            # Generate candle
            change = random.gauss(0, 0.01)
            open_price = current_price
            close_price = open_price * (1 + change)
            
            high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.005)))
            low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.005)))
            
            volume = random.randint(1000, 10000)
            
            candles.append({
                'timestamp': current_time.isoformat(),
                'symbol': symbol,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
            
            current_price = close_price
            current_time += timedelta(minutes=1)
        
        # Save to file
        filename = f"{symbol}_gaps_{datetime.now().strftime('%Y%m%d')}.csv"
        file_path = self.output_dir / filename
        self._save_to_csv(candles, file_path)
        
        logger.info(f"Generated data with gaps: {file_path}")
        return str(file_path)
    
    def generate_circuit_breaker(
        self,
        symbol: str,
        start_price: float,
        num_candles: int,
        trigger_at: int = None
    ) -> str:
        """Generate data with circuit breaker event"""
        if trigger_at is None:
            trigger_at = num_candles // 2
        
        candles = []
        current_price = start_price
        current_time = datetime.now()
        
        for i in range(num_candles):
            if i == trigger_at:
                # Circuit breaker: 10% drop in single candle
                change = -0.10
                logger.info(f"Circuit breaker triggered at candle {i}")
            elif i > trigger_at and i < trigger_at + 10:
                # Trading halted for 10 candles
                change = 0
                volume = 0
            else:
                # Normal movement
                change = random.gauss(0, 0.01)
                volume = random.randint(1000, 10000)
            
            open_price = current_price
            close_price = open_price * (1 + change)
            
            high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.002)))
            low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.002)))
            
            if i > trigger_at and i < trigger_at + 10:
                volume = 0
            else:
                volume = random.randint(1000, 10000)
            
            candles.append({
                'timestamp': current_time.isoformat(),
                'symbol': symbol,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
            
            current_price = close_price
            current_time += timedelta(minutes=1)
        
        # Save to file
        filename = f"{symbol}_circuit_breaker_{datetime.now().strftime('%Y%m%d')}.csv"
        file_path = self.output_dir / filename
        self._save_to_csv(candles, file_path)
        
        logger.info(f"Generated circuit breaker data: {file_path}")
        return str(file_path)
    
    def generate_extreme_volatility(
        self,
        symbol: str,
        start_price: float,
        num_candles: int
    ) -> str:
        """Generate extremely volatile data"""
        candles = []
        current_price = start_price
        current_time = datetime.now()
        
        for i in range(num_candles):
            # Extreme volatility: 5% standard deviation
            change = random.gauss(0, 0.05)
            open_price = current_price
            close_price = open_price * (1 + change)
            
            # Wide high-low range
            high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.03)))
            low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.03)))
            
            # High volume during volatility
            volume = random.randint(10000, 100000)
            
            candles.append({
                'timestamp': current_time.isoformat(),
                'symbol': symbol,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
            
            current_price = close_price
            current_time += timedelta(minutes=1)
        
        # Save to file
        filename = f"{symbol}_extreme_volatility_{datetime.now().strftime('%Y%m%d')}.csv"
        file_path = self.output_dir / filename
        self._save_to_csv(candles, file_path)
        
        logger.info(f"Generated extreme volatility data: {file_path}")
        return str(file_path)
    
    def generate_flash_crash(
        self,
        symbol: str,
        start_price: float,
        num_candles: int,
        crash_at: int = None
    ) -> str:
        """Generate flash crash scenario"""
        if crash_at is None:
            crash_at = num_candles // 2
        
        candles = []
        current_price = start_price
        current_time = datetime.now()
        
        for i in range(num_candles):
            if i == crash_at:
                # Flash crash: 20% drop
                change = -0.20
                volume = random.randint(50000, 200000)
                logger.info(f"Flash crash at candle {i}")
            elif i == crash_at + 1:
                # Immediate recovery: 15% gain
                change = 0.15
                volume = random.randint(50000, 200000)
            else:
                # Normal movement
                change = random.gauss(0, 0.01)
                volume = random.randint(1000, 10000)
            
            open_price = current_price
            close_price = open_price * (1 + change)
            
            high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.005)))
            low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.005)))
            
            candles.append({
                'timestamp': current_time.isoformat(),
                'symbol': symbol,
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'volume': volume
            })
            
            current_price = close_price
            current_time += timedelta(minutes=1)
        
        # Save to file
        filename = f"{symbol}_flash_crash_{datetime.now().strftime('%Y%m%d')}.csv"
        file_path = self.output_dir / filename
        self._save_to_csv(candles, file_path)
        
        logger.info(f"Generated flash crash data: {file_path}")
        return str(file_path)
    
    def _save_to_csv(self, candles: List[Dict], file_path: Path) -> None:
        """Save candles to CSV file"""
        with open(file_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume'])
            writer.writeheader()
            writer.writerows(candles)


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Mock Data Generator')
    parser.add_argument('--symbol', default='TEST', help='Symbol name')
    parser.add_argument('--price', type=float, default=1000.0, help='Starting price')
    parser.add_argument('--candles', type=int, default=1000, help='Number of candles')
    parser.add_argument('--output-dir', default='./test_data', help='Output directory')
    parser.add_argument('--type', choices=['normal', 'gaps', 'circuit_breaker', 'extreme_volatility', 'flash_crash', 'all'],
                       default='all', help='Type of data to generate')
    
    args = parser.parse_args()
    
    generator = MockDataGenerator(output_dir=args.output_dir)
    
    if args.type == 'normal' or args.type == 'all':
        generator.generate_normal_data(args.symbol, args.price, args.candles)
    
    if args.type == 'gaps' or args.type == 'all':
        generator.generate_with_gaps(args.symbol, args.price, args.candles)
    
    if args.type == 'circuit_breaker' or args.type == 'all':
        generator.generate_circuit_breaker(args.symbol, args.price, args.candles)
    
    if args.type == 'extreme_volatility' or args.type == 'all':
        generator.generate_extreme_volatility(args.symbol, args.price, args.candles)
    
    if args.type == 'flash_crash' or args.type == 'all':
        generator.generate_flash_crash(args.symbol, args.price, args.candles)
    
    logger.info("Mock data generation completed")


if __name__ == "__main__":
    main()
