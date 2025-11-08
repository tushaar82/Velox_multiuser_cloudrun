"""
Market Data Simulator

Provides simulated market data for offline testing and development.
"""
import csv
import random
import threading
import time
from datetime import datetime, timedelta
from typing import List, Optional, Callable, Dict
from enum import Enum
import logging

from .models import Tick

logger = logging.getLogger(__name__)


class SimulatorMode(Enum):
    """Simulator operating modes"""
    LIVE = "live"  # Connect to real market data
    REPLAY = "replay"  # Replay historical data
    SIMULATED = "simulated"  # Generate synthetic data


class SimulatorState(Enum):
    """Simulator playback states"""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class MarketDataSimulator:
    """
    Simulates market data for offline testing.
    
    Supports:
    - Historical data replay at configurable speeds
    - CSV file loading for custom tick data
    - Realistic tick data generation
    - Playback controls (play, pause, stop, speed adjustment)
    """
    
    def __init__(self):
        self.mode = SimulatorMode.SIMULATED
        self.state = SimulatorState.STOPPED
        self.speed = 1.0  # 1x = real-time
        self.current_time: Optional[datetime] = None
        self.tick_callbacks: List[Callable[[Tick], None]] = []
        self.playback_thread: Optional[threading.Thread] = None
        self.historical_data: Dict[str, List[Tick]] = {}  # symbol -> ticks
        self.current_indices: Dict[str, int] = {}  # symbol -> current index
        self._stop_flag = False
    
    def load_csv_data(self, symbol: str, csv_file: str) -> int:
        """
        Load historical tick data from CSV file.
        
        CSV format: timestamp,symbol,price,volume
        
        Args:
            symbol: Symbol to load data for
            csv_file: Path to CSV file
        
        Returns:
            Number of ticks loaded
        """
        ticks = []
        
        try:
            with open(csv_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tick = Tick(
                        symbol=row['symbol'],
                        price=float(row['price']),
                        volume=int(row['volume']),
                        timestamp=datetime.fromisoformat(row['timestamp'])
                    )
                    ticks.append(tick)
            
            self.historical_data[symbol] = sorted(ticks, key=lambda t: t.timestamp)
            self.current_indices[symbol] = 0
            
            logger.info(f"Loaded {len(ticks)} ticks for {symbol} from {csv_file}")
            return len(ticks)
            
        except Exception as e:
            logger.error(f"Failed to load CSV data: {e}", exc_info=True)
            return 0
    
    def generate_synthetic_data(
        self,
        symbol: str,
        start_price: float,
        num_ticks: int,
        volatility: float = 0.02,
        trend: float = 0.0,
        start_time: Optional[datetime] = None
    ) -> int:
        """
        Generate realistic synthetic tick data.
        
        Args:
            symbol: Symbol to generate data for
            start_price: Starting price
            num_ticks: Number of ticks to generate
            volatility: Price volatility (0.02 = 2%)
            trend: Price trend per tick (0.001 = 0.1% upward trend)
            start_time: Starting timestamp (defaults to now)
        
        Returns:
            Number of ticks generated
        """
        if start_time is None:
            start_time = datetime.now()
        
        ticks = []
        current_price = start_price
        current_time = start_time
        
        for i in range(num_ticks):
            # Random walk with trend
            change = random.gauss(trend, volatility)
            current_price *= (1 + change)
            current_price = max(current_price, 0.01)  # Prevent negative prices
            
            # Random volume
            volume = random.randint(100, 10000)
            
            # Create tick
            tick = Tick(
                symbol=symbol,
                price=round(current_price, 2),
                volume=volume,
                timestamp=current_time
            )
            ticks.append(tick)
            
            # Advance time (1 second per tick)
            current_time += timedelta(seconds=1)
        
        self.historical_data[symbol] = ticks
        self.current_indices[symbol] = 0
        
        logger.info(f"Generated {num_ticks} synthetic ticks for {symbol}")
        return num_ticks
    
    def start_replay(self, symbols: Optional[List[str]] = None) -> bool:
        """
        Start replaying historical data.
        
        Args:
            symbols: List of symbols to replay (None = all loaded symbols)
        
        Returns:
            True if started successfully
        """
        if self.state == SimulatorState.PLAYING:
            logger.warning("Simulator already playing")
            return False
        
        if not self.historical_data:
            logger.error("No historical data loaded")
            return False
        
        # Determine which symbols to replay
        replay_symbols = symbols if symbols else list(self.historical_data.keys())
        
        # Validate symbols
        for symbol in replay_symbols:
            if symbol not in self.historical_data:
                logger.error(f"No data loaded for symbol: {symbol}")
                return False
        
        # Start playback thread
        self._stop_flag = False
        self.state = SimulatorState.PLAYING
        self.playback_thread = threading.Thread(
            target=self._replay_loop,
            args=(replay_symbols,)
        )
        self.playback_thread.daemon = True
        self.playback_thread.start()
        
        logger.info(f"Started replay for {len(replay_symbols)} symbols at {self.speed}x speed")
        return True
    
    def pause(self) -> None:
        """Pause playback"""
        if self.state == SimulatorState.PLAYING:
            self.state = SimulatorState.PAUSED
            logger.info("Simulator paused")
    
    def resume(self) -> None:
        """Resume playback"""
        if self.state == SimulatorState.PAUSED:
            self.state = SimulatorState.PLAYING
            logger.info("Simulator resumed")
    
    def stop(self) -> None:
        """Stop playback"""
        self._stop_flag = True
        self.state = SimulatorState.STOPPED
        
        if self.playback_thread:
            self.playback_thread.join(timeout=5)
        
        logger.info("Simulator stopped")
    
    def set_speed(self, speed: float) -> None:
        """
        Set playback speed.
        
        Args:
            speed: Speed multiplier (1.0 = real-time, 2.0 = 2x, 0.5 = half speed)
        """
        if speed <= 0:
            raise ValueError("Speed must be positive")
        
        self.speed = speed
        logger.info(f"Simulator speed set to {speed}x")
    
    def jump_to_time(self, target_time: datetime) -> None:
        """
        Jump to a specific timestamp in the replay.
        
        Args:
            target_time: Target timestamp to jump to
        """
        for symbol in self.historical_data:
            ticks = self.historical_data[symbol]
            
            # Find the index closest to target time
            for i, tick in enumerate(ticks):
                if tick.timestamp >= target_time:
                    self.current_indices[symbol] = i
                    break
            else:
                # Target time is after all data
                self.current_indices[symbol] = len(ticks)
        
        self.current_time = target_time
        logger.info(f"Jumped to {target_time}")
    
    def on_tick(self, callback: Callable[[Tick], None]) -> None:
        """Register callback for tick events"""
        self.tick_callbacks.append(callback)
    
    def get_state(self) -> Dict:
        """Get current simulator state"""
        return {
            'mode': self.mode.value,
            'state': self.state.value,
            'speed': self.speed,
            'current_time': self.current_time.isoformat() if self.current_time else None,
            'loaded_symbols': list(self.historical_data.keys()),
            'progress': self._get_progress()
        }
    
    def _get_progress(self) -> Dict[str, float]:
        """Get playback progress for each symbol"""
        progress = {}
        for symbol, ticks in self.historical_data.items():
            if ticks:
                current_idx = self.current_indices.get(symbol, 0)
                progress[symbol] = (current_idx / len(ticks)) * 100
        return progress
    
    def _replay_loop(self, symbols: List[str]) -> None:
        """Main replay loop"""
        while not self._stop_flag:
            # Check if paused
            if self.state == SimulatorState.PAUSED:
                time.sleep(0.1)
                continue
            
            # Get next tick for each symbol
            ticks_to_emit = []
            min_timestamp = None
            
            for symbol in symbols:
                idx = self.current_indices.get(symbol, 0)
                ticks = self.historical_data.get(symbol, [])
                
                if idx < len(ticks):
                    tick = ticks[idx]
                    if min_timestamp is None or tick.timestamp < min_timestamp:
                        min_timestamp = tick.timestamp
                    ticks_to_emit.append((symbol, tick))
            
            # If no more ticks, stop
            if not ticks_to_emit:
                logger.info("Replay completed")
                self.stop()
                break
            
            # Emit ticks with the minimum timestamp
            for symbol, tick in ticks_to_emit:
                if tick.timestamp == min_timestamp:
                    self._emit_tick(tick)
                    self.current_indices[symbol] += 1
            
            self.current_time = min_timestamp
            
            # Sleep based on speed (1 second real-time = 1/speed seconds)
            time.sleep(1.0 / self.speed)
    
    def _emit_tick(self, tick: Tick) -> None:
        """Emit tick to all callbacks"""
        for callback in self.tick_callbacks:
            try:
                callback(tick)
            except Exception as e:
                logger.error(f"Error in tick callback: {e}", exc_info=True)


class SimulatorController:
    """
    Controller for simulator with API endpoints.
    
    Provides control interface for UI or API.
    """
    
    def __init__(self, simulator: MarketDataSimulator):
        self.simulator = simulator
    
    def start(self, symbols: Optional[List[str]] = None) -> Dict:
        """Start playback"""
        success = self.simulator.start_replay(symbols)
        return {
            'success': success,
            'state': self.simulator.get_state()
        }
    
    def pause(self) -> Dict:
        """Pause playback"""
        self.simulator.pause()
        return {'success': True, 'state': self.simulator.get_state()}
    
    def resume(self) -> Dict:
        """Resume playback"""
        self.simulator.resume()
        return {'success': True, 'state': self.simulator.get_state()}
    
    def stop(self) -> Dict:
        """Stop playback"""
        self.simulator.stop()
        return {'success': True, 'state': self.simulator.get_state()}
    
    def set_speed(self, speed: float) -> Dict:
        """Set playback speed"""
        try:
            self.simulator.set_speed(speed)
            return {'success': True, 'speed': speed}
        except ValueError as e:
            return {'success': False, 'error': str(e)}
    
    def jump_to_time(self, timestamp: str) -> Dict:
        """Jump to timestamp"""
        try:
            target_time = datetime.fromisoformat(timestamp)
            self.simulator.jump_to_time(target_time)
            return {'success': True, 'current_time': timestamp}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_status(self) -> Dict:
        """Get simulator status"""
        return self.simulator.get_state()
    
    def load_data(self, symbol: str, csv_file: str) -> Dict:
        """Load data from CSV"""
        count = self.simulator.load_csv_data(symbol, csv_file)
        return {
            'success': count > 0,
            'symbol': symbol,
            'ticks_loaded': count
        }
    
    def generate_data(
        self,
        symbol: str,
        start_price: float,
        num_ticks: int,
        volatility: float = 0.02,
        trend: float = 0.0
    ) -> Dict:
        """Generate synthetic data"""
        count = self.simulator.generate_synthetic_data(
            symbol, start_price, num_ticks, volatility, trend
        )
        return {
            'success': count > 0,
            'symbol': symbol,
            'ticks_generated': count
        }
