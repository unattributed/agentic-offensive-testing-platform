"""Privacy-preserving operator metrics."""

from dataclasses import dataclass


@dataclass
class OperatorMetrics:
    manual_hours_spent: float = 0
    agent_assisted_hours_spent: float = 0
    number_of_requests: int = 0
    number_of_cases_executed: int = 0
    number_of_candidates_generated: int = 0
    number_confirmed: int = 0
    number_submitted: int = 0
    number_accepted: int = 0
    number_rejected: int = 0
    number_duplicate: int = 0
    bounty_amount: float = 0
    estimated_tool_cost: float = 0
