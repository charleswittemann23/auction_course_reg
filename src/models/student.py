"""Student model for course auction simulation."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Student:
    """Represents a student in the course auction."""
    
    id: str
    seniority_years: int  # 1-4 years
    virtual_budget: float = 1000.0
    allocated_course: Optional[str] = None
    clearing_price: float = 0.0
    
    def __post_init__(self):
        # Priority weight: linear formula (1.0 + 0.25 * seniority)
        self.priority_weight = 1.0 + 0.25 * self.seniority_years
    
    def effective_bid(self, bid_amount: float) -> float:
        """Calculate effective bid with priority weight."""
        return bid_amount * self.priority_weight
    
    def __repr__(self) -> str:
        return f"Student(id={self.id}, seniority={self.seniority_years}y, budget={self.virtual_budget})"