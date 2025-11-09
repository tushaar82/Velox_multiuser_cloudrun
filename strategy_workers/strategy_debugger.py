"""
Strategy Debugger

Provides debugging capabilities for strategy development.
"""
import threading
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BreakpointType(Enum):
    """Types of breakpoints"""
    CANDLE_COMPLETE = "candle_complete"
    SIGNAL_GENERATED = "signal_generated"
    ORDER_PLACED = "order_placed"
    POSITION_OPENED = "position_opened"
    POSITION_CLOSED = "position_closed"
    INDICATOR_VALUE = "indicator_value"
    CUSTOM = "custom"


@dataclass
class Breakpoint:
    """Breakpoint configuration"""
    id: str
    type: BreakpointType
    enabled: bool = True
    condition: Optional[str] = None  # Python expression
    hit_count: int = 0
    max_hits: Optional[int] = None


@dataclass
class DebugFrame:
    """Debug frame capturing strategy state"""
    timestamp: datetime
    symbol: str
    timeframe: str
    candle_data: Dict[str, Any]
    indicator_values: Dict[str, Any]
    strategy_variables: Dict[str, Any]
    signals: List[Dict[str, Any]]
    positions: List[Dict[str, Any]]
    orders: List[Dict[str, Any]]


class StrategyDebugger:
    """
    Strategy debugger with breakpoints and variable inspection.
    
    Features:
    - Breakpoints on candle completion
    - Variable inspection
    - Step-through execution
    - Conditional breakpoints
    """
    
    def __init__(self):
        self.breakpoints: Dict[str, Breakpoint] = {}
        self.debug_frames: List[DebugFrame] = []
        self.is_paused = False
        self.current_frame: Optional[DebugFrame] = None
        self.pause_event = threading.Event()
        self.pause_event.set()  # Not paused initially
        self.step_mode = False
        self.callbacks: List[Callable[[DebugFrame], None]] = []
    
    def add_breakpoint(
        self,
        breakpoint_type: BreakpointType,
        condition: Optional[str] = None,
        max_hits: Optional[int] = None
    ) -> str:
        """
        Add a breakpoint.
        
        Args:
            breakpoint_type: Type of breakpoint
            condition: Optional condition (Python expression)
            max_hits: Maximum number of hits before disabling
        
        Returns:
            Breakpoint ID
        """
        breakpoint_id = f"bp_{len(self.breakpoints) + 1}"
        
        breakpoint = Breakpoint(
            id=breakpoint_id,
            type=breakpoint_type,
            condition=condition,
            max_hits=max_hits
        )
        
        self.breakpoints[breakpoint_id] = breakpoint
        logger.info(f"Added breakpoint: {breakpoint_id} ({breakpoint_type.value})")
        
        return breakpoint_id
    
    def remove_breakpoint(self, breakpoint_id: str) -> bool:
        """Remove a breakpoint"""
        if breakpoint_id in self.breakpoints:
            del self.breakpoints[breakpoint_id]
            logger.info(f"Removed breakpoint: {breakpoint_id}")
            return True
        return False
    
    def enable_breakpoint(self, breakpoint_id: str) -> bool:
        """Enable a breakpoint"""
        if breakpoint_id in self.breakpoints:
            self.breakpoints[breakpoint_id].enabled = True
            return True
        return False
    
    def disable_breakpoint(self, breakpoint_id: str) -> bool:
        """Disable a breakpoint"""
        if breakpoint_id in self.breakpoints:
            self.breakpoints[breakpoint_id].enabled = False
            return True
        return False
    
    def check_breakpoint(
        self,
        breakpoint_type: BreakpointType,
        context: Dict[str, Any]
    ) -> bool:
        """
        Check if any breakpoint should trigger.
        
        Args:
            breakpoint_type: Type of event
            context: Context variables for condition evaluation
        
        Returns:
            True if should pause
        """
        for bp in self.breakpoints.values():
            if not bp.enabled:
                continue
            
            if bp.type != breakpoint_type:
                continue
            
            # Check max hits
            if bp.max_hits and bp.hit_count >= bp.max_hits:
                bp.enabled = False
                continue
            
            # Evaluate condition
            if bp.condition:
                try:
                    if not eval(bp.condition, {}, context):
                        continue
                except Exception as e:
                    logger.error(f"Error evaluating breakpoint condition: {e}")
                    continue
            
            # Breakpoint hit
            bp.hit_count += 1
            logger.info(f"Breakpoint hit: {bp.id} (hit count: {bp.hit_count})")
            return True
        
        return False
    
    def capture_frame(
        self,
        symbol: str,
        timeframe: str,
        candle_data: Dict[str, Any],
        indicator_values: Dict[str, Any],
        strategy_variables: Dict[str, Any],
        signals: List[Dict[str, Any]],
        positions: List[Dict[str, Any]],
        orders: List[Dict[str, Any]]
    ) -> DebugFrame:
        """
        Capture current strategy state.
        
        Args:
            symbol: Symbol
            timeframe: Timeframe
            candle_data: Candle data
            indicator_values: Indicator values
            strategy_variables: Strategy internal variables
            signals: Generated signals
            positions: Current positions
            orders: Current orders
        
        Returns:
            Debug frame
        """
        frame = DebugFrame(
            timestamp=datetime.now(),
            symbol=symbol,
            timeframe=timeframe,
            candle_data=candle_data,
            indicator_values=indicator_values,
            strategy_variables=strategy_variables,
            signals=signals,
            positions=positions,
            orders=orders
        )
        
        self.debug_frames.append(frame)
        self.current_frame = frame
        
        # Notify callbacks
        for callback in self.callbacks:
            try:
                callback(frame)
            except Exception as e:
                logger.error(f"Error in debug callback: {e}")
        
        return frame
    
    def pause(self) -> None:
        """Pause execution"""
        self.is_paused = True
        self.pause_event.clear()
        logger.info("Debugger paused")
    
    def resume(self) -> None:
        """Resume execution"""
        self.is_paused = False
        self.step_mode = False
        self.pause_event.set()
        logger.info("Debugger resumed")
    
    def step(self) -> None:
        """Step to next event"""
        self.step_mode = True
        self.pause_event.set()
        logger.info("Debugger stepping")
    
    def wait_if_paused(self) -> None:
        """Wait if debugger is paused"""
        if self.step_mode:
            self.pause()
            self.step_mode = False
        
        self.pause_event.wait()
    
    def get_current_frame(self) -> Optional[DebugFrame]:
        """Get current debug frame"""
        return self.current_frame
    
    def get_frames(self, limit: int = 100) -> List[DebugFrame]:
        """Get recent debug frames"""
        return self.debug_frames[-limit:]
    
    def clear_frames(self) -> None:
        """Clear all debug frames"""
        self.debug_frames.clear()
        self.current_frame = None
    
    def inspect_variable(self, variable_name: str) -> Any:
        """Inspect a strategy variable"""
        if self.current_frame is None:
            return None
        
        return self.current_frame.strategy_variables.get(variable_name)
    
    def inspect_indicator(self, indicator_name: str) -> Any:
        """Inspect an indicator value"""
        if self.current_frame is None:
            return None
        
        return self.current_frame.indicator_values.get(indicator_name)
    
    def on_frame_captured(self, callback: Callable[[DebugFrame], None]) -> None:
        """Register callback for frame capture"""
        self.callbacks.append(callback)
    
    def get_breakpoints(self) -> List[Dict[str, Any]]:
        """Get all breakpoints"""
        return [
            {
                'id': bp.id,
                'type': bp.type.value,
                'enabled': bp.enabled,
                'condition': bp.condition,
                'hit_count': bp.hit_count,
                'max_hits': bp.max_hits
            }
            for bp in self.breakpoints.values()
        ]
    
    def get_state(self) -> Dict[str, Any]:
        """Get debugger state"""
        return {
            'is_paused': self.is_paused,
            'step_mode': self.step_mode,
            'num_breakpoints': len(self.breakpoints),
            'num_frames': len(self.debug_frames),
            'current_frame': {
                'timestamp': self.current_frame.timestamp.isoformat(),
                'symbol': self.current_frame.symbol,
                'timeframe': self.current_frame.timeframe
            } if self.current_frame else None
        }


