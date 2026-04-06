from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


def _parse_dt(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    s = str(value).strip()
    if not s:
        return None
    s_iso = s.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s_iso)
    except ValueError:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class RunInfo:
    run_id: str
    timestamp: str
    app_version: str
    config_fingerprint: str


@dataclass
class EventChain:
    signal_id: str
    decision: dict[str, Any] | None = None
    order_sent: dict[str, Any] | None = None
    fills: list[dict[str, Any]] = field(default_factory=list)
    rejections: list[dict[str, Any]] = field(default_factory=list)

    @property
    def was_filled(self) -> bool:
        return bool(self.fills)

    @property
    def was_rejected(self) -> bool:
        return bool(self.rejections)

    @property
    def intent(self) -> str:
        if not self.decision:
            return ""
        return str(self.decision.get("intent", ""))

    @property
    def is_actionable(self) -> bool:
        return self.intent not in ("", "NONE")

    def decision_time(self) -> Optional[datetime]:
        if not self.decision:
            return None
        ctx = self.decision.get("context", {})
        return _parse_dt(ctx.get("decision_time"))

    def first_fill_time(self) -> Optional[datetime]:
        times = []
        for ev in self.fills:
            dt = _parse_dt(ev.get("timestamp"))
            if dt is not None:
                times.append(dt)
        return min(times) if times else None

    def latency_ms(self) -> Optional[float]:
        start = self.decision_time()
        end = self.first_fill_time()
        if start is None or end is None:
            return None
        return max(0.0, (end - start).total_seconds() * 1000.0)


@dataclass(frozen=True)
class ReplayReport:
    run_info: RunInfo | None
    chains: list[EventChain]
    orphaned_events: list[dict[str, Any]]
    total_decisions: int
    actionable_decisions: int
    filled_count: int
    rejected_count: int
    unexecuted_count: int
    fill_rate: float
    latencies_ms: list[float]


def replay_from_file(path: str | Path) -> ReplayReport:
    p = Path(path)
    run_info: RunInfo | None = None
    chains: dict[str, EventChain] = {}
    orphaned_events: list[dict[str, Any]] = []

    with p.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            ev = json.loads(line)
            event_type = str(ev.get('event_type', ''))

            if event_type == 'RUN_START':
                run_info = RunInfo(
                    run_id=str(ev.get('run_id', '')),
                    timestamp=str(ev.get('timestamp', '')),
                    app_version=str(ev.get('app_version', '')),
                    config_fingerprint=str(ev.get('config_fingerprint', '')),
                )
                continue

            signal_id = ev.get('signal_id')
            if not signal_id:
                orphaned_events.append(ev)
                continue

            signal_id = str(signal_id)
            chain = chains.get(signal_id)

            if event_type == 'DECISION':
                if chain is None:
                    chain = EventChain(signal_id=signal_id)
                    chains[signal_id] = chain
                chain.decision = ev
                continue

            if chain is None:
                orphaned_events.append(ev)
                continue

            if event_type == 'ORDER_SENT':
                chain.order_sent = ev
            elif event_type in {'FILL_OPEN', 'FILL_CLOSE', 'ORDER_RESULT'}:
                chain.fills.append(ev)
            elif event_type == 'REJECTED':
                chain.rejections.append(ev)
            else:
                orphaned_events.append(ev)

    chain_list = list(chains.values())
    total_decisions = len(chain_list)
    actionable = [c for c in chain_list if c.is_actionable]
    actionable_decisions = len(actionable)
    filled_count = sum(1 for c in actionable if c.was_filled)
    rejected_count = sum(1 for c in actionable if c.was_rejected)
    unexecuted_count = sum(1 for c in actionable if not c.was_filled and not c.was_rejected)
    latencies_ms = [lat for c in actionable if (lat := c.latency_ms()) is not None]
    fill_rate = (filled_count / actionable_decisions) if actionable_decisions else 0.0

    return ReplayReport(
        run_info=run_info,
        chains=chain_list,
        orphaned_events=orphaned_events,
        total_decisions=total_decisions,
        actionable_decisions=actionable_decisions,
        filled_count=filled_count,
        rejected_count=rejected_count,
        unexecuted_count=unexecuted_count,
        fill_rate=fill_rate,
        latencies_ms=latencies_ms,
    )
