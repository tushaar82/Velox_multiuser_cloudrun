"""
Historical Data Downloader

Downloads historical market data from Angel One SmartAPI for replay testing.
"""
import sys
import os
import csv
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import logging

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HistoricalDataDownloader:
    """
    Downloads historical data from Angel One SmartAPI.
    
    Saves data in CSV format for replay testing.
    """
    
    def __init__(self, output_dir: str = "./replay_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to import SmartAPI
        try:
            from smartapi import SmartConnect
            self.smartapi_available = True
            self.smart_api = None
        except ImportError:
            logger.warning("SmartAPI not installed. Will generate mock data instead.")
            self.smartapi_available = False
    
    def connect(self, api_key: str, client_code: str, password: str, totp: str) -> bool:
        """
        Connect to Angel One SmartAPI.
        
        Args:
            api_key: API key
            client_code: Client code
            password: Password
            totp: TOTP token
        
        Returns:
            True if connected successfully
        """
        if not self.smartapi_available:
            logger.error("SmartAPI not available")
            return False
        
        try:
            from smartapi import SmartConnect
            
            self.smart_api = SmartConnect(api_key=api_key)
            data = self.smart_api.generateSession(client_code, password, totp)
            
            if data['status']:
                logger.info("Connected to Angel One SmartAPI successfully")
                return True
            else:
                logger.error(f"Failed to connect: {data.get('message')}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to SmartAPI: {e}", exc_info=True)
            return False
    
    def download_symbol_data(
        self,
        symbol: str,
        token: str,
        exchange: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "ONE_MINUTE"
    ) -> Optional[str]:
        """
        Download historical data for a symbol.
        
        Args:
            symbol: Symbol name
            token: Symbol token
            exchange: Exchange (NSE, BSE, etc.)
            start_date: Start date
            end_date: End date
            interval: Candle interval
        
        Returns:
            Path to saved CSV file or None if failed
        """
        if not self.smartapi_available or not self.smart_api:
            logger.warning(f"SmartAPI not available, generating mock data for {symbol}")
            return self._generate_mock_data(symbol, start_date, end_date)
        
        try:
            # Download data from SmartAPI
            params = {
                "exchange": exchange,
                "symboltoken": token,
                "interval": interval,
                "fromdate": start_date.strftime("%Y-%m-%d %H:%M"),
                "todate": end_date.strftime("%Y-%m-%d %H:%M")
            }
            
            logger.info(f"Downloading {symbol} from {start_date} to {end_date}...")
            data = self.smart_api.getCandleData(params)
            
            if not data or 'data' not in data:
                logger.error(f"No data received for {symbol}")
                return None
            
            # Save to CSV
            output_file = self.output_dir / f"{symbol}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"
            
            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume'])
                
                for candle in data['data']:
                    # candle format: [timestamp, open, high, low, close, volume]
                    timestamp = datetime.strptime(candle[0], "%Y-%m-%dT%H:%M:%S%z")
                    writer.writerow([
                        timestamp.isoformat(),
                        symbol,
                        candle[1],  # open
                        candle[2],  # high
                        candle[3],  # low
                        candle[4],  # close
                        candle[5]   # volume
                    ])
            
            logger.info(f"Saved {len(data['data'])} candles to {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"Error downloading data for {symbol}: {e}", exc_info=True)
            return None
    
    def _generate_mock_data(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> str:
        """
        Generate mock historical data for testing.
        
        Args:
            symbol: Symbol name
            start_date: Start date
            end_date: End date
        
        Returns:
            Path to saved CSV file
        """
        import random
        
        output_file = self.output_dir / f"{symbol}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_mock.csv"
        
        logger.info(f"Generating mock data for {symbol}...")
        
        # Generate realistic price data
        base_price = 1000.0
        current_price = base_price
        current_time = start_date
        
        candles = []
        
        while current_time < end_date:
            # Generate OHLC for 1-minute candle
            open_price = current_price
            
            # Random price movement
            change = random.gauss(0, 0.005)  # 0.5% volatility
            close_price = open_price * (1 + change)
            
            high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.002)))
            low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.002)))
            
            volume = random.randint(1000, 50000)
            
            candles.append([
                current_time.isoformat(),
                symbol,
                round(open_price, 2),
                round(high_price, 2),
                round(low_price, 2),
                round(close_price, 2),
                volume
            ])
            
            current_price = close_price
            current_time += timedelta(minutes=1)
        
        # Write to CSV
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'symbol', 'open', 'high', 'low', 'close', 'volume'])
            writer.writerows(candles)
        
        logger.info(f"Generated {len(candles)} mock candles to {output_file}")
        return str(output_file)
    
    def download_multiple_symbols(
        self,
        symbols: List[dict],
        days: int = 30
    ) -> List[str]:
        """
        Download data for multiple symbols.
        
        Args:
            symbols: List of symbol dicts with 'symbol', 'token', 'exchange'
            days: Number of days to download
        
        Returns:
            List of saved file paths
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        files = []
        
        for symbol_info in symbols:
            file_path = self.download_symbol_data(
                symbol=symbol_info['symbol'],
                token=symbol_info.get('token', ''),
                exchange=symbol_info.get('exchange', 'NSE'),
                start_date=start_date,
                end_date=end_date
            )
            
            if file_path:
                files.append(file_path)
        
        return files


def main():
    """Main download function"""
    parser = argparse.ArgumentParser(description='Download historical market data')
    parser.add_argument('--days', type=int, default=30, help='Number of days to download')
    parser.add_argument('--output-dir', default='./replay_data', help='Output directory')
    parser.add_argument('--symbols', nargs='+', default=['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK'],
                       help='Symbols to download')
    parser.add_argument('--api-key', help='Angel One API key')
    parser.add_argument('--client-code', help='Angel One client code')
    parser.add_argument('--password', help='Angel One password')
    parser.add_argument('--totp', help='Angel One TOTP')
    
    args = parser.parse_args()
    
    downloader = HistoricalDataDownloader(output_dir=args.output_dir)
    
    # Connect if credentials provided
    if args.api_key and args.client_code and args.password and args.totp:
        if not downloader.connect(args.api_key, args.client_code, args.password, args.totp):
            logger.error("Failed to connect to Angel One. Will generate mock data.")
    
    # Prepare symbol list
    symbols = [{'symbol': s, 'token': '', 'exchange': 'NSE'} for s in args.symbols]
    
    # Download data
    files = downloader.download_multiple_symbols(symbols, days=args.days)
    
    logger.info(f"Downloaded {len(files)} files:")
    for file in files:
        logger.info(f"  - {file}")


if __name__ == "__main__":
    main()
