"""Campaign iteration, runtime, request, rate, and failure budgets."""

from dataclasses import dataclass


@dataclass
class SafetyBudget:
    max_iterations: int
    max_runtime_seconds: int
    max_requests: int
    max_requests_per_minute: int
    max_consecutive_failures: int
    iterations: int = 0
    requests: int = 0
    current_minute_requests: int = 0
    consecutive_failures: int = 0

    def denial_reason(self, *, elapsed_seconds: float, proposed_requests: int = 0) -> str | None:
        if proposed_requests < 0:
            raise ValueError("proposed request count cannot be negative")
        if self.iterations >= self.max_iterations:
            return "iteration_limit"
        if elapsed_seconds >= self.max_runtime_seconds:
            return "runtime_limit"
        if self.requests + proposed_requests > self.max_requests:
            return "request_limit"
        if self.current_minute_requests + proposed_requests > self.max_requests_per_minute:
            return "rate_limit"
        if self.consecutive_failures >= self.max_consecutive_failures:
            return "consecutive_failure_limit"
        return None

    def can_continue(self, elapsed_seconds: float = 0, proposed_requests: int = 0) -> bool:
        return (
            self.denial_reason(
                elapsed_seconds=elapsed_seconds,
                proposed_requests=proposed_requests,
            )
            is None
        )

    def record(self, request_count: int, *, failed: bool = False) -> None:
        if request_count < 0:
            raise ValueError("request count cannot be negative")
        self.iterations += 1
        self.requests += request_count
        self.current_minute_requests += request_count
        self.consecutive_failures = self.consecutive_failures + 1 if failed else 0

    def reset_rate_window(self) -> None:
        self.current_minute_requests = 0