class VariableInspector:
    """
    Variable inspector for real-time strategy monitoring.
    
    Tracks and displays strategy variables and indicators.
    """
    
    def __init__(self):
        self.watched_variables: Dict[str, List[Any]] = {}
        self.watched_indicators: Dict[str, List[Any]] = {}
        self.max_history = 1000
    
    def watch_variable(self, name: str) -> None:
        """Start watching a variable"""
        if name not in self.watched_variables:
            self.watched_variables[name] = []
            logger.info(f"Watching variable: {name}")
    
    def watch_indicator(self, name: str) -> None:
        """Start watching an indicator"""
        if name not in self.watched_indicators:
            self.watched_indicators[name] = []
            logger.info(f"Watching indicator: {name}")
    
    def unwatch_variable(self, name: str) -> None:
        """Stop watching a variable"""
        if name in self.watched_variables:
            del self.watched_variables[name]
    
    def unwatch_indicator(self, name: str) -> None:
        """Stop watching an indicator"""
        if name in self.watched_indicators:
            del self.watched_indicators[name]
    
    def update(self, frame: DebugFrame) -> None:
        """Update watched values from debug frame"""
        # Update variables
        for name in self.watched_variables:
            value = frame.strategy_variables.get(name)
            if value is not None:
                self.watched_variables[name].append({
                    'timestamp': frame.timestamp,
                    'value': value
                })
                
                # Limit history
                if len(self.watched_variables[name]) > self.max_history:
                    self.watched_variables[name].pop(0)
        
        # Update indicators
        for name in self.watched_indicators:
            value = frame.indicator_values.get(name)
            if value is not None:
                self.watched_indicators[name].append({
                    'timestamp': frame.timestamp,
                    'value': value
                })
                
                # Limit history
                if len(self.watched_indicators[name]) > self.max_history:
                    self.watched_indicators[name].pop(0)
    
    def get_variable_history(self, name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get variable history"""
        if name not in self.watched_variables:
            return []
        
        history = self.watched_variables[name][-limit:]
        return [
            {
                'timestamp': h['timestamp'].isoformat(),
                'value': h['value']
            }
            for h in history
        ]
    
    def get_indicator_history(self, name: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get indicator history"""
        if name not in self.watched_indicators:
            return []
        
        history = self.watched_indicators[name][-limit:]
        return [
            {
                'timestamp': h['timestamp'].isoformat(),
                'value': h['value']
            }
            for h in history
        ]
    
    def get_current_values(self) -> Dict[str, Any]:
        """Get current values of all watched items"""
        result = {
            'variables': {},
            'indicators': {}
        }
        
        for name, history in self.watched_variables.items():
            if history:
                result['variables'][name] = history[-1]['value']
        
        for name, history in self.watched_indicators.items():
            if history:
                result['indicators'][name] = history[-1]['value']
        
        return result
