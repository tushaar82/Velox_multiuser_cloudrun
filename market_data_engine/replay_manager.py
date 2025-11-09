"""
Replay Session Manager

Manages replay sessions with save/load state and time travel features.
"""
import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import logging

from .simulator import MarketDataSimulator, SimulatorState

logger = logging.getLogger(__name__)


@dataclass
class ReplayEvent:
    """Event that occurred during replay"""
    timestamp: datetime
    event_type: str  # 'tick', 'candle_complete', 'signal', 'order', 'position_update'
    symbol: str
    data: Dict[str, Any]


@dataclass
class ReplaySession:
    """Replay session state"""
    session_id: str
    name: str
    created_at: datetime
    symbols: List[str]
    start_time: datetime
    end_time: datetime
    current_time: Optional[datetime]
    speed: float
    state: str
    events: List[ReplayEvent]
    strategy_configs: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]


class ReplaySessionManager:
    """
    Manages replay sessions with save/load functionality.
    
    Features:
    - Save/load replay state
    - Time travel (jump to specific timestamp)
    - Event logging
    - Session comparison
    """
    
    def __init__(self, sessions_dir: str = "./replay_sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: Optional[ReplaySession] = None
        self.simulator: Optional[MarketDataSimulator] = None
    
    def create_session(
        self,
        name: str,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime,
        strategy_configs: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Create a new replay session.
        
        Args:
            name: Session name
            symbols: Symbols to replay
            start_time: Replay start time
            end_time: Replay end time
            strategy_configs: Strategy configurations
        
        Returns:
            Session ID
        """
        session_id = f"replay_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.current_session = ReplaySession(
            session_id=session_id,
            name=name,
            created_at=datetime.now(),
            symbols=symbols,
            start_time=start_time,
            end_time=end_time,
            current_time=start_time,
            speed=1.0,
            state=SimulatorState.STOPPED.value,
            events=[],
            strategy_configs=strategy_configs or [],
            performance_metrics={}
        )
        
        logger.info(f"Created replay session: {session_id}")
        return session_id
    
    def save_session(self, session_id: Optional[str] = None) -> str:
        """
        Save current replay session to disk.
        
        Args:
            session_id: Session ID (uses current if None)
        
        Returns:
            Path to saved session file
        """
        if session_id is None:
            if self.current_session is None:
                raise ValueError("No active session to save")
            session_id = self.current_session.session_id
        
        session_file = self.sessions_dir / f"{session_id}.json"
        
        # Convert session to dict
        session_dict = asdict(self.current_session)
        
        # Convert datetime objects to ISO format
        session_dict['created_at'] = session_dict['created_at'].isoformat()
        session_dict['start_time'] = session_dict['start_time'].isoformat()
        session_dict['end_time'] = session_dict['end_time'].isoformat()
        if session_dict['current_time']:
            session_dict['current_time'] = session_dict['current_time'].isoformat()
        
        # Convert events
        for event in session_dict['events']:
            event['timestamp'] = event['timestamp'].isoformat()
        
        # Save to file
        with open(session_file, 'w') as f:
            json.dump(session_dict, f, indent=2)
        
        logger.info(f"Saved session to {session_file}")
        return str(session_file)
    
    def load_session(self, session_id: str) -> ReplaySession:
        """
        Load a replay session from disk.
        
        Args:
            session_id: Session ID to load
        
        Returns:
            Loaded replay session
        """
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if not session_file.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")
        
        with open(session_file, 'r') as f:
            session_dict = json.load(f)
        
        # Convert ISO format back to datetime
        session_dict['created_at'] = datetime.fromisoformat(session_dict['created_at'])
        session_dict['start_time'] = datetime.fromisoformat(session_dict['start_time'])
        session_dict['end_time'] = datetime.fromisoformat(session_dict['end_time'])
        if session_dict['current_time']:
            session_dict['current_time'] = datetime.fromisoformat(session_dict['current_time'])
        
        # Convert events
        for event in session_dict['events']:
            event['timestamp'] = datetime.fromisoformat(event['timestamp'])
        
        # Create ReplaySession object
        events = [ReplayEvent(**e) for e in session_dict['events']]
        session_dict['events'] = events
        
        self.current_session = ReplaySession(**session_dict)
        
        logger.info(f"Loaded session: {session_id}")
        return self.current_session
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all saved replay sessions.
        
        Returns:
            List of session summaries
        """
        sessions = []
        
        for session_file in self.sessions_dir.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    session_dict = json.load(f)
                
                sessions.append({
                    'session_id': session_dict['session_id'],
                    'name': session_dict['name'],
                    'created_at': session_dict['created_at'],
                    'symbols': session_dict['symbols'],
                    'start_time': session_dict['start_time'],
                    'end_time': session_dict['end_time'],
                    'num_events': len(session_dict['events'])
                })
            except Exception as e:
                logger.error(f"Error loading session {session_file}: {e}")
        
        return sorted(sessions, key=lambda s: s['created_at'], reverse=True)
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a replay session.
        
        Args:
            session_id: Session ID to delete
        
        Returns:
            True if deleted successfully
        """
        session_file = self.sessions_dir / f"{session_id}.json"
        
        if session_file.exists():
            session_file.unlink()
            logger.info(f"Deleted session: {session_id}")
            return True
        
        return False
    
    def log_event(
        self,
        event_type: str,
        symbol: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Log an event during replay.
        
        Args:
            event_type: Type of event
            symbol: Symbol
            data: Event data
        """
        if self.current_session is None:
            return
        
        event = ReplayEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            symbol=symbol,
            data=data
        )
        
        self.current_session.events.append(event)
    
    def get_events(
        self,
        event_type: Optional[str] = None,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[ReplayEvent]:
        """
        Get events from current session with filters.
        
        Args:
            event_type: Filter by event type
            symbol: Filter by symbol
            start_time: Filter by start time
            end_time: Filter by end time
        
        Returns:
            Filtered list of events
        """
        if self.current_session is None:
            return []
        
        events = self.current_session.events
        
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if symbol:
            events = [e for e in events if e.symbol == symbol]
        
        if start_time:
            events = [e for e in events if e.timestamp >= start_time]
        
        if end_time:
            events = [e for e in events if e.timestamp <= end_time]
        
        return events
    
    def jump_to_time(self, target_time: datetime) -> bool:
        """
        Jump to a specific time in the replay.
        
        Args:
            target_time: Target timestamp
        
        Returns:
            True if successful
        """
        if self.current_session is None:
            logger.error("No active session")
            return False
        
        if self.simulator is None:
            logger.error("No simulator attached")
            return False
        
        # Validate time range
        if target_time < self.current_session.start_time:
            target_time = self.current_session.start_time
        elif target_time > self.current_session.end_time:
            target_time = self.current_session.end_time
        
        # Jump simulator
        self.simulator.jump_to_time(target_time)
        self.current_session.current_time = target_time
        
        logger.info(f"Jumped to {target_time}")
        return True
    
    def attach_simulator(self, simulator: MarketDataSimulator) -> None:
        """Attach a simulator to this session manager"""
        self.simulator = simulator
    
    def update_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update performance metrics for current session"""
        if self.current_session:
            self.current_session.performance_metrics = metrics
    
    def compare_sessions(
        self,
        session_ids: List[str]
    ) -> Dict[str, Any]:
        """
        Compare multiple replay sessions.
        
        Args:
            session_ids: List of session IDs to compare
        
        Returns:
            Comparison results
        """
        sessions = []
        
        for session_id in session_ids:
            try:
                session = self.load_session(session_id)
                sessions.append(session)
            except Exception as e:
                logger.error(f"Error loading session {session_id}: {e}")
        
        if not sessions:
            return {}
        
        comparison = {
            'sessions': [],
            'common_symbols': self._find_common_symbols(sessions),
            'time_overlap': self._find_time_overlap(sessions)
        }
        
        for session in sessions:
            comparison['sessions'].append({
                'session_id': session.session_id,
                'name': session.name,
                'symbols': session.symbols,
                'num_events': len(session.events),
                'performance': session.performance_metrics
            })
        
        return comparison
    
    def _find_common_symbols(self, sessions: List[ReplaySession]) -> List[str]:
        """Find symbols common to all sessions"""
        if not sessions:
            return []
        
        common = set(sessions[0].symbols)
        for session in sessions[1:]:
            common &= set(session.symbols)
        
        return sorted(list(common))
    
    def _find_time_overlap(self, sessions: List[ReplaySession]) -> Dict[str, str]:
        """Find time overlap between sessions"""
        if not sessions:
            return {}
        
        start_time = max(s.start_time for s in sessions)
        end_time = min(s.end_time for s in sessions)
        
        if start_time >= end_time:
            return {'overlap': False}
        
        return {
            'overlap': True,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
