from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Conditional import for pandas type hinting
try:
    import pandas as pd
except ImportError:
    pd = None

from .events import write_jsonl
from .hashing import compute_config_fingerprint
from .schemas import (
    Decision,
    DecisionContext,
    ExecutionReport,
    OrderRequest,
    RunStart,
)
from .snapshot import save_bars_snapshot

logger = logging.getLogger(__name__)


class ConsistencyRecorder:
    """
    The main interface for a trading bot to log audit events.
    (Aggregates Steps 10, 12, 26, 30-33)
    """

    def __init__(self, root_dir: str | Path, run_id: str):
        self.root = Path(root_dir)
        self.run_id = run_id
        
        # Folder structure (Step 10)
        # output/run_id/audit/events.jsonl
        # output/run_id/audit/snapshots/
        self.audit_dir = self.root / self.run_id / "audit"
        self.events_path = self.audit_dir / "events.jsonl"
        self.snapshots_dir = self.audit_dir / "snapshots"

    def log_startup(self, config: dict, app_version: str = "0.0.0") -> None:
        """
        Step 12: Log the RunStart event.
        """
        try:
            fingerprint = compute_config_fingerprint(config)
            ev = RunStart(
                run_id=self.run_id,
                timestamp=datetime.now(timezone.utc),
                app_version=app_version,
                config_fingerprint=fingerprint,
            )
            write_jsonl(self.events_path, ev.to_event())
        except Exception:
            logger.exception("Failed to log startup event")

    def log_decision(
        self,
        context: DecisionContext,
        intent: str,
        bars: Optional[pd.DataFrame] = None,
        suggested_price: Optional[float] = None,
        suggested_sl: Optional[float] = None,
        suggested_tp: Optional[float] = None,
    ) -> str:
        """
        Step 19 & 26: Log a decision and optionally snapshot data.
        Returns: signal_id (Step 23)
        """
        try:
            # 1. Create the Decision object (auto-generates signal_id)
            decision = Decision(
                context=context,
                intent=intent,
                suggested_price=suggested_price,
                suggested_sl=suggested_sl,
                suggested_tp=suggested_tp,
            )

            # 2. Snapshot logic (Step 26: Snapshot only if actionable)
            # We snapshot if intent is NOT 'NONE' (actionable) AND bars are provided.
            if intent != "NONE" and bars is not None and not bars.empty:
                fname = save_bars_snapshot(
                    self.snapshots_dir, decision.signal_id, bars
                )
                decision.snapshot_path = fname

            # 3. Write to log
            write_jsonl(self.events_path, decision.to_event())

            return decision.signal_id

        except Exception:
            logger.exception("Failed to log decision")
            return "error_id"

    def log_order_request(self, req: OrderRequest) -> None:
        """Step 30: Log that we tried to send an order."""
        try:
            write_jsonl(self.events_path, req.to_event())
        except Exception:
            logger.exception("Failed to log order request")

    def log_execution(self, report: ExecutionReport) -> None:
        """Step 32-33: Log a fill or rejection."""
        try:
            write_jsonl(self.events_path, report.to_event())
        except Exception:
            logger.exception("Failed to log execution report")
