"""MBOS Audit v1 — structured JSONL event log.

Records all system events: user requests, governor decisions, tool calls,
tool results, errors. JSONL format for easy parsing and replay.

Usage:
    auditor = Auditor()
    auditor.record(ToolCallEvent(...))
"""
import json, os, time, threading
from typing import Optional


class Auditor:
    """Structured JSONL audit log for all MBOS events."""

    LOG_DIR = "logs/audit"

    def __init__(self):
        os.makedirs(self.LOG_DIR, exist_ok=True)
        self._lock = threading.Lock()
        self._count = 0
        self._errors = 0

    def record(self, event) -> None:
        """Write an event to the audit log."""
        try:
            record = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "event_id": getattr(event, "event_id", ""),
                "event_type": getattr(event, "event_type", "unknown"),
                "session_id": getattr(event, "session_id", 0),
                "request_id": getattr(event, "request_id", ""),
            }
            # Add event-specific fields
            for attr in ("tool_name", "arguments", "status", "elapsed_ms",
                        "error", "severity", "provider", "remaining"):
                val = getattr(event, attr, None)
                if val is not None and val != "":
                    record[attr] = val

            if hasattr(event, "payload") and event.payload:
                record["payload"] = event.payload
            if hasattr(event, "metadata") and event.metadata:
                record["metadata"] = event.metadata

            logfile = os.path.join(self.LOG_DIR, f"audit_{time.strftime('%Y%m%d')}.jsonl")
            with self._lock:
                with open(logfile, "a") as f:
                    f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
                self._count += 1
        except Exception:
            self._errors += 1

    def record_decision(self, decision) -> None:
        """Record a Governor decision."""
        record = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "event_type": "governor_decision",
            "allow": decision.allow,
            "reason": decision.reason,
            "risk_level": decision.risk_level,
            "required_action": decision.required_action,
            "tool_name": decision.tool_name,
        }
        try:
            logfile = os.path.join(self.LOG_DIR, f"audit_{time.strftime('%Y%m%d')}.jsonl")
            with self._lock:
                with open(logfile, "a") as f:
                    f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
                self._count += 1
        except Exception:
            self._errors += 1

    def stats(self) -> dict:
        return {"total_events": self._count, "errors": self._errors,
                "log_dir": self.LOG_DIR}
