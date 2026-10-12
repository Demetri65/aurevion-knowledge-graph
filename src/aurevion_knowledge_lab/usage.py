"""Opt-in LiteLLM usage recording without prompts, keys or provider payloads."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock


class UsageLedger:
    def __init__(self):
        self.records = []
        self._ids = set()
        self._lock = Lock()

    def record(self, kwargs, response, start_time, end_time):
        data = response.model_dump() if hasattr(response, "model_dump") else dict(response)
        request_id = data.get("id") or f"{kwargs.get('model')}:{start_time}:{end_time}"
        usage = data.get("usage") or {}
        cost = kwargs.get("response_cost")
        row = {"request_id": request_id, "model": kwargs.get("model"),
               "recorded_at": datetime.now(timezone.utc).isoformat(),
               "input_tokens": usage.get("prompt_tokens"), "output_tokens": usage.get("completion_tokens"),
               "total_tokens": usage.get("total_tokens"),
               "estimated_api_cost_usd": cost if isinstance(cost, (int, float)) else None}
        with self._lock:
            if request_id not in self._ids:
                self._ids.add(request_id)
                self.records.append(row)

    def summary(self):
        with self._lock:
            rows = list(self.records)
        known_costs = [row["estimated_api_cost_usd"] for row in rows if row["estimated_api_cost_usd"] is not None]
        return {"observed_requests": len(rows), "observed_total_tokens": sum(row["total_tokens"] or 0 for row in rows),
                "estimated_api_cost_usd": sum(known_costs) if known_costs else None,
                "requests_missing_cost": len(rows) - len(known_costs),
                "note": "Observed LiteLLM callbacks; estimated API cost is not a billing statement or a hard spend limit."}


def install_usage_ledger():
    import litellm
    from litellm.integrations.custom_logger import CustomLogger

    ledger = UsageLedger()

    class Recorder(CustomLogger):
        def log_success_event(self, kwargs, response_obj, start_time, end_time):
            ledger.record(kwargs, response_obj, start_time, end_time)

        async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
            ledger.record(kwargs, response_obj, start_time, end_time)

    recorder = Recorder()
    litellm.callbacks = [*litellm.callbacks, recorder]
    return ledger
