from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .hashing import compute_signal_id


@dataclass
class DecisionContext:
    """
    Captures the exact market state and configuration at the moment of decision.
    (Steps 20-22)
    """
    symbol: str
    decision_time: datetime

    # Market data snapshots (Step 20)
    bid: float
    ask: float
    spread: float

    # Strategy inputs (Step 21)
    strategy_tag: str
    params: dict[str, Any]

    # Data integrity (Step 22)
    bars_hash: str      # Hash of the OHLCV data used
    features_hash: str  # Hash of calculated indicators

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "decision_time": self.decision_time.isoformat(),
            "bid": self.bid,
            "ask": self.ask,
            "spread": self.spread,
            "strategy_tag": self.strategy_tag,
            "params": self.params,
            "bars_hash": self.bars_hash,
            "features_hash": self.features_hash,
        }


@dataclass
class Decision:
    """
    The central event recording a strategy's choice.
    (Step 19)
    """
    context: DecisionContext
    intent: str  # BUY, SELL, NONE

    # This ID is auto-calculated in __post_init__
    signal_id: str = field(init=False)

    # Optional execution details if intent != NONE
    suggested_price: Optional[float] = None
    suggested_sl: Optional[float] = None
    suggested_tp: Optional[float] = None

    # Pointer to full data snapshot (Step 29)
    snapshot_path: Optional[str] = None

    def __post_init__(self):
        # Auto-generate ID immediately upon creation (Steps 23 & 24)
        self.signal_id = compute_signal_id(
            symbol=self.context.symbol,
            decision_time=self.context.decision_time,
            side=self.intent,
            strategy_tag=self.context.strategy_tag,
            bars_hash=self.context.bars_hash
        )

    def to_event(self) -> dict[str, Any]:
        return {
            "event_type": "DECISION",
            "signal_id": self.signal_id,
            "intent": self.intent,
            "context": self.context.to_dict(),
            "suggested": {
                "price": self.suggested_price,
                "sl": self.suggested_sl,
                "tp": self.suggested_tp,
            },
            "snapshot_path": self.snapshot_path,
        }


@dataclass
class RunStart:
    """
    Step 12: Boot event to link a log file to a specific code/config version.
    """
    run_id: str
    timestamp: datetime
    app_version: str
    config_fingerprint: str  # from compute_config_fingerprint

    def to_event(self) -> dict[str, Any]:
        return {
            "event_type": "RUN_START",
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "app_version": self.app_version,
            "config_fingerprint": self.config_fingerprint,
        }


@dataclass
class OrderRequest:
    """
    Step 30: The specific request sent to the broker.
    """
    signal_id: str
    timestamp: datetime
    symbol: str
    side: str
    volume: float
    price: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    order_type: str = "MARKET"

    def to_event(self) -> dict[str, Any]:
        return {
            "event_type": "ORDER_SENT",
            "signal_id": self.signal_id,
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "side": self.side,
            "volume": self.volume,
            "price": self.price,
            "sl": self.sl,
            "tp": self.tp,
            "order_type": self.order_type,
        }


@dataclass
class ExecutionReport:
    """
    Steps 31-34: Fills, Rejections, or Cancellations.
    """
    signal_id: str
    timestamp: datetime
    event_subtype: str  # FILL_OPEN, FILL_CLOSE, REJECTED, ORDER_RESULT

    # Execution details
    fill_price: Optional[float] = None
    commission: Optional[float] = None
    profit: Optional[float] = None
    order_id: Optional[str] = None
    position_id: Optional[str] = None
    comment: str = ""

    def to_event(self) -> dict[str, Any]:
        return {
            "event_type": self.event_subtype,
            "signal_id": self.signal_id,
            "timestamp": self.timestamp.isoformat(),
            "fill_price": self.fill_price,
            "commission": self.commission,
            "profit": self.profit,
            "order_id": self.order_id,
            "position_id": self.position_id,
            "comment": self.comment,
        }
