"""Campaign request, iteration, and runtime budgets."""

from dataclasses import dataclass


@dataclass
class SafetyBudget:
    max_iterations: int
    max_runtime_seconds: int
    max_requests: int
    iterations: int = 0
    requests: int = 0

    def can_continue(self, elapsed_seconds: float = 0) -> bool:
        return (
            self.iterations < self.max_iterations
            and self.requests < self.max_requests
            and elapsed_seconds < self.max_runtime_seconds
        )

    def record(self, request_count: int) -> None:
        self.iterations += 1
        self.requests += request_count
