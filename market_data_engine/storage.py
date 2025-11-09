"""
Market Data Storage

Handles storage of completed candles in InfluxDB and forming candles in Redis.
"""
import json
from datetime import datetime
from typing import List, Optional, Dict
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import redis

from .models import Candle, CandleBuffer, IndicatorValue
from shared.config.settings import get_settings

settings = get_settings()


class InfluxDBStorage:
    """Manages storage of completed candles in InfluxDB"""
    
    def __init__(self):
        self.client = None
        self.write_api = None
        self.query_api = None
        self.bucket = settings.influxdb_bucket
        self.org = settings.influxdb_org
    
    def connect(self) -> None:
        """Establish connection to InfluxDB"""
        self.client = InfluxDBClient(
            url=settings.influxdb_url,
            token=settings.influxdb_token,
            org=self.org
        )
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.query_api = self.client.query_api()
    
    def disconnect(self) -> None:
        """Close InfluxDB connection"""
        if self.client:
            self.client.close()
    
    def store_candle(self, candle: Candle) -> None:
        """Store a completed candle in InfluxDB"""
        if candle.is_forming:
            raise ValueError("Cannot store forming candle in InfluxDB")
        
        point = (
            Point("candles")
            .tag("symbol", candle.symbol)
            .tag("timeframe", candle.timeframe)
            .field("open", candle.open)
            .field("high", candle.high)
            .field("low", candle.low)
            .field("close", candle.close)
            .field("volume", candle.volume)
            .time(candle.timestamp, WritePrecision.NS)
        )
        
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)
    
    def store_candles_batch(self, candles: List[Candle]) -> None:
        """Store multiple candles in a batch"""
        points = []
        for candle in candles:
            if not candle.is_forming:
                point = (
                    Point("candles")
                    .tag("symbol", candle.symbol)
                    .tag("timeframe", candle.timeframe)
                    .field("open", candle.open)
                    .field("high", candle.high)
                    .field("low", candle.low)
                    .field("close", candle.close)
                    .field("volume", candle.volume)
                    .time(candle.timestamp, WritePrecision.NS)
                )
                points.append(point)
        
        if points:
            self.write_api.write(bucket=self.bucket, org=self.org, record=points)
    
    def get_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Candle]:
        """Retrieve historical candles for a symbol and timeframe"""
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: {start_time.isoformat()}, stop: {end_time.isoformat()})
          |> filter(fn: (r) => r["_measurement"] == "candles")
          |> filter(fn: (r) => r["symbol"] == "{symbol}")
          |> filter(fn: (r) => r["timeframe"] == "{timeframe}")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
        '''
        
        result = self.query_api.query(org=self.org, query=query)
        
        candles = []
        for table in result:
            for record in table.records:
                candle = Candle(
                    symbol=record.values.get('symbol'),
                    timeframe=record.values.get('timeframe'),
                    open=record.values.get('open'),
                    high=record.values.get('high'),
                    low=record.values.get('low'),
                    close=record.values.get('close'),
                    volume=int(record.values.get('volume', 0)),
                    timestamp=record.get_time(),
                    is_forming=False
                )
                candles.append(candle)
        
        return candles
    
    def get_recent_candles(self, symbol: str, timeframe: str, count: int) -> List[Candle]:
        """Get the most recent N candles"""
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -30d)
          |> filter(fn: (r) => r["_measurement"] == "candles")
          |> filter(fn: (r) => r["symbol"] == "{symbol}")
          |> filter(fn: (r) => r["timeframe"] == "{timeframe}")
          |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
          |> sort(columns: ["_time"], desc: true)
          |> limit(n: {count})
        '''
        
        result = self.query_api.query(org=self.org, query=query)
        
        candles = []
        for table in result:
            for record in table.records:
                candle = Candle(
                    symbol=record.values.get('symbol'),
                    timeframe=record.values.get('timeframe'),
                    open=record.values.get('open'),
                    high=record.values.get('high'),
                    low=record.values.get('low'),
                    close=record.values.get('close'),
                    volume=int(record.values.get('volume', 0)),
                    timestamp=record.get_time(),
                    is_forming=False
                )
                candles.append(candle)
        
        # Reverse to get chronological order
        return list(reversed(candles))
    
    def store_indicator(self, indicator: IndicatorValue) -> None:
        """Store indicator value in InfluxDB"""
        # Convert value to appropriate format
        if isinstance(indicator.value, dict):
            # For indicators with multiple values (e.g., MACD)
            point = Point("indicators").tag("symbol", indicator.symbol).tag("timeframe", indicator.timeframe).tag("type", indicator.indicator_type)
            for key, val in indicator.value.items():
                point = point.field(key, val)
        elif isinstance(indicator.value, list):
            # For indicators with list values (e.g., Bollinger Bands)
            point = Point("indicators").tag("symbol", indicator.symbol).tag("timeframe", indicator.timeframe).tag("type", indicator.indicator_type)
            for i, val in enumerate(indicator.value):
                point = point.field(f"value_{i}", val)
        else:
            # Single value indicators
            point = (
                Point("indicators")
                .tag("symbol", indicator.symbol)
                .tag("timeframe", indicator.timeframe)
                .tag("type", indicator.indicator_type)
                .field("value", indicator.value)
            )
        
        # Add parameters as tags
        for key, val in indicator.params.items():
            point = point.tag(key, str(val))
        
        point = point.time(indicator.timestamp, WritePrecision.NS)
        self.write_api.write(bucket=self.bucket, org=self.org, record=point)


