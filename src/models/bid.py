"""Bid model for course auction simulation."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Bid:
    """Represents a student's bid for a specific course."""
    
    student_id: str
    course_id: str
    bid_amount: float
    true_valuation: float  # Student's true value for the course
    is_allocated: bool = False
    clearing_price: Optional[float] = None
    
    def effective_value(self, priority_weight: float) -> float:
        """Calculate effective value with priority weight."""
        return self.true_valuation * priority_weight
    
    def __repr__(self) -> str:
        return f"Bid(student={self.student_id}, course={self.course_id}, amount={self.bid_amount:.2f}, value={self.true_valuation:.2f})"