class RedisStorage:
    """Manages storage of forming candles and indicator cache in Redis"""
    
    def __init__(self):
        self.client = None
    
    def connect(self) -> None:
        """Establish connection to Redis"""
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
    
    def disconnect(self) -> None:
        """Close Redis connection"""
        if self.client:
            self.client.close()
    
    def _get_forming_candle_key(self, symbol: str, timeframe: str) -> str:
        """Generate Redis key for forming candle"""
        return f"forming_candle:{symbol}:{timeframe}"
    
    def store_forming_candle(self, candle: Candle) -> None:
        """Store forming candle in Redis"""
        key = self._get_forming_candle_key(candle.symbol, candle.timeframe)
        self.client.set(key, json.dumps(candle.to_dict()), ex=3600)  # 1 hour expiry
    
    def get_forming_candle(self, symbol: str, timeframe: str) -> Optional[Candle]:
        """Retrieve forming candle from Redis"""
        key = self._get_forming_candle_key(symbol, timeframe)
        data = self.client.get(key)
        if data:
            return Candle.from_dict(json.loads(data))
        return None
    
    def delete_forming_candle(self, symbol: str, timeframe: str) -> None:
        """Delete forming candle from Redis (when it completes)"""
        key = self._get_forming_candle_key(symbol, timeframe)
        self.client.delete(key)
    
    def _get_indicator_cache_key(self, symbol: str, timeframe: str, indicator_type: str, params: Dict) -> str:
        """Generate Redis key for indicator cache"""
        params_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"indicator:{symbol}:{timeframe}:{indicator_type}:{params_str}"
    
    def cache_indicator(self, indicator: IndicatorValue, ttl: int = 300) -> None:
        """Cache indicator value in Redis"""
        key = self._get_indicator_cache_key(
            indicator.symbol,
            indicator.timeframe,
            indicator.indicator_type,
            indicator.params
        )
        self.client.set(key, json.dumps(indicator.to_dict()), ex=ttl)
    
    def get_cached_indicator(
        self,
        symbol: str,
        timeframe: str,
        indicator_type: str,
        params: Dict
    ) -> Optional[IndicatorValue]:
        """Retrieve cached indicator value from Redis"""
        key = self._get_indicator_cache_key(symbol, timeframe, indicator_type, params)
        data = self.client.get(key)
        if data:
            return IndicatorValue.from_dict(json.loads(data))
        return None
    
    def publish_candle_update(self, candle: Candle) -> None:
        """Publish candle update to Redis pub/sub"""
        channel = f"candle_update:{candle.symbol}:{candle.timeframe}"
        self.client.publish(channel, json.dumps(candle.to_dict()))
    
    def publish_candle_complete(self, candle: Candle) -> None:
        """Publish candle completion event to Redis pub/sub"""
        channel = f"candle_complete:{candle.symbol}:{candle.timeframe}"
        self.client.publish(channel, json.dumps(candle.to_dict()))
    
    def subscribe_to_candle_updates(self, symbol: str, timeframe: str):
        """Subscribe to candle updates for a symbol/timeframe"""
        pubsub = self.client.pubsub()
        channel = f"candle_update:{symbol}:{timeframe}"
        pubsub.subscribe(channel)
        return pubsub
    
    def subscribe_to_candle_completions(self, symbol: str, timeframe: str):
        """Subscribe to candle completion events"""
        pubsub = self.client.pubsub()
        channel = f"candle_complete:{symbol}:{timeframe}"
        pubsub.subscribe(channel)
        return pubsub


class CandleBufferManager:
    """Manages in-memory candle buffers for all symbols and timeframes"""
    
    def __init__(self, max_candles_per_buffer: int = 500):
        self.buffers: Dict[str, CandleBuffer] = {}
        self.max_candles_per_buffer = max_candles_per_buffer
    
    def _get_buffer_key(self, symbol: str, timeframe: str) -> str:
        """Generate key for buffer lookup"""
        return f"{symbol}:{timeframe}"
    
    def get_buffer(self, symbol: str, timeframe: str) -> CandleBuffer:
        """Get or create a candle buffer for symbol/timeframe"""
        key = self._get_buffer_key(symbol, timeframe)
        if key not in self.buffers:
            self.buffers[key] = CandleBuffer(
                symbol=symbol,
                timeframe=timeframe,
                max_size=self.max_candles_per_buffer
            )
        return self.buffers[key]
    
    def add_candle(self, candle: Candle) -> None:
        """Add a completed candle to the appropriate buffer"""
        buffer = self.get_buffer(candle.symbol, candle.timeframe)
        buffer.add_candle(candle)
    
    def get_recent_candles(self, symbol: str, timeframe: str, count: int) -> List[Candle]:
        """Get recent candles from buffer"""
        buffer = self.get_buffer(symbol, timeframe)
        return buffer.get_recent_candles(count)
    
    def clear_buffer(self, symbol: str, timeframe: str) -> None:
        """Clear a specific buffer"""
        key = self._get_buffer_key(symbol, timeframe)
        if key in self.buffers:
            self.buffers[key].clear()
    
    def clear_all_buffers(self) -> None:
        """Clear all buffers"""
        for buffer in self.buffers.values():
            buffer.clear()
